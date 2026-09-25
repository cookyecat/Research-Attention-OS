import threading
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.execution_integrity import require_side_effects_authorized, runtime_profile_hash
from app.models.acquisition import InformationSnapshot
from app.models.analysis import AnalysisRun
from app.models.event import Event, EventMembershipAssertion
from app.models.kernel import KernelNode, KernelPatch, KernelVersion
from app.models.scheduler import AttentionPlan
from app.models.source import Source
from app.schemas.api import KernelNodeCreate, PatchModifyIn
from app.services.analysis_runs import plan_public
from app.services.current_attention import (
    current_attention_plans,
    current_attention_source_map,
)
from app.services.kernel_commit import commit_patch
from app.services.source_versions import current_source_ids
from app.testing.kernel_fixture import seed_mvp_kernel

router = APIRouter()


def _require_kernel_write_authority() -> None:
    try:
        require_side_effects_authorized()
    except RuntimeError as exc:
        raise HTTPException(403, str(exc)) from exc



@router.get("")
def get_kernel(db: Session = Depends(get_db)):
    nodes = db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
    grouped: dict[str, list] = {}
    for node in nodes:
        grouped.setdefault(node.node_type, []).append(
            {
                "id": str(node.id),
                "node_type": node.node_type,
                "title": node.title,
                "status": node.status,
                "current_version": node.current_version,
                "payload": node.payload,
            }
        )
    return grouped


@router.post("/seed")
def seed_kernel(db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    existing = db.execute(select(func.count()).select_from(KernelNode)).scalar_one()
    if existing:
        return {"seeded": False, "reason": "kernel already has nodes"}
    nodes = seed_mvp_kernel(db)
    from app.services.embeddings import refresh_node_embedding

    for node in nodes.values():
        refresh_node_embedding(db, node)
    return {"seeded": True, "ids": {code: str(n.id) for code, n in nodes.items()}}


@router.post("/nodes")
def create_node(body: KernelNodeCreate, db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    # User-authored bootstrap only. AI must use KernelPatch.
    node = KernelNode(
        node_type=body.node_type,
        title=body.title,
        status=body.status,
        payload=body.payload,
        current_version=1,
    )
    db.add(node)
    db.flush()
    db.add(
        KernelVersion(
            kernel_node_id=node.id,
            version=1,
            snapshot={
                "id": str(node.id),
                "node_type": node.node_type,
                "title": node.title,
                "status": node.status,
                "payload": node.payload,
                "current_version": 1,
            },
            committed_by="USER",
        )
    )
    from app.services.embeddings import refresh_node_embedding

    refresh_node_embedding(db, node)
    return {"id": str(node.id), "node_type": node.node_type, "current_version": 1}


@router.get("/nodes/{node_id}/versions")
def node_versions(node_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.execute(select(KernelVersion).where(KernelVersion.kernel_node_id == node_id).order_by(KernelVersion.version))
        .scalars()
        .all()
    )
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "snapshot": r.snapshot,
            "patch_id": str(r.patch_id) if r.patch_id else None,
            "committed_by": r.committed_by,
            "committed_at": r.committed_at.isoformat() if r.committed_at else None,
        }
        for r in rows
    ]


