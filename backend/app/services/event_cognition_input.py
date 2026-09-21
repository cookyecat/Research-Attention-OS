from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event, EventMembershipAssertion
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.event_membership import (
    AUTHORIZED_MEMBERSHIP_STATUSES,
    active_authorized_memberships,
)
from app.services.extraction import ExtractionResult, _evidence_maturity
from app.services.frame_conditioned_cognition import (
    FrameConditionedCognitionError,
    event_frame_to_extraction,
)
from app.services.source_graph import (
    FrozenAnalysisRelationalContext,
    freeze_analysis_relational_context,
)

EVENT_COGNITION_INPUT_CONTRACT = "event-cognition-input-v0.1"


class EventCognitionInputError(RuntimeError):
    pass


@dataclass(frozen=True)
class EventCognitionInput:
    event_id: UUID
    member_source_ids: tuple[UUID, ...]
    frame_ids: tuple[UUID, ...]
    frame_digests: tuple[str, ...]
    semantic_input_digests: tuple[str, ...]
    extraction: ExtractionResult
    relational_context: FrozenAnalysisRelationalContext
    event_state: dict
    input_digest: str
    retrieval_text: str

    def as_dict(self) -> dict:
        return {
            "contract": EVENT_COGNITION_INPUT_CONTRACT,
            "event_id": str(self.event_id),
            "member_source_ids": [str(value) for value in self.member_source_ids],
            "frame_ids": [str(value) for value in self.frame_ids],
            "frame_digests": list(self.frame_digests),
            "semantic_input_digests": list(self.semantic_input_digests),
            "relational_context": self.relational_context.as_dict(),
            "event_state": dict(self.event_state),
            "input_digest": self.input_digest,
            "semantic_unit_count": (
                len(self.extraction.claims)
                + len(self.extraction.observations)
                + len(self.extraction.inferences)
            ),
        }


def _stable_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _event_state(event: Event) -> dict:
    """Decision-bearing Event V1 state.

    Untyped Event.attributes are intentionally excluded from V0.1 cognition
    identity. Audited evidence changes are already represented by frame digests.
    """
    return {
        "title": event.title,
        "event_type": event.event_type,
        "actors": sorted(str(value) for value in (event.actors or [])),
        "action": event.action,
        "object": event.object,
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "time_context": event.time_context,
        "location": event.location,
        "summary": event.summary,
        "current_state": event.current_state,
        "status": str(event.status),
    }


