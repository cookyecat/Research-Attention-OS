from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.manual_observation import ManualObservationConnector
from app.connectors.manual_text import ManualTextConnector
from app.connectors.pdf import PDFConnector
from app.connectors.url import URLConnector
from app.enums import EventStatus, IngestionStatus, SourceType
from app.models.event import Event, EventSource
from app.models.ingestion import IngestionJob, ParserRun
from app.models.source import Source, SourceAuthor
from app.services.fingerprint import NormalizedSource, content_hash, fingerprint
from app.services.source_graph import link_near_duplicates, resolve_references


def persist_normalized(db: Session, normalized: NormalizedSource, *, job: IngestionJob | None = None) -> Source:
    fp = fingerprint(normalized, version=settings.fingerprint_version)
    hashed = content_hash(normalized.content_text)
    source = Source(
        source_type=normalized.source_type,
        title=normalized.title,
        canonical_url=normalized.canonical_url,
        content_text=normalized.content_text,
        published_at=normalized.published_at,
        publisher=normalized.publisher,
        language=normalized.language,
        fingerprint=fp,
        content_hash=hashed,
        ingestion_method=normalized.ingestion_method,
        raw_metadata={
            **(normalized.raw_metadata or {}),
            "external_ids": normalized.external_ids,
            "fingerprint_version": settings.fingerprint_version,
        },
    )
    db.add(source)
    db.flush()
    for name in normalized.author_entities:
        db.add(SourceAuthor(source_id=source.id, author_name=name, author_type=None))
    db.add(
        ParserRun(
            source_id=source.id,
            parser_name=normalized.ingestion_method.lower(),
            parser_version="v1",
            output_metadata={"references": normalized.reference_candidates, "raw_metadata": normalized.raw_metadata},
        )
    )
    db.flush()
    link_near_duplicates(db, source)
    if normalized.reference_candidates:
        resolve_references(db, source.id, max_depth=1)
    if job:
        job.status = IngestionStatus.PERSISTED
        job.finished_at = datetime.now(timezone.utc)
    return source


def ingest_text(db: Session, text: str, title: str | None = None, **metadata) -> Source:
    job = IngestionJob(connector_type="MANUAL_TEXT", input_ref=(title or text[:80]), status=IngestionStatus.NORMALIZING)
    db.add(job)
    db.flush()
    normalized = ManualTextConnector().ingest(text, title=title, **metadata)
    return persist_normalized(db, normalized, job=job)


def ingest_observation(db: Session, text: str, title: str | None = None) -> Source:
    job = IngestionJob(connector_type="MANUAL_OBSERVATION", input_ref=text[:80], status=IngestionStatus.NORMALIZING)
    db.add(job)
    db.flush()
    normalized = ManualObservationConnector().ingest(text, title=title)
    return persist_normalized(db, normalized, job=job)


def ingest_url(db: Session, url: str) -> Source:
    job = IngestionJob(connector_type="URL", input_ref=url, status=IngestionStatus.FETCHING)
    db.add(job)
    db.flush()
    try:
        job.status = IngestionStatus.PARSING
        normalized = URLConnector().ingest(url)
        job.status = IngestionStatus.NORMALIZING
        return persist_normalized(db, normalized, job=job)
    except Exception as exc:
        job.status = IngestionStatus.FETCH_FAILED
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        db.flush()
        raise


def ingest_pdf(db: Session, data: bytes, filename: str | None = None) -> Source:
    job = IngestionJob(connector_type="PDF", input_ref=filename, status=IngestionStatus.PARSING)
    db.add(job)
    db.flush()
    if len(data) > settings.max_upload_bytes:
        job.status = IngestionStatus.PARSE_FAILED
        job.error_message = "File exceeds size limit"
        db.flush()
        raise ValueError("File exceeds size limit")
    normalized = PDFConnector().ingest(data, filename=filename)
    return persist_normalized(db, normalized, job=job)


def attach_or_create_event(db: Session, source: Source, title: str | None, summary: str | None) -> Event:
    event_title = title or source.title or "Untitled event"
    existing = db.execute(select(Event).where(Event.title == event_title)).scalars().first()
    if existing is None and source.content_hash:
        linked = db.execute(
            select(EventSource).join(Source, Source.id == EventSource.source_id).where(
                Source.content_hash == source.content_hash
            )
        ).scalars().first()
        if linked:
            existing = db.get(Event, linked.event_id)
    if existing is None:
        existing = Event(
            title=event_title,
            event_type="PUBLICATION",
            summary=summary or (source.content_text or "")[:400],
            confidence=0.6,
            status=EventStatus.CANDIDATE,
        )
        db.add(existing)
        db.flush()
    already = db.get(EventSource, (existing.id, source.id))
    if already is None:
        db.add(EventSource(event_id=existing.id, source_id=source.id, relationship="REPORTS", confidence=0.7))
        db.flush()
    return existing
