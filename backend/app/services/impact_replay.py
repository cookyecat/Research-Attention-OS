"""Cognitive Impact Replay / Attribution Harness.

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

from app.cognitive.client import thinking_request_fields
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
    FIDELITY_EXACT,
    canonical_json,
    extraction_from_snapshot,
    fingerprint_snapshot,
    frozen_impact_input_from_run,
    kernel_nodes_from_snapshot,
    matches_from_snapshot,
)

EXPERIMENTAL_KEYS = ("provider", "model", "thinking", "reasoning_effort", "timeout")
WIRE_CONDITION_KEYS = ("model", "thinking", "reasoning_effort", "timeout")
NON_EXPERIMENTAL_KEYS = ("label",)
FALLBACK_STATUSES = frozenset({"fallback", "rule-after-fallback", "error"})
INVALIDATING_ERROR_TYPES = frozenset({"timeout", "schema", "LLMTimeoutError", "LLMError"})


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


def _provider_kind(config: dict | None) -> str:
    return str((config or {}).get("provider") or settings.cognitive_provider or "rule").lower()


def is_deterministic_replay(config: dict | None, runtime: dict | None) -> bool:
    runtime = runtime or {}
    if runtime.get("fallback_used") or runtime.get("status") in FALLBACK_STATUSES:
        return False
    kind = _provider_kind(config)
    provider_type = str(runtime.get("provider_type") or kind).lower()
    return kind == "rule" and not provider_type.startswith("model")


def thinking_protocol_label(raw: str | None = None) -> str:
    protocol = (raw if raw is not None else settings.llm_thinking_protocol or "none").strip().lower()
    if protocol in {"deepseek", "thinking"}:
        return "deepseek"
    return "none"


def flatten_thinking_wire(fields: dict | None) -> dict:
    """Collapse thinking_request_fields() into scalar Impact runtime keys."""
    out = {}
    fields = fields or {}
    if "thinking" in fields:
        raw = fields["thinking"]
        out["thinking"] = raw.get("type") if isinstance(raw, dict) else raw
    if "reasoning_effort" in fields:
        out["reasoning_effort"] = fields["reasoning_effort"]
    return out


def wire_effective_model_runtime(
    *,
    thinking: str | None,
    reasoning_effort: str | None,
    timeout,
    model: str | None,
) -> dict:
    """Runtime fields actually placed on the provider/model request.

    protocol=none: thinking / reasoning_effort are omitted.
    deepseek: thinking is sent; reasoning_effort only when thinking=enabled.
    """
    wire = {
        "model": _norm_value(model),
        "timeout": _norm_value(timeout),
    }
    wire.update(flatten_thinking_wire(thinking_request_fields(thinking, reasoning_effort)))
    return wire


def execution_validity(runtime: dict | None) -> dict:
    runtime = runtime or {}
    reasons: list[str] = []
    status = str(runtime.get("status") or "success")
    error_type = runtime.get("error_type")
    if runtime.get("fallback_used") or status in FALLBACK_STATUSES:
        reasons.append("fallback")
    if error_type in INVALIDATING_ERROR_TYPES or error_type == "timeout" or status == "timeout":
        reasons.append("timeout" if "timeout" in str(error_type or status) else "runtime_error")
    elif runtime.get("error") and status != "success":
        reasons.append("runtime_error")
    if status not in {"success"} and "fallback" not in reasons and "runtime_error" not in reasons:
        reasons.append("non_success_status")
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for item in reasons:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return {"valid": not ordered, "reasons": ordered}


def attribute_stages(
    *,
    raw: list[dict],
    grounded: list[dict],
    primary: dict,
    original_grounded: list[dict],
    original_primary: dict | None,
    original_raw: list[dict] | None = None,
    input_fidelity: str | None = None,
    original: dict | None = None,
    runtime: dict | None = None,
    config: dict | None = None,
) -> dict:
    grounded_keys = {_effect_key(e) for e in grounded}
    discarded = [e for e in raw if _effect_key(e) not in grounded_keys]
    orig_g = [canonical_effect(e) for e in original_grounded]
    orig_p = _stringify_update(original_primary) or {"operation": None, "target_node_id": None}
    orig_r = [canonical_effect(e) for e in original_raw] if original_raw is not None else None
    matches_original_grounded = canonical_json(grounded) == canonical_json(orig_g)
    matches_original_primary = canonical_json(primary) == canonical_json(orig_p)
    matches_original_raw = None if orig_r is None else canonical_json(raw) == canonical_json(orig_r)
    observed = {
        "raw_count": len(raw),
        "grounded_count": len(grounded),
        "discarded_count": len(discarded),
        "discarded": discarded,
        "raw_equals_grounded": canonical_json(raw) == canonical_json(grounded),
        "matches_original_raw": matches_original_raw,
        "matches_original_grounded": matches_original_grounded,
        "matches_original_primary": matches_original_primary,
        "stage_diffs": {
            "raw_generation": matches_original_raw is False,
            "grounding": bool(discarded) or (matches_original_raw is True and matches_original_grounded is False),
            "primary_selection": matches_original_grounded and not matches_original_primary,
        },
    }

    insufficient: list[str] = []
    original = original or {}
    validity = execution_validity(runtime)
    if input_fidelity != FIDELITY_EXACT:
        insufficient.append("input_reconstructed")
    if not validity["valid"]:
        insufficient.extend(f"execution_{reason}" for reason in validity["reasons"])
    original_version = original.get("impact_assessor_version")
    if original_version and original_version != IMPACT_ASSESSOR_VERSION:
        insufficient.append("assessor_version_mismatch")
    if not is_deterministic_replay(config, runtime):
        insufficient.append("model_output_variance_possible")
    diverged = (matches_original_raw is False) or (not matches_original_grounded) or (not matches_original_primary)
    if diverged and orig_r is None and not matches_original_grounded:
        insufficient.append("original_raw_effects_unavailable")

    likely = None
    attribution_sufficient = not insufficient
    if attribution_sufficient and diverged:
        if orig_r is not None and matches_original_raw is False:
            likely = "raw_generation"
        elif orig_r is not None and matches_original_raw and not matches_original_grounded:
            likely = "grounding"
        elif matches_original_grounded and not matches_original_primary:
            likely = "primary_selection"
        elif discarded and matches_original_raw is None and not matches_original_grounded:
            attribution_sufficient = False
            insufficient.append("cannot_isolate_raw_vs_grounding")
        elif not matches_original_grounded:
            attribution_sufficient = False
            insufficient.append("cannot_isolate_divergent_stage")
    elif not diverged:
        likely = None

    return {
        "raw_count": observed["raw_count"],
        "grounded_count": observed["grounded_count"],
        "discarded_count": observed["discarded_count"],
        "discarded": discarded,
        "matches_original_grounded": matches_original_grounded,
        "matches_original_primary": matches_original_primary,
        "observed": observed,
        "attribution_sufficient": attribution_sufficient,
        "insufficient_reasons": insufficient,
        "likely_stage": likely if attribution_sufficient else None,
        "notes": (
            "observed reports raw → grounded → primary diffs. likely_stage is set only when "
            "frozen input, versions, and execution conditions support a causal stage judgment."
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
    requested_thinking = (
        impact_rec.get("thinking") if impact_rec.get("thinking") is not None else stage_runtime.get("thinking")
    )
    requested_effort = (
        impact_rec.get("reasoning_effort")
        if impact_rec.get("reasoning_effort") is not None
        else stage_runtime.get("reasoning_effort")
    )
    timeout = impact_rec.get("timeout") if impact_rec.get("timeout") is not None else stage_runtime.get("timeout")
    model = impact_rec.get("model") or meta.get("model")
    fallback = bool(getattr(provider, "fallback_used", False))
    status = impact_rec.get("status") or "success"
    provider_type = getattr(provider, "provider_type", None)
    protocol = thinking_protocol_label()
    requested = {
        "thinking": requested_thinking,
        "reasoning_effort": requested_effort,
        "timeout": timeout,
        "model": model,
    }
    model_path = (not fallback) and str(provider_type or "").lower().startswith("model")
    wire = (
        wire_effective_model_runtime(
            thinking=requested_thinking,
            reasoning_effort=requested_effort,
            timeout=timeout,
            model=model or settings.llm_model,
        )
        if model_path
        else {}
    )
    runtime = {
        "provider_type": provider_type,
        "fallback_used": fallback,
        "model": model,
        "timeout": timeout,
        "requested": requested,
        "wire": wire,
        "thinking_protocol": protocol,
        "thinking": wire.get("thinking"),
        "reasoning_effort": wire.get("reasoning_effort"),
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
        "status": status,
        "stage_provenance": provenance.get("impact") if isinstance(provenance, dict) else None,
    }
    runtime["execution"] = execution_validity(runtime)
    return runtime


def _frozen_input_public(snapshot: dict) -> dict:
    targets = snapshot.get("kernel_targets") or []
    return {
        "schema_version": snapshot.get("schema_version"),
        "analysis_run_id": snapshot.get("analysis_run_id"),
        "input_fidelity": snapshot.get("input_fidelity"),
        "reconstruction_gaps": snapshot.get("reconstruction_gaps") or [],
        "input_hash": snapshot.get("input_hash"),
        "kernel_snapshot_hash": snapshot.get("kernel_snapshot_hash"),
        "independence": snapshot.get("independence"),
        "kernel_targets": targets,
        "fingerprint_coverage": snapshot.get("fingerprint_coverage"),
        "match_count": len(snapshot.get("matches") or []),
        "claim_count": len((snapshot.get("extraction") or {}).get("claims") or []),
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
        nodes=nodes,
    )
    raw_effects = getattr(assessment, "raw_effects", None)
    if raw_effects is None:
        raw_effects = getattr(provider, "last_raw_effects", None) or assessment.effects
    raw = [canonical_effect(e) for e in raw_effects]
    grounded = [canonical_effect(e) for e in assessment.effects]
    primary = serialize_primary(assessment)
    original = snapshot.get("original") or {}
    original_stages = snapshot.get("original_stages") or {}
    original_grounded = original_stages.get("grounded_effects") or (original.get("cognitive_impact") or {}).get("effects") or []
    original_raw = original_stages.get("raw_effects")
    original_primary = original_stages.get("primary_update") or original.get("update")
    runtime = _runtime_from_provider(provider)
    config_dict = config.as_dict()
    attribution = attribute_stages(
        raw=raw,
        grounded=grounded,
        primary=primary,
        original_grounded=original_grounded,
        original_primary=original_primary,
        original_raw=original_raw,
        input_fidelity=snapshot.get("input_fidelity"),
        original=original,
        runtime=runtime,
        config=config_dict,
    )
    fingerprint = snapshot.get("input_fingerprint") or fingerprint_snapshot(snapshot)
    return {
        "input_fingerprint": fingerprint,
        "input_fidelity": snapshot.get("input_fidelity"),
        "frozen_input": _frozen_input_public(snapshot),
        "stages": {
            "frozen_input": fingerprint,
            "raw_effects": raw,
            "grounded_effects": grounded,
            "primary_update": primary,
        },
        "attribution": attribution,
        "runtime": runtime,
        "config": config_dict,
        "original_primary_update": _stringify_update(original_primary),
        "repeatability": {
            "deterministic": is_deterministic_replay(config_dict, runtime),
            "input_identity_required": True,
            "stage_identity_required": is_deterministic_replay(config_dict, runtime),
        },
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
            "input_fidelity": snapshot.get("input_fidelity"),
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


def _norm_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, float):
        return round(value, 6)
    return value


def declared_experimental_config(config: dict | None) -> dict:
    config = config or {}
    return {key: _norm_value(config.get(key)) for key in EXPERIMENTAL_KEYS}


def resolved_declared_config(config: dict | None) -> dict:
    """Requested experimental knobs after provider defaults. Label is omitted."""
    config = config or {}
    kind = _provider_kind(config)
    if kind == "rule":
        return {
            "provider": "rule",
            "model": None,
            "thinking": None,
            "reasoning_effort": None,
            "timeout": None,
        }
    base = STAGE_RUNTIME["impact"]
    return {
        "provider": "model",
        "model": config.get("model") or settings.llm_model,
        "thinking": config.get("thinking") or base.thinking,
        "reasoning_effort": config.get("reasoning_effort")
        if config.get("reasoning_effort") is not None
        else base.reasoning_effort,
        "timeout": float(config["timeout"]) if config.get("timeout") is not None else float(base.timeout),
    }


def _wire_from_replay(replay: dict) -> dict:
    """Actual provider/model request fields that governed this replay."""
    runtime = replay.get("runtime") or {}
    config = replay.get("config") or {}
    wire = runtime.get("wire")
    if isinstance(wire, dict) and wire:
        return {key: _norm_value(wire[key]) for key in WIRE_CONDITION_KEYS if key in wire}
    fallback = bool(runtime.get("fallback_used")) or runtime.get("status") in FALLBACK_STATUSES
    kind = _provider_kind(config)
    provider_type = str(runtime.get("provider_type") or kind).lower()
    if fallback or kind == "rule" or provider_type == "rule":
        return {}
    requested = runtime.get("requested") if isinstance(runtime.get("requested"), dict) else {}
    resolved = resolved_declared_config(config)
    recomputed = wire_effective_model_runtime(
        thinking=requested.get("thinking") or runtime.get("thinking") or resolved.get("thinking"),
        reasoning_effort=(
            requested.get("reasoning_effort")
            if requested.get("reasoning_effort") is not None
            else resolved.get("reasoning_effort")
        ),
        timeout=(
            requested.get("timeout")
            if requested.get("timeout") is not None
            else (runtime.get("timeout") if runtime.get("timeout") is not None else resolved.get("timeout"))
        ),
        model=requested.get("model") or runtime.get("model") or resolved.get("model"),
    )
    return {key: _norm_value(recomputed[key]) for key in WIRE_CONDITION_KEYS if key in recomputed}


def effective_conditions(replay: dict) -> dict:
    """Runtime conditions that actually governed this Impact execution.

    thinking / reasoning_effort appear only when they were placed on the wire.
    """
    runtime = replay.get("runtime") or {}
    config = replay.get("config") or {}
    validity = runtime.get("execution") or execution_validity(runtime)
    fallback = bool(runtime.get("fallback_used")) or runtime.get("status") in FALLBACK_STATUSES
    kind = _provider_kind(config)
    provider_type = str(runtime.get("provider_type") or kind).lower()
    if fallback:
        provider = "rule-fallback"
    elif kind == "rule" or provider_type == "rule":
        provider = "rule"
    else:
        provider = "model"
    cond = {"provider": provider}
    if provider == "model":
        cond.update(_wire_from_replay(replay))
    return {
        **cond,
        "execution_valid": bool(validity.get("valid")),
        "fallback_used": fallback,
        "error_type": runtime.get("error_type"),
        "status": runtime.get("status") or "success",
        "thinking_protocol": runtime.get("thinking_protocol") or thinking_protocol_label(),
    }


def _diff_maps(a: dict, b: dict) -> dict:
    keys = sorted(set(a) | set(b))
    diff = {}
    for key in keys:
        if _norm_value(a.get(key)) != _norm_value(b.get(key)):
            diff[key] = {"a": a.get(key), "b": b.get(key)}
    return diff


def compare_replays(a: dict, b: dict) -> dict:
    stages_a = a.get("stages") or {}
    stages_b = b.get("stages") or {}
    fidelity_a = a.get("input_fidelity") or (a.get("frozen_input") or {}).get("input_fidelity")
    fidelity_b = b.get("input_fidelity") or (b.get("frozen_input") or {}).get("input_fidelity")
    same_input = a.get("input_fingerprint") == b.get("input_fingerprint")
    declared_raw = _diff_maps(declared_experimental_config(a.get("config")), declared_experimental_config(b.get("config")))
    declared_resolved = _diff_maps(resolved_declared_config(a.get("config")), resolved_declared_config(b.get("config")))
    cond_a = effective_conditions(a)
    cond_b = effective_conditions(b)
    effective_keys = ("provider", "model", "thinking", "reasoning_effort", "timeout")
    effective_a = {key: cond_a.get(key) for key in effective_keys if key in cond_a}
    effective_b = {key: cond_b.get(key) for key in effective_keys if key in cond_b}
    effective_diff = _diff_maps(effective_a, effective_b)
    validity_a = (a.get("runtime") or {}).get("execution") or execution_validity(a.get("runtime"))
    validity_b = (b.get("runtime") or {}).get("execution") or execution_validity(b.get("runtime"))
    invalid_reasons: list[str] = []
    if not same_input:
        invalid_reasons.append("frozen_input_mismatch")
    if fidelity_a != FIDELITY_EXACT or fidelity_b != FIDELITY_EXACT:
        invalid_reasons.append("input_not_exact")
    if not validity_a.get("valid"):
        invalid_reasons.extend(f"a_{reason}" for reason in validity_a.get("reasons") or ["execution_invalid"])
    if not validity_b.get("valid"):
        invalid_reasons.extend(f"b_{reason}" for reason in validity_b.get("reasons") or ["execution_invalid"])
    if cond_a.get("fallback_used") or cond_b.get("fallback_used"):
        if "fallback" not in " ".join(invalid_reasons):
            invalid_reasons.append("fallback")
    if cond_a.get("error_type") in INVALIDATING_ERROR_TYPES or cond_b.get("error_type") in INVALIDATING_ERROR_TYPES:
        invalid_reasons.append("runtime_error_or_timeout")
    single_effective = len(effective_diff) == 1
    execution_ok = bool(validity_a.get("valid")) and bool(validity_b.get("valid"))
    controlled_single_variable = same_input and execution_ok and single_effective
    if same_input and execution_ok and not single_effective:
        if not effective_diff:
            invalid_reasons.append("no_effective_variable_difference")
        else:
            invalid_reasons.append("multiple_effective_variables")
    if declared_raw and not effective_diff:
        invalid_reasons.append("declared_experiment_variable_not_effective")
    # Dedup reasons
    seen = set()
    ordered_reasons = []
    for item in invalid_reasons:
        if item not in seen:
            seen.add(item)
            ordered_reasons.append(item)
    exact_input = fidelity_a == FIDELITY_EXACT and fidelity_b == FIDELITY_EXACT
    causal = controlled_single_variable and exact_input
    return {
        "same_input": same_input,
        "input_fingerprint": a.get("input_fingerprint"),
        "input_fidelity_a": fidelity_a,
        "input_fidelity_b": fidelity_b,
        "exact_frozen_input": exact_input,
        "config_a": a.get("config"),
        "config_b": b.get("config"),
        "ignored_fields": list(NON_EXPERIMENTAL_KEYS),
        "declared_variable_diff": declared_raw,
        "resolved_declared_variable_diff": declared_resolved,
        "effective_conditions_a": cond_a,
        "effective_conditions_b": cond_b,
        "variable_diff": effective_diff,
        "single_effective_variable": single_effective,
        "controlled_single_variable": controlled_single_variable,
        "causal_comparison": causal,
        "execution_valid": execution_ok,
        "invalid_reasons": ordered_reasons,
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


def repeatability_report(first: dict, second: dict) -> dict:
    same_input = first.get("input_fingerprint") == second.get("input_fingerprint")
    stages_identical = canonical_json(first.get("stages")) == canonical_json(second.get("stages"))
    deterministic = is_deterministic_replay(first.get("config"), first.get("runtime")) and is_deterministic_replay(
        second.get("config"), second.get("runtime")
    )
    harness_ok = same_input and (stages_identical if deterministic else True)
    return {
        "input_reproducible": same_input,
        "stages_identical": stages_identical,
        "deterministic": deterministic,
        "model_repeatable": None if deterministic else stages_identical,
        "harness_ok": harness_ok,
        "harness_failure": not harness_ok,
        "notes": (
            "Identical frozen-input fingerprints are required. "
            "Stage-for-stage equality is a harness requirement only for deterministic/rule providers. "
            "LLM raw/grounded/primary jitter is model output variance, not a harness failure."
        ),
    }
