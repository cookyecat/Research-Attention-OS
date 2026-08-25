from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import DetectedBy, SourceEdgeRelationship, SourceType
from app.models.ingestion import ParserRun
from app.models.source import Source, SourceEdge
from app.services.fingerprint import NormalizedSource, content_hash, fingerprint
from app.services.references import extract_reference_candidates


def persist_source_edge(
    db: Session,
    source_id: UUID,
    target_id: UUID,
    relationship: str,
    *,
    confidence: float = 1.0,
    detected_by: str = DetectedBy.PARSER,
    evidence: str | None = None,
) -> SourceEdge:
    existing = db.execute(
        select(SourceEdge).where(
            SourceEdge.source_id == source_id,
            SourceEdge.target_id == target_id,
            SourceEdge.relationship == relationship,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    edge = SourceEdge(
        source_id=source_id,
        target_id=target_id,
        relationship=relationship,
        confidence=confidence,
        detected_by=detected_by,
        evidence=evidence,
    )
    db.add(edge)
    db.flush()
    return edge


def _match_existing(db: Session, doi: str | None, arxiv_id: str | None, url: str | None, title: str | None) -> Source | None:
    conditions = []
    if doi:
        fp = fingerprint(
            NormalizedSource(source_type="PAPER", external_ids={"doi": doi}, ingestion_method="REFERENCE_STUB")
        )
        conditions.append(Source.fingerprint == fp)
    if arxiv_id:
        fp = fingerprint(
            NormalizedSource(source_type="PAPER", external_ids={"arxiv_id": arxiv_id}, ingestion_method="REFERENCE_STUB")
        )
        conditions.append(Source.fingerprint == fp)
    if url:
        fp = fingerprint(NormalizedSource(source_type="URL", canonical_url=url, ingestion_method="REFERENCE_STUB"))
        conditions.append(Source.fingerprint == fp)
    if conditions:
        found = db.execute(select(Source).where(or_(*conditions), Source.deleted_at.is_(None))).scalars().first()
        if found:
            return found
    if title and len(title) > 12:
        found = db.execute(
            select(Source).where(Source.title.ilike(title[:80] + "%"), Source.deleted_at.is_(None))
        ).scalars().first()
        if found:
            return found
    return None


def create_stub_source(db: Session, candidate: dict) -> Source:
    external = {}
    if candidate.get("doi"):
        external["doi"] = candidate["doi"]
    if candidate.get("arxiv_id"):
        external["arxiv_id"] = candidate["arxiv_id"]
    normalized = NormalizedSource(
        source_type=SourceType.PAPER,
        title=candidate.get("title") or candidate.get("raw_text", "")[:200],
        canonical_url=candidate.get("url"),
        content_text=None,
        external_ids=external,
        raw_metadata={"stub": True, "raw_text": candidate.get("raw_text")},
        ingestion_method="REFERENCE_STUB",
    )
    source = Source(
        source_type=SourceType.PAPER,
        title=normalized.title,
        canonical_url=normalized.canonical_url,
        content_text=None,
        fingerprint=fingerprint(normalized),
        content_hash=None,
        ingestion_method="REFERENCE_STUB",
        raw_metadata=normalized.raw_metadata,
        publisher=None,
    )
    db.add(source)
    db.flush()
    return source


def resolve_references(db: Session, source_id: UUID, *, max_depth: int = 1) -> list[dict]:
    if max_depth > 1:
        raise ValueError("MVP does not recursively fetch depth-2 references")
    source = db.get(Source, source_id)
    if source is None:
        return []
    run = db.execute(select(ParserRun).where(ParserRun.source_id == source_id)).scalars().first()
    refs = []
    if run and run.output_metadata:
        refs = list(run.output_metadata.get("references") or [])
    if not refs and source.content_text:
        refs = extract_reference_candidates(source.content_text)
        db.add(
            ParserRun(
                source_id=source.id,
                parser_name="reference-extractor",
                parser_version="v1",
                output_metadata={"references": refs},
            )
        )
        db.flush()
    results = []
    for cand in refs:
        existing = _match_existing(db, cand.get("doi"), cand.get("arxiv_id"), cand.get("url"), cand.get("title"))
        created_stub = False
        if existing is None:
            existing = create_stub_source(db, cand)
            created_stub = True
        persist_source_edge(
            db,
            source.id,
            existing.id,
            SourceEdgeRelationship.CITES,
            confidence=float(cand.get("confidence") or 0.5),
            detected_by=DetectedBy.PARSER,
            evidence=cand.get("raw_text"),
        )
        results.append(
            {
                "candidate": cand,
                "resolved_source_id": str(existing.id),
                "stub": created_stub or existing.ingestion_method == "REFERENCE_STUB",
                "relationship": "CITES",
            }
        )
    return results


def independence_report(db: Session, source_ids: list[UUID]) -> dict:
    if not source_ids:
        return {"independent_sources": 0, "secondary_reports": 0}
    edges = db.execute(
        select(SourceEdge).where(
            SourceEdge.source_id.in_(source_ids),
            SourceEdge.relationship.in_(
                [SourceEdgeRelationship.REPOSTS, SourceEdgeRelationship.DERIVED_FROM, SourceEdgeRelationship.REPORTS_ON]
            ),
        )
    ).scalars().all()
    secondary = {e.source_id for e in edges}
    independent = [sid for sid in source_ids if sid not in secondary]
    if not independent:
        independent = source_ids[:1]
        secondary = set(source_ids[1:])
    return {
        "independent_sources": len(set(independent)),
        "secondary_reports": len(secondary),
        "independent_source_ids": [str(x) for x in independent],
        "secondary_source_ids": [str(x) for x in secondary],
    }


def link_near_duplicates(db: Session, source: Source) -> list[Source]:
    if not source.content_hash:
        return []
    others = (
        db.execute(
            select(Source).where(
                Source.content_hash == source.content_hash,
                Source.id != source.id,
                Source.deleted_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    for other in others:
        persist_source_edge(
            db,
            source.id,
            other.id,
            SourceEdgeRelationship.REPOSTS,
            confidence=0.9,
            detected_by=DetectedBy.METADATA,
            evidence="identical content_hash",
        )
    return list(others)
