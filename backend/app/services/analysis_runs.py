from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cognitive.versions import (
    ATTENTION_POLICY_VERSION,
    DELTA_VERSION,
    EMBEDDING_MODEL_VERSION_NONE,
    EVIDENCE_REASONER_VERSION,
    EXTRACTOR_VERSION,
    MATCHER_VERSION,
    PIPELINE_VERSION,
    PROMPT_VERSION,
    PROVIDER_VERSION,
    SCHEDULER_VERSION,
)
from app.config import settings
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelNode, KernelPatch
from app.models.analysis import AnalysisRun
from app.models.scheduler import AttentionFeedback, AttentionPlan
from app.models.source import Source
from app.services.cognitive_impact import visible_prediction_from_frozen
from app.services.attention_feedback import feedback_for_plan, feedback_public


def kernel_snapshot_hash(nodes: list[KernelNode]) -> str:
    payload = [
        {
            "id": str(n.id),
            "type": n.node_type,
            "version": n.current_version,
            "status": n.status,
            "title": n.title,
        }
        for n in sorted(nodes, key=lambda x: str(x.id))
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def input_hash(source: Source, extras: list[Source]) -> str:
    parts = [
        str(source.id),
        source.content_hash or "",
        source.content_text or "",
        source.source_type,
    ]
    for extra in sorted(extras, key=lambda s: str(s.id)):
        parts.extend([str(extra.id), extra.content_hash or "", extra.content_text or ""])
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def identity_key(
    *,
    input_digest: str,
    kernel_digest: str,
    provider_type: str,
    provider_version: str,
    model_name: str | None,
    extractor_version: str,
    matcher_version: str,
    evidence_reasoner_version: str,
    delta_version: str,
    prompt_version: str,
    embedding_model_version: str,
    pipeline_version: str,
) -> str:
    """Cognitive Analysis identity. Scheduler version is intentionally excluded."""
    raw = "|".join(
        [
            input_digest,
            kernel_digest,
            provider_type,
            provider_version,
            model_name or "none",
            extractor_version,
            matcher_version,
            evidence_reasoner_version,
            delta_version,
            prompt_version,
            embedding_model_version or EMBEDDING_MODEL_VERSION_NONE,
            pipeline_version,
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def compute_identity(
    *,
    input_digest: str,
    kernel_digest: str,
    provider_type: str,
    model_name: str | None,
    embedding_model_version: str = EMBEDDING_MODEL_VERSION_NONE,
) -> str:
    return identity_key(
        input_digest=input_digest,
        kernel_digest=kernel_digest,
        provider_type=provider_type.split("+")[0],
        provider_version=PROVIDER_VERSION,
        model_name=model_name,
        extractor_version=EXTRACTOR_VERSION,
        matcher_version=MATCHER_VERSION,
        evidence_reasoner_version=EVIDENCE_REASONER_VERSION,
        delta_version=DELTA_VERSION,
        prompt_version=PROMPT_VERSION,
        embedding_model_version=embedding_model_version,
        pipeline_version=PIPELINE_VERSION,
    )


def find_completed_run(db: Session, key: str) -> AnalysisRun | None:
    return (
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.identity_key == key, AnalysisRun.status == "COMPLETED")
            .order_by(AnalysisRun.completed_at.desc(), AnalysisRun.created_at.desc())
        )
        .scalars()
        .first()
    )


def find_live_run(db: Session, key: str) -> AnalysisRun | None:
    return (
        db.execute(
            select(AnalysisRun)
            .where(
                AnalysisRun.identity_key == key,
                AnalysisRun.status.in_(("RUNNING", "COMPLETED")),
            )
            .order_by(AnalysisRun.created_at.desc())
        )
        .scalars()
        .first()
    )


def latest_run_for_source(db: Session, source_id: UUID) -> AnalysisRun | None:
    return (
        db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.source_id == source_id, AnalysisRun.status == "COMPLETED")
            .order_by(AnalysisRun.completed_at.desc(), AnalysisRun.created_at.desc())
        )
        .scalars()
        .first()
    )


def next_attempt(db: Session, key: str) -> int:
    rows = db.execute(select(AnalysisRun.attempt).where(AnalysisRun.identity_key == key)).all()
    if not rows:
        return 1
    return max(int(r[0] or 1) for r in rows) + 1


def supersede_completed(db: Session, key: str) -> None:
    rows = (
        db.execute(select(AnalysisRun).where(AnalysisRun.identity_key == key, AnalysisRun.status == "COMPLETED"))
        .scalars()
        .all()
    )
    for row in rows:
        row.status = "SUPERSEDED"
    if rows:
        db.flush()


