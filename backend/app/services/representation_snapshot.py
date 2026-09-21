from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.event import Event, EventSource
from app.models.source import Source, SourceEdge
from app.services.analysis_runs import canonical_extra_sources
from app.services.source_graph import FrozenAnalysisRelationalContext, freeze_analysis_relational_context


REPRESENTATION_SNAPSHOT_VERSION = "world-representation-v0.1"
DECISION_REPRESENTATION_VERSION = "decision-representation-v0.1"


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _collect_attention_packets(sources: list[Source]) -> dict:
    packets: dict = {}
    for source in sources:
        candidate = (source.raw_metadata or {}).get("collective_attention_evidence_packets")
        if isinstance(candidate, dict):
            # Preserve the same precedence semantics currently used by pipeline:
            # later canonical extras overwrite duplicate packet keys.
            packets.update(candidate)
    return packets


def _edge_fact(edge: SourceEdge) -> dict:
    return {
        "source_id": str(edge.source_id),
        "relationship": str(edge.relationship),
        "target_id": str(edge.target_id),
        "confidence": float(edge.confidence or 0.0),
        "detected_by": str(edge.detected_by or ""),
        "evidence": edge.evidence or None,
    }


def _event_fact(event: Event, links: list[EventSource]) -> dict:
    members = sorted(
        (
            {
                "source_id": str(link.source_id),
                "relationship": str(link.relationship),
                "confidence": None if link.confidence is None else float(link.confidence),
            }
            for link in links
        ),
        key=lambda row: (row["source_id"], row["relationship"]),
    )
    return {
        "event_id": str(event.id),
        "title": event.title,
        "event_type": event.event_type,
        "actors": list(event.actors or []),
        "action": event.action,
        "object": event.object,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "time_context": event.time_context,
        "location": event.location,
        "summary": event.summary,
        "current_state": event.current_state,
        "attributes": dict(event.attributes or {}),
        "status": event.status,
        "confidence": float(event.confidence or 0.0),
        "members": members,
    }

@dataclass(frozen=True)
class FrozenRepresentationSnapshot:
    schema_version: str
    decision_version: str
    primary_source_id: str
    source_ids: tuple[str, ...]
    graph_digest: str
    decision_representation_digest: str
    relational_context: FrozenAnalysisRelationalContext
    event_hypotheses: tuple[dict, ...]
    graph_edges: tuple[dict, ...]
    collective_attention_evidence_packets: dict

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "decision_version": self.decision_version,
            "primary_source_id": self.primary_source_id,
            "source_ids": list(self.source_ids),
            "graph_digest": self.graph_digest,
            "decision_representation_digest": self.decision_representation_digest,
            "decision_scope": "legacy-source-scope-v0.1",
            "relational_context": self.relational_context.as_dict(),
            "event_hypotheses": list(self.event_hypotheses),
            "graph_edges": list(self.graph_edges),
            "collective_attention_evidence_packets": self.collective_attention_evidence_packets,
        }


def freeze_representation_snapshot(
    db: Session,
    source: Source,
    extras: list[Source] | None = None,
) -> FrozenRepresentationSnapshot:
    """Freeze the world-representation facts visible to one AnalysisRun.

    v0.1 intentionally keeps current Core mathematics unchanged. Candidate
    events and presentation relations affect graph_digest only. The decision
    digest contains exactly the relational facts consumed by current cognition
    plus collective-attention evidence consumed by no-Delta D/S/P.
    """
    ordered_sources = [source, *canonical_extra_sources(extras)]
    source_ids = [item.id for item in ordered_sources]
    relational = freeze_analysis_relational_context(db, source_ids)

    # Full graph view: any SourceEdge touching an explicit analysis Source.
    edges = (
        db.execute(
            select(SourceEdge).where(
                or_(
                    SourceEdge.source_id.in_(source_ids),
                    SourceEdge.target_id.in_(source_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    edge_facts = tuple(
        sorted(
            (_edge_fact(edge) for edge in edges),
            key=lambda row: (
                row["source_id"],
                row["relationship"],
                row["target_id"],
                row["confidence"],
            ),
        )
    )

    direct_event_links = (
        db.execute(select(EventSource).where(EventSource.source_id.in_(source_ids)))
        .scalars()
        .all()
    )
    event_ids = sorted({link.event_id for link in direct_event_links}, key=str)
    event_facts: list[dict] = []
    if event_ids:
        events = db.execute(select(Event).where(Event.id.in_(event_ids))).scalars().all()
        all_links = (
            db.execute(select(EventSource).where(EventSource.event_id.in_(event_ids)))
            .scalars()
            .all()
        )
        links_by_event: dict[UUID, list[EventSource]] = {}
        for link in all_links:
            links_by_event.setdefault(link.event_id, []).append(link)
        event_facts = [
            _event_fact(event, links_by_event.get(event.id, []))
            for event in sorted(events, key=lambda row: str(row.id))
        ]

    p_packets = _collect_attention_packets(ordered_sources)

    graph_payload = {
        "schema_version": REPRESENTATION_SNAPSHOT_VERSION,
        "primary_source_id": str(source.id),
        "source_ids": [str(item.id) for item in ordered_sources],
        "event_hypotheses": event_facts,
        "graph_edges": list(edge_facts),
        "collective_attention_evidence_packets": p_packets,
    }
    graph_digest = _canonical_digest(graph_payload)

    # Transitional decision scope: preserve current Source-level Core semantics.
    # Candidate Events / Related graph facts are deliberately excluded until
    # later representation phases authorize them as decision inputs.
    decision_payload = {
        "decision_version": DECISION_REPRESENTATION_VERSION,
        "source_ids": [str(item.id) for item in ordered_sources],
        "relational_facts": [list(fact) for fact in relational.facts],
        "independence": relational.report(),
        "is_duplicate": relational.is_duplicate,
        "collective_attention_evidence_packets": p_packets,
    }
    decision_digest = _canonical_digest(decision_payload)

    return FrozenRepresentationSnapshot(
        schema_version=REPRESENTATION_SNAPSHOT_VERSION,
        decision_version=DECISION_REPRESENTATION_VERSION,
        primary_source_id=str(source.id),
        source_ids=tuple(str(item.id) for item in ordered_sources),
        graph_digest=graph_digest,
        decision_representation_digest=decision_digest,
        relational_context=relational,
        event_hypotheses=tuple(event_facts),
        graph_edges=edge_facts,
        collective_attention_evidence_packets=p_packets,
    )
