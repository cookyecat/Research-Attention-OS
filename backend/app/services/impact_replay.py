"""Cognitive Impact Replay / Attribution Harness v0.1.

Re-executes only Impact on a frozen AnalysisRun input. Never mutates the run,
Kernel, AttentionPlan, or Human Feedback.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.cognitive.runtime import STAGE_RUNTIME, StageRuntime
from app.cognitive.versions import IMPACT_ASSESSOR_VERSION, IMPACT_REPLAY_VERSION
from app.config import settings
from app.models.analysis import AnalysisRun
from app.models.impact_replay import ImpactReplay
from app.services.cognitive_impact import CognitiveImpactAssessment, primary_update
from app.services.impact_input import (
    canonical_json,
    extraction_from_snapshot,
    fingerprint_snapshot,
    frozen_impact_input_from_run,
    kernel_nodes_from_snapshot,
    matches_from_snapshot,
)


@dataclass
class ImpactReplayConfig:
    provider: str | None = None
    model: str | None = None
    thinking: str | None = None
    reasoning_effort: str | None = None
    timeout: float | None = None
    label: str | None = None

    def as_dict(self) -> dict:
        kind = (self.provider or settings.cognitive_provider or "rule").lower()
        return {
            "provider": kind,
            "model": self.model if kind != "rule" else None,
            "thinking": self.thinking,
            "reasoning_effort": self.reasoning_effort,
            "timeout": self.timeout,
            "label": self.label,
        }


def serialize_primary(assessment: CognitiveImpactAssessment | None) -> dict:
    raw = primary_update(assessment)
    op = raw.get("operation")
    if hasattr(op, "value"):
        op = op.value
    elif op is not None:
        op = str(op)
    return {"operation": op, "target_node_id": raw.get("target_node_id")}


def canonical_effect(item) -> dict:
    if hasattr(item, "as_dict"):
        item = item.as_dict()
    item = item if isinstance(item, dict) else {}
    op = item.get("operation")
    if hasattr(op, "value"):
        op = op.value
    return {
        "target_kernel_node_id": item.get("target_kernel_node_id"),
        "operation": str(op) if op is not None else None,
        "change_magnitude": round(float(item.get("change_magnitude") or 0), 3),
        "epistemic_strength": round(float(item.get("epistemic_strength") or 0), 3),
        "target_importance": round(float(item.get("target_importance") or 0), 3),
        "reason": item.get("reason") or "",
        "exploration_candidate": bool(item.get("exploration_candidate")),
    }


def _effect_key(item: dict) -> tuple:
    return (
        item.get("operation"),
        item.get("target_kernel_node_id"),
        item.get("reason"),
        item.get("change_magnitude"),
    )


def _stringify_update(raw) -> dict | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    op = raw.get("operation")
    if hasattr(op, "value"):
        op = op.value
    elif op is not None:
        op = str(op)
    return {"operation": op, "target_node_id": raw.get("target_node_id")}


def attribute_stages(
    *,
    raw: list[dict],
    grounded: list[dict],
    primary: dict,
    original_grounded: list[dict],
    original_primary: dict | None,
) -> dict:
    grounded_keys = {_effect_key(e) for e in grounded}
    discarded = [e for e in raw if _effect_key(e) not in grounded_keys]
    orig_g = [canonical_effect(e) for e in original_grounded]
    orig_p = _stringify_update(original_primary) or {"operation": None, "target_node_id": None}
    matches_original_grounded = canonical_json(grounded) == canonical_json(orig_g)
    matches_original_primary = canonical_json(primary) == canonical_json(orig_p)

    likely = None
    if discarded:
        likely = "grounding"
    if not matches_original_grounded:
        likely = "raw_generation"
    elif matches_original_grounded and not matches_original_primary:
        likely = "primary_selection"

    return {
        "raw_count": len(raw),
        "grounded_count": len(grounded),
        "discarded_count": len(discarded),
        "discarded": discarded,
        "matches_original_grounded": matches_original_grounded,
        "matches_original_primary": matches_original_primary,
        "likely_stage": likely,
        "notes": (
            "likely_stage locates where this replay diverged from the frozen AnalysisRun "
            "and/or where grounding discarded raw effects. It is attribution, not scoring."
        ),
    }


def make_impact_provider(config: ImpactReplayConfig, *, chat_fn=None):
    kind = (config.provider or settings.cognitive_provider or "rule").lower()
    rule = RuleBasedCognitiveProvider()
    if kind == "rule":
        rule.stage_provenance = {"impact": {"provider": "rule", "status": "success"}}
        return rule
    base = STAGE_RUNTIME["impact"]
    impact_runtime = StageRuntime(
        thinking=config.thinking or base.thinking,  # type: ignore[arg-type]
        reasoning_effort=config.reasoning_effort or base.reasoning_effort,  # type: ignore[arg-type]
        timeout=float(config.timeout if config.timeout is not None else base.timeout),
    )
    model = ModelBackedCognitiveProvider(
        chat_fn=chat_fn,
        model=config.model,
        impact_runtime=impact_runtime,
    )
    return FallbackProvider(model, rule)


def _runtime_from_provider(provider) -> dict:
    provenance = getattr(provider, "stage_provenance", None) or {}
    impact_rec = provenance.get("impact") if isinstance(provenance, dict) else {}
    stage_runtime = getattr(provider, "last_stage_runtime", None) or {}
    if not impact_rec and hasattr(provider, "primary"):
        stage_runtime = getattr(provider.primary, "last_stage_runtime", None) or stage_runtime
        provenance = getattr(provider, "stage_provenance", None) or {}
        impact_rec = provenance.get("impact") if isinstance(provenance, dict) else {}
    meta = getattr(provider, "last_meta", None) or {}
    return {
        "provider_type": getattr(provider, "provider_type", None),
        "fallback_used": bool(getattr(provider, "fallback_used", False)),
        "model": impact_rec.get("model") or meta.get("model"),
        "thinking": impact_rec.get("thinking") if impact_rec.get("thinking") is not None else stage_runtime.get("thinking"),
        "reasoning_effort": impact_rec.get("reasoning_effort")
        if impact_rec.get("reasoning_effort") is not None
        else stage_runtime.get("reasoning_effort"),
        "timeout": impact_rec.get("timeout") if impact_rec.get("timeout") is not None else stage_runtime.get("timeout"),
        "latency_ms": impact_rec.get("latency_ms") if impact_rec.get("latency_ms") is not None else meta.get("latency_ms"),
        "prompt_tokens": impact_rec.get("prompt_tokens")
        if impact_rec.get("prompt_tokens") is not None
        else meta.get("prompt_tokens"),
        "completion_tokens": impact_rec.get("completion_tokens")
        if impact_rec.get("completion_tokens") is not None
        else meta.get("completion_tokens"),
        "estimated_cost_usd": impact_rec.get("estimated_cost_usd")
        if impact_rec.get("estimated_cost_usd") is not None
        else meta.get("estimated_cost_usd"),
        "error": impact_rec.get("error"),
        "error_type": impact_rec.get("error_type"),
        "status": impact_rec.get("status") or "success",
        "stage_provenance": provenance.get("impact") if isinstance(provenance, dict) else None,
    }


def replay_frozen_impact(
    snapshot: dict,
    *,
    provider=None,
    config: ImpactReplayConfig | None = None,
    chat_fn=None,
) -> dict:
    config = config or ImpactReplayConfig()
    provider = provider or make_impact_provider(config, chat_fn=chat_fn)
    extraction = extraction_from_snapshot(snapshot)
    matches = matches_from_snapshot(snapshot)
    nodes = kernel_nodes_from_snapshot(snapshot)
    indep = snapshot.get("independence") or {}
    assessment = provider.assess_cognitive_impact(
        snapshot.get("source_text") or "",
        extraction,
        matches,
        is_duplicate=bool(indep.get("is_duplicate")),
        independent_source_count=int(indep.get("independent_source_count") or 1),
        secondary_report_count=int(indep.get("secondary_report_count") or 0),
        threatens_active_work=bool(indep.get("threatens_active_work")),
        nodes=nodes,
    )
    raw_effects = getattr(assessment, "raw_effects", None)
    if raw_effects is None:
        raw_effects = getattr(provider, "last_raw_effects", None) or assessment.effects
    raw = [canonical_effect(e) for e in raw_effects]
    grounded = [canonical_effect(e) for e in assessment.effects]
    primary = serialize_primary(assessment)
    original = snapshot.get("original") or {}
    original_grounded = (original.get("cognitive_impact") or {}).get("effects") or []
    attribution = attribute_stages(
        raw=raw,
        grounded=grounded,
        primary=primary,
        original_grounded=original_grounded,
        original_primary=original.get("update"),
    )
    return {
        "input_fingerprint": snapshot.get("input_fingerprint") or fingerprint_snapshot(snapshot),
        "frozen_input": {
            "schema_version": snapshot.get("schema_version"),
            "analysis_run_id": snapshot.get("analysis_run_id"),
            "input_hash": snapshot.get("input_hash"),
            "kernel_snapshot_hash": snapshot.get("kernel_snapshot_hash"),
            "independence": snapshot.get("independence"),
            "match_count": len(snapshot.get("matches") or []),
            "claim_count": len((snapshot.get("extraction") or {}).get("claims") or []),
        },
        "stages": {
            "frozen_input": snapshot.get("input_fingerprint") or fingerprint_snapshot(snapshot),
            "raw_effects": raw,
            "grounded_effects": grounded,
            "primary_update": primary,
        },
        "attribution": attribution,
        "runtime": _runtime_from_provider(provider),
        "config": config.as_dict(),
        "original_primary_update": _stringify_update(original.get("update")),
    }


def replay_public(row: ImpactReplay) -> dict:
    return {
        "id": str(row.id),
        "analysis_run_id": str(row.analysis_run_id),
        "label": row.label,
        "input_fingerprint": row.input_fingerprint,
        "replay_version": row.replay_version,
        "config": row.config,
        "frozen_input": row.frozen_input,
        "stages": row.stages,
        "attribution": row.attribution,
        "runtime": row.runtime,
        "provenance": row.provenance,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def persist_replay(
    db: Session,
    run: AnalysisRun,
    snapshot: dict,
    result: dict,
    *,
    config: ImpactReplayConfig,
) -> ImpactReplay:
    row = ImpactReplay(
        analysis_run_id=run.id,
        label=config.label,
        input_fingerprint=result["input_fingerprint"],
        replay_version=IMPACT_REPLAY_VERSION,
        config=result.get("config") or config.as_dict(),
        frozen_input=result.get("frozen_input") or {},
        stages=result.get("stages") or {},
        attribution=result.get("attribution") or {},
        runtime=result.get("runtime") or {},
        provenance={
            "analysis_run_id": str(run.id),
            "kernel_snapshot_hash": run.kernel_snapshot_hash,
            "input_hash": run.input_hash,
            "original_provider_type": run.provider_type,
            "original_model_name": run.model_name,
            "impact_assessor_version": IMPACT_ASSESSOR_VERSION,
            "impact_replay_version": IMPACT_REPLAY_VERSION,
        },
        error=(result.get("runtime") or {}).get("error"),
    )
    db.add(row)
    db.flush()
    return row


def replay_analysis_run(
    db: Session,
    run_id: UUID,
    *,
    config: ImpactReplayConfig | None = None,
    chat_fn=None,
    persist: bool = True,
) -> dict:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(404, "AnalysisRun not found")
    before_payload = deepcopy(run.result_payload)
    snapshot = frozen_impact_input_from_run(db, run)
    config = config or ImpactReplayConfig()
    result = replay_frozen_impact(snapshot, config=config, chat_fn=chat_fn)
    row = None
    if persist:
        row = persist_replay(db, run, snapshot, result, config=config)
    db.refresh(run)
    if run.result_payload != before_payload:
        raise RuntimeError("Impact replay mutated AnalysisRun.result_payload")
    out = dict(result)
    if row is not None:
        out["id"] = str(row.id)
        out["provenance"] = row.provenance
        out["replay_version"] = row.replay_version
        out["created_at"] = row.created_at.isoformat() if row.created_at else None
    return out


def list_replays_for_run(db: Session, run_id: UUID) -> list[ImpactReplay]:
    return (
        db.execute(
            select(ImpactReplay)
            .where(ImpactReplay.analysis_run_id == run_id)
            .order_by(ImpactReplay.created_at.desc(), ImpactReplay.id.desc())
        )
        .scalars()
        .all()
    )


def compare_replays(a: dict, b: dict) -> dict:
    stages_a = a.get("stages") or {}
    stages_b = b.get("stages") or {}
    return {
        "same_input": a.get("input_fingerprint") == b.get("input_fingerprint"),
        "input_fingerprint": a.get("input_fingerprint"),
        "config_a": a.get("config"),
        "config_b": b.get("config"),
        "diff": {
            "raw_effects": canonical_json(stages_a.get("raw_effects")) != canonical_json(stages_b.get("raw_effects")),
            "grounded_effects": canonical_json(stages_a.get("grounded_effects"))
            != canonical_json(stages_b.get("grounded_effects")),
            "primary_update": canonical_json(stages_a.get("primary_update"))
            != canonical_json(stages_b.get("primary_update")),
        },
        "a": {
            "id": a.get("id"),
            "primary_update": stages_a.get("primary_update"),
            "raw_count": len(stages_a.get("raw_effects") or []),
            "grounded_count": len(stages_a.get("grounded_effects") or []),
        },
        "b": {
            "id": b.get("id"),
            "primary_update": stages_b.get("primary_update"),
            "raw_count": len(stages_b.get("raw_effects") or []),
            "grounded_count": len(stages_b.get("grounded_effects") or []),
        },
    }
