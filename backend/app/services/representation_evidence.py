from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
import re
import unicodedata
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.acquisition import InformationSnapshot
from app.models.event import Event, EventEvidenceFrame, EventSource
from app.models.source import Source, SourceEdge
from app.services.source_graph import source_edge_authority_eligible


REPRESENTATION_EVIDENCE_BUNDLE_VERSION = "representation-evidence-bundle-v0.3"


def stable_digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _when(source: Source) -> datetime:
    value = source.published_at or source.ingested_at
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _normalize(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").lower()
    return re.sub(r"\s+", " ", text).strip()


def _char_bigrams(value: str | None) -> set[str]:
    text = re.sub(r"[\W_]+", "", _normalize(value), flags=re.UNICODE)
    if not text:
        return set()
    if len(text) < 2:
        return {text}
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _text_similarity(a: str | None, b: str | None) -> dict:
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return {"sequence": 0.0, "bigram_jaccard": 0.0}
    ga, gb = _char_bigrams(na), _char_bigrams(nb)
    return {
        "sequence": round(float(difflib.SequenceMatcher(None, na, nb).ratio()), 4),
        "bigram_jaccard": round(len(ga & gb) / max(1, len(ga | gb)), 4),
    }


def _host(url: str | None) -> str | None:
    try:
        return (urlparse(url or "").hostname or "").lower() or None
    except Exception:
        return None


def _frame_text(frame: EventEvidenceFrame) -> str:
    payload = frame.frame_payload or {}
    parts = [
        payload.get("event_title"),
        payload.get("event_summary"),
        payload.get("rendered_event_text"),
    ]
    for row in payload.get("actions") or []:
        if isinstance(row, dict):
            parts.append(row.get("description"))
    for row in payload.get("actors") or []:
        if isinstance(row, dict):
            parts.extend([row.get("name"), row.get("role")])
    for row in payload.get("claim_evidence") or []:
        if isinstance(row, dict):
            parts.append(row.get("text"))
    return " ".join(str(x) for x in parts if x)


def _source_meta(db: Session, source: Source) -> dict:
    external_item_ids = sorted(
        {
            str(value)
            for value in db.execute(
                select(InformationSnapshot.external_item_id).where(
                    InformationSnapshot.raos_source_id == source.id
                )
            ).scalars().all()
        }
    )
    return {
        "source_id": str(source.id),
        "source_type": source.source_type,
        "title": source.title,
        "publisher": source.publisher,
        "canonical_url": source.canonical_url,
        "host": _host(source.canonical_url),
        "published_at": source.published_at.isoformat() if source.published_at else None,
        "ingested_at": source.ingested_at.isoformat() if source.ingested_at else None,
        "content_hash": source.content_hash,
        "ingestion_method": source.ingestion_method,
        "external_item_ids": external_item_ids,
        "content_excerpt": (source.content_text or "")[:2400],
    }


def _frame_projection(frame: EventEvidenceFrame) -> dict:
    payload = dict(frame.frame_payload or {})
    return {
        "frame_id": str(frame.id),
        "source_id": str(frame.source_id),
        "frame_contract_version": frame.frame_contract_version,
        "semantic_input_digest": frame.semantic_input_digest,
        "semantic_provenance": payload.get("semantic_provenance"),
        "event_key": payload.get("event_key"),
        "event_title": payload.get("event_title"),
        "event_summary": payload.get("event_summary"),
        "actors": payload.get("actors") or [],
        "actions": payload.get("actions") or [],
        "affected_systems_populations": payload.get("affected_systems_populations") or [],
        "uncertainties": payload.get("uncertainties") or [],
        "claim_evidence": payload.get("claim_evidence") or [],
        "observation_evidence": payload.get("observation_evidence") or [],
        "rendered_event_text": payload.get("rendered_event_text") or "",
    }


@dataclass(frozen=True)
class RepresentationEvidenceBundle:
    payload: dict
    digest: str

    @property
    def evidence_ids(self) -> set[str]:
        return {
            str(item["evidence_id"])
            for item in self.payload.get("evidence") or []
            if isinstance(item, dict) and item.get("evidence_id")
        }


def build_frame_pair_evidence_bundle(
    db: Session,
    frame_a_id: UUID,
    frame_b_id: UUID,
) -> RepresentationEvidenceBundle:
    frame_a = db.get(EventEvidenceFrame, frame_a_id)
    frame_b = db.get(EventEvidenceFrame, frame_b_id)
    if frame_a is None or frame_b is None:
        raise ValueError("EventEvidenceFrame not found")
    source_a = db.get(Source, frame_a.source_id)
    source_b = db.get(Source, frame_b.source_id)
    if source_a is None or source_b is None:
        raise ValueError("Source for EventEvidenceFrame not found")

    evidence: list[dict] = [
        {
            "evidence_id": "SOURCE_A",
            "kind": "SOURCE_METADATA",
            "data": _source_meta(db, source_a),
        },
        {
            "evidence_id": "SOURCE_B",
            "kind": "SOURCE_METADATA",
            "data": _source_meta(db, source_b),
        },
        {
            "evidence_id": "FRAME_A",
            "kind": "AUDITED_EVENT_FRAME"
            if (frame_a.frame_payload or {}).get("semantic_provenance", {}).get("authority")
            == "SEMANTIC_AUDITED"
            else "EVENT_FRAME",
            "data": _frame_projection(frame_a),
        },
        {
            "evidence_id": "FRAME_B",
            "kind": "AUDITED_EVENT_FRAME"
            if (frame_b.frame_payload or {}).get("semantic_provenance", {}).get("authority")
            == "SEMANTIC_AUDITED"
            else "EVENT_FRAME",
            "data": _frame_projection(frame_b),
        },
    ]

    edges = db.execute(
        select(SourceEdge)
        .where(
            or_(
                (SourceEdge.source_id == source_a.id) & (SourceEdge.target_id == source_b.id),
                (SourceEdge.source_id == source_b.id) & (SourceEdge.target_id == source_a.id),
            )
        )
        .order_by(SourceEdge.relationship, SourceEdge.source_id, SourceEdge.target_id, SourceEdge.id)
    ).scalars().all()
    for index, edge in enumerate(edges):
        direction = "A_TO_B" if edge.source_id == source_a.id else "B_TO_A"
        evidence.append(
            {
                "evidence_id": f"GRAPH_EDGE_{index}",
                "kind": "EXISTING_SOURCE_GRAPH_FACT",
                "data": {
                    "direction": direction,
                    "relationship": edge.relationship,
                    "confidence": edge.confidence,
                    "detected_by": edge.detected_by,
                    "evidence": edge.evidence,
                    "authority_eligible": source_edge_authority_eligible(db, edge),
                    "warning": "Existing graph fact is evidence, not ground truth for this shadow audit.",
                },
            }
        )

    memberships: list[dict] = []
    for label, source in (("A", source_a), ("B", source_b)):
        rows = db.execute(
            select(EventSource, Event)
            .join(Event, Event.id == EventSource.event_id)
            .where(EventSource.source_id == source.id)
            .order_by(Event.created_at.desc(), Event.id)
        ).all()
        for es, event in rows:
            memberships.append(
                {
                    "side": label,
                    "event_id": str(event.id),
                    "event_status": event.status,
                    "event_title": event.title,
                    "relationship": es.relationship,
                    "confidence": es.confidence,
                }
            )
    if memberships:
        evidence.append(
            {
                "evidence_id": "CURRENT_EVENT_PROJECTION",
                "kind": "CURRENT_RAOS_EVENT_PROJECTION",
                "data": {
                    "memberships": memberships,
                    "warning": "Current projection may be revised and must not decide the audit by itself.",
                },
            }
        )

    title_similarity = _text_similarity(source_a.title, source_b.title)
    frame_similarity = _text_similarity(_frame_text(frame_a)[:5000], _frame_text(frame_b)[:5000])
    content_similarity = _text_similarity(
        (source_a.content_text or "")[:6000],
        (source_b.content_text or "")[:6000],
    )
    evidence.append(
        {
            "evidence_id": "PAIR_SIMILARITY",
            "kind": "NON_AUTHORITATIVE_SIMILARITY",
            "data": {
                "title": title_similarity,
                "event_frame": frame_similarity,
                "source_text": content_similarity,
                "warning": "Similarity is retrieval/context evidence only and cannot authorize SAME_EVENT.",
            },
        }
    )

    delta_hours = abs((_when(source_a) - _when(source_b)).total_seconds()) / 3600.0
    evidence.append(
        {
            "evidence_id": "TEMPORAL_RELATION",
            "kind": "TEMPORAL_EVIDENCE",
            "data": {"distance_hours": round(delta_hours, 3)},
        }
    )

    if source_a.content_hash and source_a.content_hash == source_b.content_hash:
        evidence.append(
            {
                "evidence_id": "CONTENT_HASH_EQUAL",
                "kind": "EXACT_CONTENT_IDENTITY",
                "data": {"content_hash": source_a.content_hash},
            }
        )
    if (
        source_a.canonical_url
        and source_b.canonical_url
        and source_a.canonical_url == source_b.canonical_url
    ):
        evidence.append(
            {
                "evidence_id": "CANONICAL_URL_EQUAL",
                "kind": "EXACT_CANONICAL_URL_IDENTITY",
                "data": {"canonical_url": source_a.canonical_url},
            }
        )

    payload = {
        "bundle_version": REPRESENTATION_EVIDENCE_BUNDLE_VERSION,
        "subject": {"type": "EVENT_FRAME", "id": str(frame_a.id), "source_id": str(source_a.id)},
        "object": {"type": "EVENT_FRAME", "id": str(frame_b.id), "source_id": str(source_b.id)},
        "evidence": evidence,
    }
    return RepresentationEvidenceBundle(payload=payload, digest=stable_digest(payload))
