from datetime import datetime, timezone
import threading
import time
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, engine, get_db
from app.execution_integrity import require_side_effects_authorized
from app.models.event import EventEvidenceFrame, RepresentationAuditRun
from app.models.source import Source, SourceEdge
from app.schemas.api import SourceCreate, SourceEdgeCreate, SourceOut
from app.services.ingestion import ingest_observation, ingest_pdf, ingest_text, ingest_url
from app.services.information_landscape import source_information_landscape
from app.services.same_event_candidates import same_event_candidates, same_event_frame_candidates
from app.services.representation_authority import simulate_representation_authority
from app.services.representation_belief import source_representation_beliefs
from app.services.source_graph import independence_report, persist_source_edge, resolve_references
from app.services.source_surface import is_user_visible_source_clause
from app.services.source_versions import current_source_id, source_version_ids

router = APIRouter()

_COMPACT_SOURCE_LOCK = threading.Lock()
_COMPACT_SOURCE_CACHE: list[SourceOut] | None = None
_COMPACT_SOURCE_CACHE_BUILT_AT = 0.0
_COMPACT_SOURCE_REFRESHING = False
_COMPACT_SOURCE_TTL_SECONDS = 5.0

_COMPACT_METADATA_KEYS = {
    "abstract",
    "acquisition",
    "affiliations",
    "author",
    "authors",
    "feed_fallback",
    "hero_image_alt",
    "hero_image_cached_url",
    "hero_image_url",
    "paper_lead_figure_url",
    "paper_profile",
    "paper_title",
    "paper_word_count",
    "primary_category",
    "published",
    "publisher_dynamic_media_status",
    "social_author",
    "social_platform",
}


def _compact_source_out(row: Source) -> SourceOut:
    payload = SourceOut.model_validate(row).model_dump()
    text = payload.get("content_text") or ""
    if len(text) > 600:
        payload["content_text"] = text[:600].rstrip() + "…"
    metadata = dict(payload.get("raw_metadata") or {})
    payload["raw_metadata"] = {
        key: metadata[key]
        for key in _COMPACT_METADATA_KEYS
        if key in metadata
    }
    return SourceOut(**payload)


def _query_compact_sources(db: Session) -> list[SourceOut]:
    rows = (
        db.execute(
            select(Source)
            .where(*is_user_visible_source_clause())
            .order_by(Source.ingested_at.desc(), Source.id.desc())
        )
        .scalars()
        .all()
    )
    return [_compact_source_out(row) for row in rows]


def _refresh_compact_source_cache_background() -> None:
    global _COMPACT_SOURCE_CACHE
    global _COMPACT_SOURCE_CACHE_BUILT_AT
    global _COMPACT_SOURCE_REFRESHING

    db = SessionLocal()
    try:
        payload = _query_compact_sources(db)
        with _COMPACT_SOURCE_LOCK:
            _COMPACT_SOURCE_CACHE = payload
            _COMPACT_SOURCE_CACHE_BUILT_AT = time.monotonic()
    finally:
        db.close()
        with _COMPACT_SOURCE_LOCK:
            _COMPACT_SOURCE_REFRESHING = False


def _compact_source_snapshot(db: Session) -> list[SourceOut]:
    global _COMPACT_SOURCE_CACHE
    global _COMPACT_SOURCE_CACHE_BUILT_AT
    global _COMPACT_SOURCE_REFRESHING

    now = time.monotonic()
    with _COMPACT_SOURCE_LOCK:
        payload = _COMPACT_SOURCE_CACHE
        age = now - _COMPACT_SOURCE_CACHE_BUILT_AT
        if payload is not None and age < _COMPACT_SOURCE_TTL_SECONDS:
            return payload
        if payload is not None:
            if not _COMPACT_SOURCE_REFRESHING:
                _COMPACT_SOURCE_REFRESHING = True
                threading.Thread(
                    target=_refresh_compact_source_cache_background,
                    name="raos-compact-source-refresh",
                    daemon=True,
                ).start()
            return payload

    payload = _query_compact_sources(db)
    with _COMPACT_SOURCE_LOCK:
        _COMPACT_SOURCE_CACHE = payload
        _COMPACT_SOURCE_CACHE_BUILT_AT = time.monotonic()
    return payload


def warm_compact_source_cache() -> None:
    """Prebuild the canonical User-Space Source projection off the request path."""
    global _COMPACT_SOURCE_CACHE
    global _COMPACT_SOURCE_CACHE_BUILT_AT

    db = SessionLocal()
    try:
        payload = _query_compact_sources(db)
        with _COMPACT_SOURCE_LOCK:
            _COMPACT_SOURCE_CACHE = payload
            _COMPACT_SOURCE_CACHE_BUILT_AT = time.monotonic()
    finally:
        db.close()