def active_event_member_source_ids(db: Session, event_id: UUID) -> list[UUID]:
    """Return active decision-authorized member Sources, failing on ambiguity."""
    rows = (
        db.execute(
            select(EventMembershipAssertion)
            .where(
                EventMembershipAssertion.event_id == event_id,
                EventMembershipAssertion.authority_status.in_(
                    AUTHORIZED_MEMBERSHIP_STATUSES
                ),
            )
            .order_by(
                EventMembershipAssertion.created_at.asc(),
                EventMembershipAssertion.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    latest: dict[UUID, EventMembershipAssertion] = {}
    for row in rows:
        latest[row.source_id] = row

    members: list[UUID] = []
    for source_id, row in latest.items():
        if (
            str(row.action).upper() != "ASSERT"
            or str(row.membership).upper() != "REPORTS_EVENT"
        ):
            continue
        active = active_authorized_memberships(db, source_id)
        if len(active) != 1:
            raise EventCognitionInputError(
                f"Source {source_id} has {len(active)} active authorized Event memberships"
            )
        if active[0].event_id != event_id:
            continue
        members.append(source_id)

    return sorted(set(members), key=str)


def _unit_signature(kind: str, item) -> str:
    supports = list(getattr(item, "semantic_supports", None) or [])
    return _stable_digest(
        {
            "kind": kind,
            "text": str(getattr(item, "text", "") or ""),
            "supports": supports,
            "source_span_text": getattr(item, "source_span_text", None),
        }
    )


def _merge_frame_extractions(
    event: Event,
    parts: list[ExtractionResult],
    *,
    provenance: dict,
) -> ExtractionResult:
    merged = ExtractionResult()
    seen_units: dict[str, str] = {}

    def add_items(kind: str, items: list, target: list) -> None:
        for item in items:
            unit_id = str(getattr(item, "semantic_unit_id", "") or "").strip()
            if not unit_id:
                raise EventCognitionInputError(
                    f"Event cognition {kind} lacks semantic_unit_id"
                )
            signature = _unit_signature(kind, item)
            previous = seen_units.get(unit_id)
            if previous is not None:
                if previous != signature:
                    raise EventCognitionInputError(
                        f"Conflicting duplicate semantic_unit_id: {unit_id}"
                    )
                continue
            seen_units[unit_id] = signature
            target.append(deepcopy(item))

    for part in parts:
        add_items("CLAIM", list(part.claims), merged.claims)
        add_items("OBSERVATION", list(part.observations), merged.observations)
        add_items("INFERENCE", list(part.inferences), merged.inferences)

    key = lambda item: str(getattr(item, "semantic_unit_id", "") or "")
    merged.claims.sort(key=key)
    merged.observations.sort(key=key)
    merged.inferences.sort(key=key)

    def merge_text(field: str) -> list[str]:
        values: dict[str, str] = {}
        for part in parts:
            for raw in list(getattr(part, field, None) or []):
                text = str(raw or "").strip()
                if text:
                    values.setdefault(text.lower(), text)
        return [values[k] for k in sorted(values)]

    merged.current_facts = merge_text("current_facts")
    merged.future_plans = merge_text("future_plans")
    merged.technical_claims = merge_text("technical_claims")
    merged.promotional_framing = merge_text("promotional_framing")
    merged.marketing_heavy = any(bool(part.marketing_heavy) for part in parts)
    merged.event_title = event.title
    merged.event_summary = event.summary
    merged.evidence_maturity = _evidence_maturity(merged)
    merged.analysis_provenance = dict(provenance)
    return merged


def _retrieval_text(event_state: dict, extraction: ExtractionResult) -> str:
    parts = [
        event_state.get("title"),
        event_state.get("event_type"),
        " ".join(event_state.get("actors") or []),
        event_state.get("action"),
        event_state.get("object"),
        event_state.get("time_context"),
        event_state.get("location"),
        event_state.get("summary"),
        event_state.get("current_state"),
    ]
    parts.extend(item.text for item in extraction.claims)
    parts.extend(item.text for item in extraction.observations)
    parts.extend(item.text for item in extraction.inferences)
    return "\n".join(str(value).strip() for value in parts if str(value or "").strip())


def build_event_cognition_input(
    db: Session,
    event_id: UUID,
) -> EventCognitionInput:
    event = db.get(Event, event_id)
    if event is None:
        raise EventCognitionInputError(f"Event not found: {event_id}")

    source_ids = active_event_member_source_ids(db, event_id)
    if not source_ids:
        raise EventCognitionInputError(
            f"Event {event_id} has no active decision-authorized member Sources"
        )

    frames = []
    parts: list[ExtractionResult] = []
    for source_id in source_ids:
        source_frames = latest_event_evidence_frames_for_source(db, source_id)
        if not source_frames:
            raise EventCognitionInputError(
                f"Source {source_id} lacks EventEvidenceFrame evidence"
            )
        for frame in sorted(
            source_frames,
            key=lambda row: (
                str(row.semantic_input_digest),
                str(row.frame_digest),
                str(row.id),
            ),
        ):
            try:
                part = event_frame_to_extraction(frame)
            except FrameConditionedCognitionError as exc:
                raise EventCognitionInputError(
                    f"Source {source_id} has unusable audited Event evidence: {exc}"
                ) from exc
            frames.append(frame)
            parts.append(part)

    relational = freeze_analysis_relational_context(db, source_ids)
    state = _event_state(event)
    frame_identity_rows = sorted(
        (
            {
                "source_id": str(frame.source_id),
                "frame_id": str(frame.id),
                "frame_digest": str(frame.frame_digest),
                "semantic_input_digest": str(frame.semantic_input_digest),
            }
            for frame in frames
        ),
        key=lambda row: (
            row["source_id"],
            row["semantic_input_digest"],
            row["frame_digest"],
            row["frame_id"],
        ),
    )
    provenance = {
        "contract": EVENT_COGNITION_INPUT_CONTRACT,
        "event_id": str(event.id),
        "member_source_ids": [str(value) for value in source_ids],
        "frame_ids": [row["frame_id"] for row in frame_identity_rows],
        "frame_digests": [row["frame_digest"] for row in frame_identity_rows],
        "semantic_input_digests": [
            row["semantic_input_digest"] for row in frame_identity_rows
        ],
        "independent_source_ids": list(relational.independent_source_ids),
        "secondary_source_ids": list(relational.secondary_source_ids),
        "decision_scope": "EVENT",
    }
    extraction = _merge_frame_extractions(event, parts, provenance=provenance)
    input_digest = _stable_digest(
        {
            "contract": EVENT_COGNITION_INPUT_CONTRACT,
            "event_id": str(event.id),
            "event_state": state,
            "members": [str(value) for value in source_ids],
            "frames": frame_identity_rows,
            "relational_digest": relational.digest,
        }
    )
    return EventCognitionInput(
        event_id=event.id,
        member_source_ids=tuple(source_ids),
        frame_ids=tuple(UUID(row["frame_id"]) for row in frame_identity_rows),
        frame_digests=tuple(row["frame_digest"] for row in frame_identity_rows),
        semantic_input_digests=tuple(
            row["semantic_input_digest"] for row in frame_identity_rows
        ),
        extraction=extraction,
        relational_context=relational,
        event_state=state,
        input_digest=input_digest,
        retrieval_text=_retrieval_text(state, extraction),
    )
