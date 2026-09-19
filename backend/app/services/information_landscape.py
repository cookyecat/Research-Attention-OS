from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import SourceEdgeRelationship
from app.models.event import Event, EventSource
from app.models.source import Source, SourceEdge
from app.services.source_graph import independence_report, source_edge_authority_eligible


_COVERAGE_EDGE_RELATIONSHIPS = {
    SourceEdgeRelationship.REPOSTS,
    SourceEdgeRelationship.DERIVED_FROM,
    SourceEdgeRelationship.REPORTS_ON,
}

_RELATED_EDGE_RELATIONSHIPS = {
    SourceEdgeRelationship.DISCUSSES,
    SourceEdgeRelationship.EXTENDS,
    SourceEdgeRelationship.CONTRADICTS,
}


def _source_card(source: Source, *, relationship: str | None = None, confidence: float | None = None) -> dict:
    return {
        "source_id": str(source.id),
        "title": source.title,
        "publisher": source.publisher,
        "canonical_url": source.canonical_url,
        "published_at": source.published_at.isoformat() if source.published_at else None,
        "ingested_at": source.ingested_at.isoformat() if source.ingested_at else None,
        "relationship": relationship,
        "confidence": confidence,
    }


def _reference_card(source: Source, edge: SourceEdge) -> dict:
    return {
        "source_id": str(source.id),
        "title": source.title,
        "publisher": source.publisher,
        "canonical_url": source.canonical_url,
        "source_type": source.source_type,
        "stub": source.ingestion_method == "REFERENCE_STUB",
        "relationship": str(edge.relationship),
        "confidence": float(edge.confidence or 0.0),
        "detected_by": str(edge.detected_by or ""),
        "evidence": edge.evidence,
    }


def _edge_relationship_between(edges: list[SourceEdge], current_id: UUID, other_id: UUID) -> tuple[str | None, float | None]:
    matches = [
        edge for edge in edges
        if {edge.source_id, edge.target_id} == {current_id, other_id}
        and edge.relationship in _COVERAGE_EDGE_RELATIONSHIPS
    ]
    if not matches:
        return None, None
    matches.sort(key=lambda edge: (-float(edge.confidence or 0.0), edge.relationship, str(edge.id)))
    edge = matches[0]
    return edge.relationship, float(edge.confidence)