def invalidate_compact_source_cache() -> None:
    global _COMPACT_SOURCE_CACHE_BUILT_AT
    with _COMPACT_SOURCE_LOCK:
        _COMPACT_SOURCE_CACHE_BUILT_AT = 0.0


@router.post("", response_model=SourceOut)
def create_source(body: SourceCreate, db: Session = Depends(get_db)):
    st = body.source_type.upper()
    try:
        if st in {"TEXT", "POST"}:
            if not body.content_text:
                raise HTTPException(400, "content_text required")
            source = ingest_text(db, body.content_text, title=body.title, publisher=body.publisher)
        elif st in {"URL"}:
            if not body.url:
                raise HTTPException(400, "url required")
            source = ingest_url(db, body.url)
        elif st == "MANUAL_OBSERVATION":
            if not body.content_text:
                raise HTTPException(400, "content_text required")
            source = ingest_observation(db, body.content_text, title=body.title)
        else:
            raise HTTPException(400, f"Unsupported source_type {body.source_type}; use /sources/pdf for PDFs")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    invalidate_compact_source_cache()
    return source


@router.post("/pdf", response_model=SourceOut)
async def create_pdf(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(400, "File exceeds size limit")
    if file.content_type not in {"application/pdf", "application/octet-stream", None}:
        # still allow if filename ends with pdf
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, "MIME validation failed: expected PDF")
    source = ingest_pdf(db, data, filename=file.filename)
    if title:
        source.title = title
    invalidate_compact_source_cache()
    return source


@router.get("", response_model=list[SourceOut])
def list_sources(
    compact: bool = False,
    limit: int | None = None,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if compact and limit is None and offset == 0:
        if db.get_bind() is engine:
            return _compact_source_snapshot(db)
        return _query_compact_sources(db)

    stmt = (
        select(Source)
        .where(*is_user_visible_source_clause())
        .order_by(Source.ingested_at.desc(), Source.id.desc())
    )
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(max(1, min(int(limit), 500)))
    rows = db.execute(stmt).scalars().all()

    if not compact:
        return rows
    return [_compact_source_out(row) for row in rows]


@router.get("/search", response_model=list[SourceOut])
def search_sources(q: str, limit: int = 20, db: Session = Depends(get_db)):
    query = q.strip()
    if not query:
        return []
    limit = max(1, min(limit, 200))
    pattern = f"%{query}%"
    rows = db.execute(
        select(Source)
        .where(
            *is_user_visible_source_clause(),
            or_(
                Source.title.ilike(pattern),
                Source.content_text.ilike(pattern),
                Source.publisher.ilike(pattern),
                Source.canonical_url.ilike(pattern),
            ),
        )
        .order_by(Source.ingested_at.desc(), Source.id.desc())
        .limit(limit)
    ).scalars().all()

    out = []
    for row in rows:
        payload = SourceOut.model_validate(row).model_dump()
        text = payload.get("content_text") or ""
        if len(text) > 900:
            payload["content_text"] = text[:900].rstrip() + "…"
        metadata = dict(payload.get("raw_metadata") or {})
        metadata.pop("paper_body_html", None)
        payload["raw_metadata"] = metadata
        out.append(SourceOut(**payload))
        if len(out) >= limit:
            break
    return out


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: UUID, db: Session = Depends(get_db)):
    resolved_id = current_source_id(db, source_id)
    source = db.get(Source, resolved_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "Source not found")
    return source