@router.post("/patches")
def create_user_patch(body: dict, db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    from app.services.kernel_commit import create_patch

    patch = create_patch(
        db,
        target_object_type=body["target_object_type"],
        target_object_id=UUID(body["target_object_id"]) if body.get("target_object_id") else None,
        change_type=body["change_type"],
        current_state=body.get("current_state"),
        proposed_state=body["proposed_state"],
        reasoning=body["reasoning"],
        proposed_by=body.get("proposed_by") or "USER",
        evidence_link_ids=body.get("evidence_link_ids") or [],
        suggested_confidence_change=body.get("suggested_confidence_change"),
    )
    return {"id": str(patch.id), "status": patch.status}


@router.get("/patches")
def list_patches(db: Session = Depends(get_db)):
    rows = db.execute(select(KernelPatch).order_by(KernelPatch.created_at.desc())).scalars().all()
    return [_patch(p) for p in rows]


@router.get("/patches/{patch_id}")
def get_patch(patch_id: UUID, db: Session = Depends(get_db)):
    patch = db.get(KernelPatch, patch_id)
    if patch is None:
        raise HTTPException(404, "not found")
    return _patch(patch)


@router.post("/patches/{patch_id}/accept")
def accept_patch(patch_id: UUID, db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    return _patch(commit_patch(db, patch_id, action="accept"))


@router.post("/patches/{patch_id}/modify")
def modify_patch(patch_id: UUID, body: PatchModifyIn, db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    return _patch(commit_patch(db, patch_id, action="modify", modified_state=body.modified_state))


@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: UUID, db: Session = Depends(get_db)):
    _require_kernel_write_authority()
    return _patch(commit_patch(db, patch_id, action="reject"))


def _presentation_score_debug(raw: dict | None) -> dict:
    debug = dict(raw or {})
    out: dict = {}

    cause = debug.get("decision_cause")
    if isinstance(cause, dict):
        out["decision_cause"] = {
            key: cause.get(key)
            for key in (
                "operation",
                "reason",
                "target_kernel_node_id",
                "target_node_type",
            )
            if cause.get(key) is not None
        }

    matches = debug.get("matches")
    if isinstance(matches, list):
        trimmed = []
        for match in matches[:3]:
            if not isinstance(match, dict):
                continue
            trimmed.append({
                key: match.get(key)
                for key in ("node_id", "node_type", "title")
                if match.get(key) is not None
            })
        if trimmed:
            out["matches"] = trimmed

    awareness = debug.get("no_delta_awareness")
    if isinstance(awareness, dict) and awareness.get("applicable"):
        witness_id = awareness.get("witness_event_id")
        events = awareness.get("events")
        witness = None
        if isinstance(events, list):
            witness = next(
                (
                    event
                    for event in events
                    if isinstance(event, dict)
                    and event.get("event_id") == witness_id
                ),
                None,
            )
            if witness is None:
                witness = next(
                    (
                        event
                        for event in events
                        if isinstance(event, dict)
                    ),
                    None,
                )
        compact_awareness = {
            "applicable": True,
            "witness_event_id": witness_id,
        }
        if isinstance(witness, dict):
            d = witness.get("D") if isinstance(witness.get("D"), dict) else {}
            s = witness.get("S") if isinstance(witness.get("S"), dict) else {}
            p = witness.get("P") if isinstance(witness.get("P"), dict) else {}
            compact_awareness["events"] = [{
                "event_id": witness.get("event_id"),
                "D": {
                    "standing_radar_fit": d.get("standing_radar_fit"),
                    "matched_clauses": list(d.get("matched_clauses") or [])[:1],
                },
                "S": {
                    "material_consequence": s.get("material_consequence"),
                    "material_changes": list(s.get("material_changes") or [])[:1],
                    "affected_shared_systems": list(
                        s.get("affected_shared_systems") or []
                    )[:1],
                },
                "P": {
                    "collective_attention_salience": p.get(
                        "collective_attention_salience"
                    ),
                },
            }]
        out["no_delta_awareness"] = compact_awareness

    return out


_COMPACT_ATTENTION_LOCK = threading.Lock()
_COMPACT_ATTENTION_CACHE_PAYLOAD: list[dict] | None = None
_COMPACT_ATTENTION_CACHE_BUILT_AT = 0.0
_COMPACT_ATTENTION_REFRESHING = False
_COMPACT_ATTENTION_TTL_SECONDS = 5.0


def _build_compact_attention(db: Session) -> list[dict]:
    plans = current_attention_plans(db)
    run_ids = {
        p.analysis_run_id
        for p in plans
        if p.analysis_run_id is not None
    }
    run_source_ids = (
        dict(
            db.execute(
                select(
                    AnalysisRun.id,
                    AnalysisRun.source_id,
                ).where(AnalysisRun.id.in_(run_ids))
            ).all()
        )
        if run_ids
        else {}
    )
    representative_source_ids = current_source_ids(
        db,
        set(run_source_ids.values()),
    )
    source_plan_map = current_attention_source_map(db, plans)
    source_ids_by_plan: dict[UUID, list[str]] = {}
    for source_id, plan in source_plan_map.items():
        source_ids_by_plan.setdefault(
            plan.id,
            [],
        ).append(str(source_id))
    for source_ids in source_ids_by_plan.values():
        source_ids.sort()

    return [
        {
            "id": str(p.id),
            "candidate_type": p.candidate_type,
            "candidate_id": str(p.candidate_id),
            "representative_source_id": (
                str(
                    representative_source_ids.get(
                        run_source_ids[p.analysis_run_id],
                        run_source_ids[p.analysis_run_id],
                    )
                )
                if p.analysis_run_id in run_source_ids
                else None
            ),
            "source_ids": source_ids_by_plan.get(p.id, []),
            "disposition": p.disposition,
            "score_debug": _presentation_score_debug(p.score_debug),
            "created_at": (
                p.created_at.isoformat()
                if p.created_at
                else None
            ),
        }
        for p in plans
    ]


def _refresh_compact_attention_background() -> None:
    global _COMPACT_ATTENTION_CACHE_PAYLOAD
    global _COMPACT_ATTENTION_CACHE_BUILT_AT
    global _COMPACT_ATTENTION_REFRESHING

    db = SessionLocal()
    try:
        payload = _build_compact_attention(db)
        with _COMPACT_ATTENTION_LOCK:
            _COMPACT_ATTENTION_CACHE_PAYLOAD = payload
            _COMPACT_ATTENTION_CACHE_BUILT_AT = time.monotonic()
    finally:
        db.close()
        with _COMPACT_ATTENTION_LOCK:
            _COMPACT_ATTENTION_REFRESHING = False


def warm_compact_attention_cache() -> None:
    """Prebuild the canonical compact Attention projection off request paths."""
    global _COMPACT_ATTENTION_CACHE_PAYLOAD
    global _COMPACT_ATTENTION_CACHE_BUILT_AT

    db = SessionLocal()
    try:
        payload = _build_compact_attention(db)
        with _COMPACT_ATTENTION_LOCK:
            _COMPACT_ATTENTION_CACHE_PAYLOAD = payload
            _COMPACT_ATTENTION_CACHE_BUILT_AT = time.monotonic()
    finally:
        db.close()


def _compact_attention_snapshot(db: Session) -> list[dict]:
    global _COMPACT_ATTENTION_CACHE_PAYLOAD
    global _COMPACT_ATTENTION_CACHE_BUILT_AT
    global _COMPACT_ATTENTION_REFRESHING

    now = time.monotonic()
    with _COMPACT_ATTENTION_LOCK:
        payload = _COMPACT_ATTENTION_CACHE_PAYLOAD
        age = now - _COMPACT_ATTENTION_CACHE_BUILT_AT

        if (
            payload is not None
            and age < _COMPACT_ATTENTION_TTL_SECONDS
        ):
            return payload

        if payload is not None:
            if not _COMPACT_ATTENTION_REFRESHING:
                _COMPACT_ATTENTION_REFRESHING = True
                threading.Thread(
                    target=_refresh_compact_attention_background,
                    name="raos-compact-attention-refresh",
                    daemon=True,
                ).start()
            return payload

    payload = _build_compact_attention(db)
    with _COMPACT_ATTENTION_LOCK:
        _COMPACT_ATTENTION_CACHE_PAYLOAD = payload
        _COMPACT_ATTENTION_CACHE_BUILT_AT = time.monotonic()
    return payload


@router.get("/attention")
def list_attention(
    compact: bool = False,
    db: Session = Depends(get_db),
):
    if compact:
        return _compact_attention_snapshot(db)

    plans = current_attention_plans(db)

    run_ids = {
        p.analysis_run_id
        for p in plans
        if p.analysis_run_id is not None
    }
    run_source_ids = (
        dict(
            db.execute(
                select(
                    AnalysisRun.id,
                    AnalysisRun.source_id,
                ).where(AnalysisRun.id.in_(run_ids))
            ).all()
        )
        if run_ids
        else {}
    )
    representative_source_ids = current_source_ids(
        db,
        set(run_source_ids.values()),
    )

    source_ids = set(representative_source_ids.values())
    sources = (
        {
            row.id: row
            for row in db.execute(
                select(Source).where(Source.id.in_(source_ids))
            )
            .scalars()
            .all()
        }
        if source_ids
        else {}
    )

    event_ids = {
        p.candidate_id
        for p in plans
        if str(p.candidate_type).upper() == "EVENT"
    }
    events = (
        {
            row.id: row
            for row in db.execute(
                select(Event).where(Event.id.in_(event_ids))
            )
            .scalars()
            .all()
        }
        if event_ids
        else {}
    )

    out = []
    for p in plans:
        public = plan_public(p)
        run_source_id = (
            run_source_ids.get(p.analysis_run_id)
            if p.analysis_run_id is not None
            else None
        )
        representative = (
            sources.get(
                representative_source_ids.get(
                    run_source_id,
                    run_source_id,
                )
            )
            if run_source_id is not None
            else None
        )
        event = (
            events.get(p.candidate_id)
            if str(p.candidate_type).upper() == "EVENT"
            else None
        )
        out.append(
            {
                "id": str(p.id),
                "candidate_type": p.candidate_type,
                "candidate_id": str(p.candidate_id),
                "representative_source_id": (
                    str(representative.id)
                    if representative
                    else None
                ),
                "event": (
                    {
                        "id": str(event.id),
                        "title": event.title,
                        "event_type": event.event_type,
                        "actors": list(event.actors or []),
                        "action": event.action,
                        "object": event.object,
                        "summary": event.summary,
                        "current_state": event.current_state,
                        "status": event.status,
                        "occurred_at": (
                            event.occurred_at.isoformat()
                            if event.occurred_at
                            else None
                        ),
                        "time_context": event.time_context,
                        "location": event.location,
                        "attributes": dict(event.attributes or {}),
                    }
                    if event is not None
                    else None
                ),
                "disposition": p.disposition,
                "update": public["update"],
                "urgency": p.urgency,
                "reason": p.reason,
                "expected_output": p.expected_output,
                "cognitive_budget_minutes": p.cognitive_budget_minutes,
                "kernel_target_ids": p.kernel_target_ids,
                "score_debug": p.score_debug,
                "created_at": (
                    p.created_at.isoformat()
                    if p.created_at
                    else None
                ),
            }
        )
    return out


def _patch(p: KernelPatch) -> dict:
    return {
        "id": str(p.id),
        "target_object_type": p.target_object_type,
        "target_object_id": str(p.target_object_id) if p.target_object_id else None,
        "change_type": p.change_type,
        "status": p.status,
        "reasoning": p.reasoning,
        "proposed_state": p.proposed_state,
        "current_state": p.current_state,
        "suggested_confidence_change": p.suggested_confidence_change,
        "reviewed_by_user_at": p.reviewed_by_user_at.isoformat() if p.reviewed_by_user_at else None,
    }