def source_information_landscape(db: Session, source_id: UUID) -> dict:
    """Return auditable world-context around one Source.

    V1 exposes already-persisted Event/EventSource and SourceEdge facts only.
    It does not infer or persist new same-event links on read.
    """
    source = db.get(Source, source_id)
    if source is None or source.deleted_at is not None:
        raise ValueError("Source not found")

    event_links = db.execute(
        select(EventSource).where(EventSource.source_id == source_id)
    ).scalars().all()
    event_ids = [link.event_id for link in event_links]

    events = []
    candidate_event_source_ids: set[UUID] = {source_id}
    confirmed_event_source_ids: set[UUID] = {source_id}
    confirmed_event_ids: set[UUID] = set()
    if event_ids:
        event_rows = db.execute(
            select(Event).where(Event.id.in_(event_ids))
        ).scalars().all()
        links = db.execute(
            select(EventSource).where(EventSource.event_id.in_(event_ids))
        ).scalars().all()
        by_event: dict[UUID, list[EventSource]] = defaultdict(list)
        for link in links:
            by_event[link.event_id].append(link)
            candidate_event_source_ids.add(link.source_id)
        for event in sorted(event_rows, key=lambda row: (-float(row.confidence or 0.0), str(row.id))):
            visible = str(event.status or "").upper() == "CONFIRMED"
            if visible:
                confirmed_event_ids.add(event.id)
                for link in by_event.get(event.id, []):
                    confirmed_event_source_ids.add(link.source_id)
            events.append({
                "event_id": str(event.id),
                "title": event.title,
                "summary": event.summary,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                "status": event.status,
                "confidence": float(event.confidence or 0.0),
                "source_count": len(by_event.get(event.id, [])),
                "coverage_authorized": visible,
            })

    graph_ids = set(candidate_event_source_ids)
    graph_edges = db.execute(
        select(SourceEdge).where(
            or_(
                SourceEdge.source_id.in_(graph_ids),
                SourceEdge.target_id.in_(graph_ids),
            )
        )
    ).scalars().all() if graph_ids else []

    graph_edges = [edge for edge in graph_edges if source_edge_authority_eligible(db, edge)]
    edge_authorized_ids: set[UUID] = set()
    for edge in graph_edges:
        if edge.relationship not in _COVERAGE_EDGE_RELATIONSHIPS or float(edge.confidence or 0.0) < 0.85:
            continue
        if edge.source_id == source_id:
            edge_authorized_ids.add(edge.target_id)
        elif edge.target_id == source_id:
            edge_authorized_ids.add(edge.source_id)

    coverage_ids = (confirmed_event_source_ids | edge_authorized_ids) - {source_id}
    coverage_sources = []
    if coverage_ids:
        rows = db.execute(
            select(Source).where(Source.id.in_(coverage_ids), Source.deleted_at.is_(None))
        ).scalars().all()
        for row in rows:
            relationship, confidence = _edge_relationship_between(graph_edges, source_id, row.id)
            coverage_sources.append(
                _source_card(
                    row,
                    relationship=relationship or "REPORTS_SAME_EVENT",
                    confidence=confidence,
                )
            )
        coverage_sources.sort(
            key=lambda row: (
                row["published_at"] or row["ingested_at"] or "",
                row["source_id"],
            )
        )

    related_edges = db.execute(
        select(SourceEdge).where(
            or_(SourceEdge.source_id == source_id, SourceEdge.target_id == source_id),
            SourceEdge.relationship.in_(list(_RELATED_EDGE_RELATIONSHIPS)),
        )
    ).scalars().all()
    related = []
    seen_related: set[UUID] = set()
    for edge in sorted(related_edges, key=lambda row: (-float(row.confidence or 0.0), str(row.id))):
        other_id = edge.target_id if edge.source_id == source_id else edge.source_id
        if other_id in coverage_ids or other_id in seen_related:
            continue
        other = db.get(Source, other_id)
        if other is None or other.deleted_at is not None:
            continue
        seen_related.add(other_id)
        related.append(
            _source_card(other, relationship=edge.relationship, confidence=float(edge.confidence or 0.0))
        )

    reference_edges = db.execute(
        select(SourceEdge).where(
            SourceEdge.source_id == source_id,
            SourceEdge.relationship == SourceEdgeRelationship.CITES,
        )
    ).scalars().all()
    references = []
    for edge in sorted(reference_edges, key=lambda row: (-float(row.confidence or 0.0), str(row.id))):
        target = db.get(Source, edge.target_id)
        if target is None or target.deleted_at is not None:
            continue
        references.append(_reference_card(target, edge))

    cluster_ids = [source_id, *sorted(coverage_ids, key=str)]
    independence = independence_report(db, cluster_ids)
    authorized_events = [event for event in events if event.get("coverage_authorized")]

    return {
        "source_id": str(source_id),
        "event": authorized_events[0] if authorized_events else None,
        "events": events,
        "coverage": {
            "source_count": len(cluster_ids),
            "other_source_count": len(coverage_sources),
            "sources": coverage_sources,
            "independence": independence,
            "authority": "persisted-event-and-sourcegraph-facts",
        },
        "related": {
            "count": len(related),
            "sources": related,
            "authority": "persisted-sourcegraph-facts",
        },
        "references": {
            "count": len(references),
            "sources": references,
            "authority": "persisted-explicit-cites-facts",
            "semantics": "CITES proves only that this Source explicitly links the target; it does not imply SAME_EVENT, DERIVED_FROM, INDEPENDENT_REPORT, or ORIGINAL_SOURCE.",
        },
        "provenance": {
            "explicit_reference_count": len(references),
            "relationship_authority": "literal-link-only",
        },
        "p_input_status": "NOT_YET_AUTHORIZED",
    }