def new_run(
    db: Session,
    *,
    source_id: UUID,
    extra_ids: list[str],
    identity: str,
    in_hash: str,
    k_hash: str,
    provider_type: str,
    model_name: str | None,
    embedding_model_version: str = EMBEDDING_MODEL_VERSION_NONE,
) -> AnalysisRun:
    run = AnalysisRun(
        source_id=source_id,
        extra_source_ids=extra_ids,
        identity_key=identity,
        attempt=next_attempt(db, identity),
        extractor_version=EXTRACTOR_VERSION,
        matcher_version=MATCHER_VERSION,
        evidence_reasoner_version=EVIDENCE_REASONER_VERSION,
        delta_version=DELTA_VERSION,
        scheduler_version=settings.scheduler_version or SCHEDULER_VERSION,
        prompt_version=PROMPT_VERSION,
        provider_version=PROVIDER_VERSION,
        embedding_model_version=embedding_model_version,
        pipeline_version=PIPELINE_VERSION,
        provider_type=provider_type,
        model_name=model_name,
        input_hash=in_hash,
        kernel_snapshot_hash=k_hash,
        status="RUNNING",
        result_payload={},
        stage_provenance=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    return run


def acquire_run(
    db: Session,
    *,
    source_id: UUID,
    extra_ids: list[str],
    identity: str,
    in_hash: str,
    k_hash: str,
    provider_type: str,
    model_name: str | None,
    embedding_model_version: str,
    reprocess: bool,
) -> tuple[str, AnalysisRun]:
    """Return ('existing'|'created', run). Unique live identity is enforced in the DB."""
    if reprocess:
        supersede_completed(db, identity)
    else:
        existing = find_live_run(db, identity)
        if existing is not None:
            return "existing", existing
    try:
        with db.begin_nested():
            run = new_run(
                db,
                source_id=source_id,
                extra_ids=extra_ids,
                identity=identity,
                in_hash=in_hash,
                k_hash=k_hash,
                provider_type=provider_type,
                model_name=model_name,
                embedding_model_version=embedding_model_version,
            )
        return "created", run
    except IntegrityError:
        existing = find_live_run(db, identity)
        if existing is None:
            raise
        return "existing", existing


def complete_run(
    run: AnalysisRun,
    payload: dict,
    *,
    fallback_used: bool = False,
    meta: dict | None = None,
    stage_provenance: dict | None = None,
) -> None:
    if run.status == "COMPLETED" and run.result_payload:
        raise RuntimeError("AnalysisRun is immutable after COMPLETED")
    meta = meta or {}
    run.status = "COMPLETED"
    run.completed_at = datetime.now(timezone.utc)
    run.result_payload = payload
    run.fallback_used = fallback_used
    run.latency_ms = meta.get("latency_ms")
    run.prompt_tokens = meta.get("prompt_tokens")
    run.completion_tokens = meta.get("completion_tokens")
    run.estimated_cost_usd = meta.get("estimated_cost_usd")
    run.error = None
    if stage_provenance is not None:
        run.stage_provenance = stage_provenance


def fail_run(run: AnalysisRun, error: str) -> None:
    run.status = "FAILED"
    run.completed_at = datetime.now(timezone.utc)
    run.error = error[:4000]


def attention_plans_for_run(db: Session, run_id: UUID) -> list[AttentionPlan]:
    return (
        db.execute(
            select(AttentionPlan)
            .where(AttentionPlan.analysis_run_id == run_id)
            .order_by(AttentionPlan.created_at.desc(), AttentionPlan.id.desc())
        )
        .scalars()
        .all()
    )


def _normalize_public_contract(payload: dict) -> dict:
    """Fill disposition / update / delta_content on read for older stored payloads.

    Historical raw attention_plan / result_payload remain as stored. Current
    top-level public contract uses the same v2.1 interpretation as the latest plan.
    """
    stored = payload.get("attention_plan")
    if isinstance(stored, dict) and not stored.get("disposition"):
        stored = dict(stored)
        if stored.get("attention_state"):
            stored["disposition"] = stored["attention_state"]
        payload["attention_plan"] = stored
    return _apply_current_public_contract(payload)


def _apply_current_public_contract(payload: dict) -> dict:
    """Overlay current v2.1 Δ_t on the HTTP response. Never writes back to AnalysisRun."""
    latest = payload.get("latest_attention_plan")
    if isinstance(latest, dict) and "update" in latest and "delta_content" in latest:
        payload["update"] = latest.get("update")
        payload["delta_content"] = latest.get("delta_content")
        if latest.get("disposition"):
            payload["disposition"] = latest["disposition"]
        return payload

    from app.services.scheduler import matches_from_debug

    stored = payload.get("attention_plan") if isinstance(payload.get("attention_plan"), dict) else {}
    debug = stored.get("score_debug") if isinstance(stored.get("score_debug"), dict) else {}
    impact = debug.get("cognitive_impact") or payload.get("cognitive_impact")
    visible = visible_prediction_from_frozen(
        frozen_impact=impact,
        frozen_matches=matches_from_debug(debug.get("matches")),
        disposition=stored.get("disposition") or payload.get("disposition"),
    )
    payload["update"] = visible["update"]
    payload["delta_content"] = visible["delta_content"]
    if visible.get("disposition"):
        payload["disposition"] = visible["disposition"]
    return payload


def plan_public(plan: AttentionPlan) -> dict:
    debug = plan.score_debug if isinstance(plan.score_debug, dict) else {}
    from app.services.scheduler import matches_from_debug

    visible = visible_prediction_from_frozen(
        frozen_impact=debug.get("cognitive_impact"),
        frozen_matches=matches_from_debug(debug.get("matches")),
        disposition=plan.disposition,
    )
    return {
        "id": str(plan.id),
        "disposition": plan.disposition,
        "update": visible["update"],
        "delta_content": visible["delta_content"],
        "urgency": plan.urgency,
        "cognitive_budget_minutes": plan.cognitive_budget_minutes,
        "kernel_target_ids": plan.kernel_target_ids,
        "expected_output": plan.expected_output,
        "reason": plan.reason,
        "watch_after_processing": plan.watch_after_processing,
        "scheduler_version": plan.scheduler_version,
        "attention_policy_version": plan.attention_policy_version or ATTENTION_POLICY_VERSION,
        "runtime_context_id": str(plan.runtime_context_id) if plan.runtime_context_id else None,
        "runtime_snapshot": plan.runtime_snapshot or {},
        "score_debug": plan.score_debug,
        "analysis_run_id": str(plan.analysis_run_id) if plan.analysis_run_id else None,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def hydrate_run(db: Session, run: AnalysisRun) -> dict:
    payload = dict(run.result_payload or {})
    patches = payload.get("kernel_patches") or []
    ids = [UUID(p["id"]) for p in patches if p.get("id")]
    if ids:
        rows = db.execute(select(KernelPatch).where(KernelPatch.id.in_(ids))).scalars().all()
        by_id = {str(p.id): p for p in rows}

        def _p(row: KernelPatch) -> dict:
            return {
                "id": str(row.id),
                "target_object_type": row.target_object_type,
                "target_object_id": str(row.target_object_id) if row.target_object_id else None,
                "change_type": row.change_type,
                "status": row.status,
                "reasoning": row.reasoning,
                "proposed_state": row.proposed_state,
                "current_state": row.current_state,
                "suggested_confidence_change": row.suggested_confidence_change,
            }

        payload["kernel_patches"] = [
            _p(by_id[p["id"]]) if p.get("id") in by_id else p for p in patches
        ]
    payload["analysis_run"] = run_public(run)
    plans = attention_plans_for_run(db, run.id)
    payload["original_attention_plan"] = payload.get("attention_plan")
    if plans:
        payload["latest_attention_plan"] = plan_public(plans[0])
        payload["attention_plan_history"] = [plan_public(p) for p in plans]
        latest_feedback = feedback_for_plan(db, plans[0].id)
        payload["attention_feedback"] = [feedback_public(f) for f in latest_feedback]
        payload["latest_attention_feedback"] = feedback_public(latest_feedback[0]) if latest_feedback else None
    else:
        payload["latest_attention_plan"] = payload.get("attention_plan")
        payload["attention_plan_history"] = [payload["attention_plan"]] if payload.get("attention_plan") else []
        payload["attention_feedback"] = []
        payload["latest_attention_feedback"] = None
    return _normalize_public_contract(payload)


def run_public(run: AnalysisRun) -> dict:
    return {
        "id": str(run.id),
        "source_id": str(run.source_id),
        "status": run.status,
        "attempt": run.attempt,
        "identity_key": run.identity_key,
        "extractor_version": run.extractor_version,
        "matcher_version": run.matcher_version,
        "evidence_reasoner_version": run.evidence_reasoner_version,
        "delta_version": run.delta_version,
        "scheduler_version": run.scheduler_version,
        "prompt_version": run.prompt_version,
        "provider_version": run.provider_version,
        "embedding_model_version": run.embedding_model_version,
        "pipeline_version": run.pipeline_version,
        "provider_type": run.provider_type,
        "model_name": run.model_name,
        "input_hash": run.input_hash,
        "kernel_snapshot_hash": run.kernel_snapshot_hash,
        "fallback_used": run.fallback_used,
        "stage_provenance": run.stage_provenance,
        "latency_ms": run.latency_ms,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "estimated_cost_usd": run.estimated_cost_usd,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error": run.error,
    }
