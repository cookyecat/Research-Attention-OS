from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.source import Source, SourceEdge
from app.schemas.api import SourceCreate, SourceEdgeCreate, SourceOut
from app.services.ingestion import ingest_observation, ingest_pdf, ingest_text, ingest_url
from app.services.source_graph import independence_report, persist_source_edge, resolve_references

router = APIRouter()


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
    return source


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    rows = db.execute(select(Source).where(Source.deleted_at.is_(None)).order_by(Source.ingested_at.desc())).scalars().all()
    return rows


@router.get("/{source_id}", response_model=SourceOut)
def get_source(source_id: UUID, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise HTTPException(404, "Source not found")
    return source


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
