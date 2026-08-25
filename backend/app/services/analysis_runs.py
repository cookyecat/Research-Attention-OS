from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cognitive.versions import (
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
from app.models.source import Source


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
    model_name: str | None,
    prompt_version: str,
    pipeline_version: str,
) -> str:
    raw = "|".join(
        [
            input_digest,
            kernel_digest,
            provider_type,
            model_name or "none",
            prompt_version,
            pipeline_version,
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()


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
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()
    return run


def complete_run(run: AnalysisRun, payload: dict, *, fallback_used: bool = False, meta: dict | None = None) -> None:
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


def fail_run(run: AnalysisRun, error: str) -> None:
    run.status = "FAILED"
    run.completed_at = datetime.now(timezone.utc)
    run.error = error[:4000]


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
    return payload


def run_public(run: AnalysisRun) -> dict:
    return {
        "id": str(run.id),
        "source_id": str(run.source_id),
        "status": run.status,
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
        "latency_ms": run.latency_ms,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "estimated_cost_usd": run.estimated_cost_usd,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error": run.error,
    }
