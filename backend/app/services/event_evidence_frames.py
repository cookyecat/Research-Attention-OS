from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import InformationSnapshot
from app.models.analysis import AnalysisRun
from app.models.event import EventEvidenceFrame
from app.models.source import Source

EVENT_EVIDENCE_FRAME_CONTRACT = "event-evidence-frame-v0.2"
DEFAULT_WORKSPACE_ID = "local-default"


def _digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_snapshot_id(db: Session, source_id: UUID) -> UUID | None:
    return db.execute(
        select(InformationSnapshot.id)
        .where(InformationSnapshot.raos_source_id == source_id)
        .order_by(InformationSnapshot.captured_at.desc(), InformationSnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _persist_payload(
    db: Session,
    *,
    source: Source,
    payload: dict,
    analysis_run_id: UUID | None,
    frame_ordinal: int,
    workspace_id: str,
) -> EventEvidenceFrame:
    frame_digest = _digest(payload)
    semantic_input_digest = _digest(
        {
            "semantic_provenance": payload.get("semantic_provenance"),
            "event_key": payload.get("event_key"),
            "event_title": payload.get("event_title"),
            "event_summary": payload.get("event_summary"),
            "actors": payload.get("actors"),
            "actions": payload.get("actions"),
            "affected_systems_populations": payload.get("affected_systems_populations"),
            "uncertainties": payload.get("uncertainties"),
            "claim_evidence": payload.get("claim_evidence"),
            "observation_evidence": payload.get("observation_evidence"),
        }
    )
    identity_key = _digest(
        {
            "workspace_id": workspace_id,
            "source_id": str(source.id),
            "analysis_run_id": str(analysis_run_id) if analysis_run_id else None,
            "frame_contract_version": EVENT_EVIDENCE_FRAME_CONTRACT,
            "frame_ordinal": int(frame_ordinal),
            "frame_digest": frame_digest,
        }
    )
    existing = db.execute(
        select(EventEvidenceFrame).where(EventEvidenceFrame.identity_key == identity_key)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = EventEvidenceFrame(
        identity_key=identity_key,
        workspace_id=workspace_id,
        source_id=source.id,
        source_snapshot_id=_latest_snapshot_id(db, source.id),
        analysis_run_id=analysis_run_id,
        frame_contract_version=EVENT_EVIDENCE_FRAME_CONTRACT,
        semantic_input_digest=semantic_input_digest,
        frame_payload=payload,
        frame_digest=frame_digest,
    )
    db.add(row)
    db.flush()
    return row


def _bridge_source_diagnostics(extraction_diagnostics: dict | None, source_id: UUID) -> dict | None:
    diagnostics = dict(extraction_diagnostics or {})
    for row in diagnostics.get("sources") or []:
        if isinstance(row, dict) and str(row.get("source_id") or "") == str(source_id):
            return row
    return None


def _bridge_payloads(
    *,
    source: Source,
    extraction_diagnostics: dict,
    semantic_provenance: dict,
) -> list[dict]:
    source_diag = _bridge_source_diagnostics(extraction_diagnostics, source.id)
    if source_diag is None:
        return []
    payloads: list[dict] = []
    for raw in source_diag.get("events") or []:
        if not isinstance(raw, dict):
            continue
        projection = raw.get("audited_projection")
        if not isinstance(projection, dict):
            continue
        payloads.append(
            {
                "event_key": projection.get("event_id") or raw.get("event_id"),
                "event_title": None,
                "event_summary": projection.get("sensor_event_summary_diagnostic_only")
                or raw.get("sensor_summary_diagnostic_only")
                or "",
                "semantic_provenance": {
                    **semantic_provenance,
                    "routing_status": projection.get("routing_status") or raw.get("routing_status"),
                    "audited_projection": True,
                },
                "source": {
                    "source_id": str(source.id),
                    "source_type": source.source_type,
                    "publisher": source.publisher,
                    "canonical_url": source.canonical_url,
                    "published_at": source.published_at.isoformat() if source.published_at else None,
                },
                "actors": list(projection.get("actor_objects") or []),
                "actions": list(projection.get("actions_changes") or []),
                "affected_systems_populations": list(
                    projection.get("affected_systems_populations") or []
                ),
                "uncertainties": list(projection.get("uncertainties") or []),
                "rejected_or_unscorable_objects": list(
                    projection.get("rejected_or_unscorable_objects") or []
                ),
                "rendered_event_text": projection.get("rendered_event_text") or "",
                "claim_evidence": [],
                "observation_evidence": [],
                "audit_summary": dict(raw.get("audit") or {}),
            }
        )
    return payloads


def _legacy_payload(
    *,
    source: Source,
    extraction,
    claims,
    observations,
    semantic_provenance: dict,
) -> dict | None:
    event_title = getattr(extraction, "event_title", None) or source.title
    event_summary = getattr(extraction, "event_summary", None) or ""
    if not event_title and not event_summary:
        return None
    return {
        "event_key": None,
        "event_title": event_title,
        "event_summary": event_summary,
        "semantic_provenance": semantic_provenance,
        "evidence_maturity": float(getattr(extraction, "evidence_maturity", 0.0) or 0.0),
        "source": {
            "source_id": str(source.id),
            "source_type": source.source_type,
            "publisher": source.publisher,
            "canonical_url": source.canonical_url,
            "published_at": source.published_at.isoformat() if source.published_at else None,
        },
        "actors": [],
        "actions": [],
        "affected_systems_populations": [],
        "uncertainties": [],
        "claim_evidence": [
            {
                "claim_id": str(row.id),
                "text": row.text,
                "claim_type": str(row.claim_type),
                "attributed_to": row.attributed_to,
                "source_span_text": row.source_span_text,
            }
            for row in claims
        ],
        "observation_evidence": [
            {
                "observation_id": str(row.id),
                "text": row.text,
                "observation_type": str(row.observation_type),
                "source_span_text": row.source_span_text,
            }
            for row in observations
        ],
    }


def persist_event_evidence_frames(
    db: Session,
    *,
    source: Source,
    extraction,
    claims,
    observations,
    analysis_run_id: UUID | None,
    extraction_diagnostics: dict | None,
    semantic_provenance: dict,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> list[EventEvidenceFrame]:
    """Persist 0..N immutable event propositions without granting authority."""
    payloads: list[dict]
    if semantic_provenance.get("mode") == "AUDITED_BRIDGE":
        payloads = _bridge_payloads(
            source=source,
            extraction_diagnostics=dict(extraction_diagnostics or {}),
            semantic_provenance=semantic_provenance,
        )
    else:
        fallback = _legacy_payload(
            source=source,
            extraction=extraction,
            claims=claims,
            observations=observations,
            semantic_provenance=semantic_provenance,
        )
        payloads = [fallback] if fallback is not None else []

    return [
        _persist_payload(
            db,
            source=source,
            payload=payload,
            analysis_run_id=analysis_run_id,
            frame_ordinal=index,
            workspace_id=workspace_id,
        )
        for index, payload in enumerate(payloads)
    ]


def backfill_frames_from_analysis_run(
    db: Session,
    run: AnalysisRun,
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> list[EventEvidenceFrame]:
    """Append frames from a completed historical AnalysisRun without re-running cognition."""
    if run.status != "COMPLETED":
        return []
    payload = dict(run.result_payload or {})
    extraction_path = dict(payload.get("extraction_path") or {})
    diagnostics = dict(extraction_path.get("diagnostics") or {})
    if extraction_path.get("mode") != "bridge":
        return []
    source = db.get(Source, run.source_id)
    if source is None:
        return []

    bridge_execution = extraction_path.get("bridge_execution")
    semantic_provenance = {
        "mode": "AUDITED_BRIDGE",
        "authority": "SEMANTIC_AUDITED",
        "bridge_execution": bridge_execution,
        "historical_backfill": True,
        "analysis_run_id": str(run.id),
    }
    bridge_payloads = _bridge_payloads(
        source=source,
        extraction_diagnostics=diagnostics,
        semantic_provenance=semantic_provenance,
    )
    return [
        _persist_payload(
            db,
            source=source,
            payload=frame_payload,
            analysis_run_id=run.id,
            frame_ordinal=index,
            workspace_id=workspace_id,
        )
        for index, frame_payload in enumerate(bridge_payloads)
    ]


def latest_event_evidence_frame(
    db: Session,
    source_id: UUID,
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> EventEvidenceFrame | None:
    frames = latest_event_evidence_frames_for_source(db, source_id, workspace_id=workspace_id)
    return frames[0] if frames else None


def latest_event_evidence_frames_for_source(
    db: Session,
    source_id: UUID,
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> list[EventEvidenceFrame]:
    """Return every frame from the latest AnalysisRun/frame batch for one Source."""
    rows = db.execute(
        select(EventEvidenceFrame)
        .where(
            EventEvidenceFrame.workspace_id == workspace_id,
            EventEvidenceFrame.source_id == source_id,
        )
        .order_by(EventEvidenceFrame.created_at.desc(), EventEvidenceFrame.id.desc())
    ).scalars().all()
    if not rows:
        return []
    latest_run_id = rows[0].analysis_run_id
    latest_contract = rows[0].frame_contract_version
    return [
        row
        for row in rows
        if row.analysis_run_id == latest_run_id and row.frame_contract_version == latest_contract
    ]


def latest_event_evidence_frames(
    db: Session,
    source_ids: list[UUID] | set[UUID] | tuple[UUID, ...],
    *,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> dict[UUID, EventEvidenceFrame]:
    """Cheap retrieval projection: choose one representative latest frame per Source."""
    ids = list(source_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(EventEvidenceFrame)
        .where(
            EventEvidenceFrame.workspace_id == workspace_id,
            EventEvidenceFrame.source_id.in_(ids),
        )
        .order_by(
            EventEvidenceFrame.source_id,
            EventEvidenceFrame.created_at.desc(),
            EventEvidenceFrame.id.desc(),
        )
    ).scalars().all()
    latest: dict[UUID, EventEvidenceFrame] = {}
    for row in rows:
        latest.setdefault(row.source_id, row)
    return latest


def event_frame_retrieval_text(frame: EventEvidenceFrame | None, fallback: Source) -> str:
    if frame is None:
        return " ".join(part for part in (fallback.title, (fallback.content_text or "")[:800]) if part)
    payload = frame.frame_payload or {}
    parts = [
        payload.get("event_title"),
        payload.get("event_summary"),
        payload.get("rendered_event_text"),
    ]
    for row in payload.get("actions") or []:
        if isinstance(row, dict) and row.get("description"):
            parts.append(row["description"])
    for row in payload.get("actors") or []:
        if isinstance(row, dict) and row.get("name"):
            parts.append(row["name"])
    for row in payload.get("claim_evidence") or []:
        if isinstance(row, dict) and row.get("text"):
            parts.append(row["text"])
    return " ".join(str(part) for part in parts if part)