@router.get("/{source_id}/landscape")
def get_source_landscape(source_id: UUID, db: Session = Depends(get_db)):
    resolved_id = current_source_id(db, source_id)
    try:
        return source_information_landscape(db, resolved_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{source_id}/same-event-candidates")
def get_same_event_candidates(
    source_id: UUID,
    limit: int = 20,
    max_window_hours: float = 168.0,
    db: Session = Depends(get_db),
):
    resolved_id = current_source_id(db, source_id)
    try:
        return same_event_candidates(
            db,
            resolved_id,
            limit=limit,
            max_window_hours=max_window_hours,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{source_id}/same-event-frame-candidates")
def get_same_event_frame_candidates(
    source_id: UUID,
    source_limit: int = 20,
    max_pairs: int = 100,
    max_window_hours: float = 168.0,
    db: Session = Depends(get_db),
):
    resolved_id = current_source_id(db, source_id)
    try:
        return same_event_frame_candidates(
            db,
            resolved_id,
            source_limit=source_limit,
            max_pairs=max_pairs,
            max_window_hours=max_window_hours,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{source_id}/representation-audits")
def get_representation_audits(
    source_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    resolved_id = current_source_id(db, source_id)
    source = db.get(Source, resolved_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "Source not found")
    frame_ids = list(
        db.execute(
            select(EventEvidenceFrame.id).where(EventEvidenceFrame.source_id == resolved_id)
        ).scalars().all()
    )
    if not frame_ids:
        return {
            "source_id": str(resolved_id),
            "frame_count": 0,
            "audit_count": 0,
            "audits": [],
        }
    rows = db.execute(
        select(RepresentationAuditRun)
        .where(
            or_(
                RepresentationAuditRun.subject_id.in_(frame_ids),
                RepresentationAuditRun.object_id.in_(frame_ids),
            )
        )
        .order_by(RepresentationAuditRun.created_at.desc(), RepresentationAuditRun.id.desc())
        .limit(max(1, min(int(limit), 500)))
    ).scalars().all()
    return {
        "source_id": str(resolved_id),
        "frame_count": len(frame_ids),
        "audit_count": len(rows),
        "audits": [
            {
                "id": str(row.id),
                "audit_type": row.audit_type,
                "subject_type": row.subject_type,
                "subject_id": str(row.subject_id),
                "object_type": row.object_type,
                "object_id": str(row.object_id),
                "input_evidence_digest": row.input_evidence_digest,
                "auditor_contract_version": row.auditor_contract_version,
                "provider": row.provider,
                "model": row.model,
                "judgments": row.judgments,
                "evidence_bundle_refs": row.evidence_bundle_refs,
                "authority_result": row.authority_result,
                "authority_policy_version": row.authority_policy_version,
                "authority_simulation": simulate_representation_authority(row),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.get("/{source_id}/representation-beliefs")
def get_representation_beliefs(
    source_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    resolved_id = current_source_id(db, source_id)
    source = db.get(Source, resolved_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "Source not found")
    return source_representation_beliefs(
        db,
        resolved_id,
        source_ids=source_version_ids(db, resolved_id),
        limit=limit,
    )


@router.get("/{source_id}/references")
def get_references(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    edges = db.execute(select(SourceEdge).where(SourceEdge.source_id == source_id, SourceEdge.relationship == "CITES")).scalars().all()
    refs = []
    for edge in edges:
        target = db.get(Source, edge.target_id)
        refs.append(
            {
                "edge_id": str(edge.id),
                "target_id": str(edge.target_id),
                "title": target.title if target else None,
                "stub": bool(target and target.ingestion_method == "REFERENCE_STUB"),
                "doi": (target.raw_metadata or {}).get("external_ids", {}).get("doi") if target else None,
                "arxiv_id": (target.raw_metadata or {}).get("external_ids", {}).get("arxiv_id") if target else None,
                "confidence": edge.confidence,
            }
        )
    return {"source_id": str(source_id), "references": refs, "count": len(refs)}


@router.post("/{source_id}/resolve-references")
def post_resolve_references(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    return {"resolved": resolve_references(db, source_id, max_depth=1)}


@router.get("/{source_id}/graph")
def get_graph(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    outgoing = db.execute(select(SourceEdge).where(SourceEdge.source_id == source_id)).scalars().all()
    incoming = db.execute(select(SourceEdge).where(SourceEdge.target_id == source_id)).scalars().all()
    related_ids = [source_id] + [e.target_id for e in outgoing] + [e.source_id for e in incoming]
    return {
        "source_id": str(source_id),
        "outgoing": [
            {"id": str(e.id), "target_id": str(e.target_id), "relationship": e.relationship, "confidence": e.confidence}
            for e in outgoing
        ],
        "incoming": [
            {"id": str(e.id), "source_id": str(e.source_id), "relationship": e.relationship, "confidence": e.confidence}
            for e in incoming
        ],
        "independence": independence_report(db, list(dict.fromkeys(related_ids))),
    }


@router.post("/source-edges")
def create_edge(body: SourceEdgeCreate, db: Session = Depends(get_db)):
    try:
        require_side_effects_authorized()
    except RuntimeError as exc:
        raise HTTPException(403, str(exc)) from exc
    edge = persist_source_edge(
        db,
        body.source_id,
        body.target_id,
        body.relationship,
        confidence=body.confidence,
        detected_by="USER",
        evidence=body.evidence,
    )
    return {"id": str(edge.id), "relationship": edge.relationship}
