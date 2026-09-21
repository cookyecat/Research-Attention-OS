from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cognitive.client import chat_json, chat_json_schema
from app.cognitive.research_aligned_contract import canonical_semantic_units
from app.config import settings
from app.enums import EventStatus
from app.models.event import Event, EventMembershipAssertion, EventRevision, EventSource
from app.models.source import Source
from app.services.event_membership import (
    AUTHORIZED_MEMBERSHIP_STATUSES,
    active_authorized_memberships,
    safe_legacy_single_member_event,
)
from app.services.extraction import ExtractionResult
from app.services.event_observation import EventObservationV01, materialize_event_observation
from app.services.event_state import snapshot_event_state

EVENT_PROCESSOR_CONTRACT = "event-processor-v1"
EVENT_CANDIDATE_CONTRACT = "coarse-event-candidate-v1"
EVENT_RESOLVER_CONTRACT = "llm-coarse-event-resolver-v1"
EVENT_MEMBERSHIP_POLICY = "event-processor-v1"
EVENT_REVISION_CONTRACT = "event-revision-v2"


class EventCandidateV1(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    event_type: str | None = Field(default=None, max_length=120)
    actors: list[str] = Field(default_factory=list)
    action: str = Field(min_length=1, max_length=500)
    object: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None
    time_context: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    description: str = Field(min_length=1, max_length=4000)
    current_state: str | None = Field(default=None, max_length=500)
    attributes: dict = Field(default_factory=dict)
    support_unit_ids: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("occurred_at", mode="before")
    @classmethod
    def parse_coarse_datetime(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                return text + "T00:00:00Z"
        return value

    @model_validator(mode="after")
    def normalize(self):
        self.actors = list(dict.fromkeys(x.strip() for x in self.actors if str(x).strip()))
        self.support_unit_ids = list(dict.fromkeys(x.strip() for x in self.support_unit_ids if str(x).strip()))
        return self


class EventResolutionV1(BaseModel):
    decision: Literal["SAME_EVENT", "DIFFERENT_EVENT", "UNCERTAIN"]
    matched_event_id: str | None = None
    rationale: str
    missing_evidence: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def shape(self):
        if self.decision == "SAME_EVENT" and not self.matched_event_id:
            raise ValueError("SAME_EVENT requires matched_event_id")
        if self.decision == "DIFFERENT_EVENT" and self.matched_event_id:
            raise ValueError("DIFFERENT_EVENT must not set matched_event_id")
        return self


@dataclass(frozen=True)
class EventProcessingResult:
    event: Event
    candidate: EventCandidateV1
    resolution: EventResolutionV1
    created: bool
    reused_existing_membership: bool
    candidate_rows: list[dict]
    execution: dict

    def as_dict(self) -> dict:
        return {
            "contract": EVENT_PROCESSOR_CONTRACT,
            "event_id": str(self.event.id),
            "candidate": self.candidate.model_dump(mode="json"),
            "resolution": self.resolution.model_dump(mode="json"),
            "created": self.created,
            "reused_existing_membership": self.reused_existing_membership,
            "candidate_rows": self.candidate_rows,
            "execution": self.execution,
        }


_CANDIDATE_SYSTEM = """You are the RAOS Event Processor V1.

Given one Source after Sensor + Semantic Auditor processing, extract exactly ONE primary coarse real-world EventCandidate.

RAOS V1 granularity:
- One normal Source describes one primary event/story/episode.
- Event is NOT one claim, sentence, benchmark number, quote, or atomic state transition.
- Claims, results, attributes, quotations, and intermediate progress belong INSIDE the event.
- Use an editorial/case granularity: would a competent editor normally keep these facts in one evolving story/case/research story?
- For a paper, the event may simply be: the authors/research team published paper P and proposed method/model M. Benchmarks and conclusions are attributes/claims inside that event.
- For an ongoing launch, preparation -> launch -> recovery may be one launch event/episode.
- Do not split the Source. V1 requires one primary EventCandidate.

Use only the supplied audited semantic units and Source metadata. Do not invent missing people, time, location, or facts.
support_unit_ids must reference supplied semantic unit ids when any units are supplied.
action should name the main coarse action/episode, not a generic word like reports.
description is a concise factual description of the event.
current_state is optional progress such as announced/launched/completed/paused.
Return schema JSON only.
"""

_RESOLVER_SYSTEM = """You are the RAOS coarse Event Resolver V1.

Decide whether ONE new EventCandidate belongs to one existing Event.

The Event unit is a coherent real-world story/episode that deserves one shared Attention lifecycle, NOT an atomic event mention.

Editorial test:
Would a competent editor normally update the same evolving news story/case/research story, or open a genuinely separate story/case?

Rules:
- Same actor, topic, company, product, or broad theme alone is NOT enough.
- Different Sources independently reporting the same occurrence/story are SAME_EVENT.
- More claims, benchmark details, quotes, corroboration, or natural progress inside the same story do NOT create a new Event.
- Preparation -> execution -> immediate result of the same operation may remain SAME_EVENT.
- A paper itself and later Sources discussing/reporting that same paper normally remain the paper's Event.
- A genuinely separate occurrence/story that deserves separate tracking is DIFFERENT_EVENT.
- If evidence is insufficient, use UNCERTAIN.
- UNCERTAIN must never be used as a hidden merge.
- Choose matched_event_id only from the supplied candidates.
Return schema JSON only.
"""


def execution_snapshot() -> dict:
    return {
        "contract": EVENT_PROCESSOR_CONTRACT,
        "candidate_contract": EVENT_CANDIDATE_CONTRACT,
        "resolver_contract": EVENT_RESOLVER_CONTRACT,
        "model": settings.llm_model if settings.llm_api_key else None,
        "canonical_strategy": "LLM_IF_AVAILABLE_ELSE_CONSERVATIVE_NEW",
        "granularity": "COARSE_EDITORIAL_EPISODE",
        "source_cardinality": "ONE_PRIMARY_EVENT_V1",
    }


def _stable_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _deterministic_candidate(source: Source, extraction: ExtractionResult) -> EventCandidateV1:
    title = extraction.event_title or source.title or "Untitled event"
    description = extraction.event_summary or source.title or (source.content_text or "")[:1200] or "Observed event"
    is_paper = str(source.source_type).upper() == "PAPER"
    return EventCandidateV1(
        title=title,
        event_type="PAPER_PUBLICATION" if is_paper else "REPORTED_EVENT",
        actors=[],
        action="PUBLISH" if is_paper else "UNSPECIFIED",
        object=source.title,
        occurred_at=source.published_at,
        time_context=(source.published_at.isoformat() if source.published_at else None),
        description=description[:4000],
        attributes={"fallback": "deterministic-no-llm"},
        missing_fields=["actors", "location"],
    )


def extract_event_candidate(source: Source, extraction: ExtractionResult, *, chat_fn=chat_json) -> tuple[EventCandidateV1, dict]:
    units = canonical_semantic_units(extraction)
    if not settings.llm_api_key and chat_fn is chat_json:
        return _deterministic_candidate(source, extraction), {
            "mode": "DETERMINISTIC_CONSERVATIVE", "model": None, "validation_events": []
        }

    payload = {
        "contract": EVENT_CANDIDATE_CONTRACT,
        "source": {
            "id": str(source.id), "source_type": str(source.source_type), "title": source.title,
            "publisher": source.publisher,
            "published_at": source.published_at.isoformat() if source.published_at else None,
        },
        "sensor_hints": {"event_title": extraction.event_title, "event_summary": extraction.event_summary},
        "audited_semantic_units": units,
    }
    obj, meta, validation_events = chat_json_schema(
        [
            {"role": "system", "content": _CANDIDATE_SYSTEM},
            {"role": "user", "content": "Extract the one primary EventCandidate.\n\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)},
        ],
        EventCandidateV1, chat_fn=chat_fn, timeout=45.0, thinking="disabled", reasoning_effort=None,
    )
    candidate = EventCandidateV1.model_validate(obj)
    allowed_ids = {str(row.get("unit_id")) for row in units if row.get("unit_id")}
    invalid = [unit_id for unit_id in candidate.support_unit_ids if unit_id not in allowed_ids]
    if invalid:
        raise ValueError(f"EventCandidate referenced unknown semantic unit ids: {invalid}")
    support_ids_filled = False
    if allowed_ids and not candidate.support_unit_ids:
        # The EventCandidate is a coarse assembly over the already-audited Source.
        # Missing explicit ids is not evidence fabrication: conservatively bind the
        # candidate to all admitted semantic units rather than failing a canonical
        # run because the model omitted bookkeeping fields.
        candidate.support_unit_ids = sorted(allowed_ids)
        support_ids_filled = True
    return candidate, {
        "mode": "LLM",
        "model": meta.get("model"),
        "meta": meta,
        "validation_events": validation_events,
        "support_ids_filled_from_audited_units": support_ids_filled,
    }


def _norm(value: str | None) -> str:
    return re.sub(r"[\s\W_]+", "", unicodedata.normalize("NFKC", value or "").lower(), flags=re.UNICODE)


def _bigrams(value: str | None) -> set[str]:
    text = _norm(value)
    if not text:
        return set()
    if len(text) == 1:
        return {text}
    return {text[i:i+2] for i in range(len(text)-1)}


def _similarity(a: str | None, b: str | None) -> float:
    aa, bb = _bigrams(a), _bigrams(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(1, len(aa | bb))


def _active_committed_event_ids(db: Session) -> set[UUID]:
    rows = (
        db.execute(
            select(EventMembershipAssertion)
            .where(EventMembershipAssertion.authority_status.in_(AUTHORIZED_MEMBERSHIP_STATUSES))
            .order_by(EventMembershipAssertion.created_at.asc(), EventMembershipAssertion.id.asc())
        ).scalars().all()
    )
    latest: dict[tuple[UUID, UUID], EventMembershipAssertion] = {}
    for row in rows:
        latest[(row.event_id, row.source_id)] = row
    return {
        row.event_id for row in latest.values()
        if str(row.action).upper() == "ASSERT" and str(row.membership).upper() == "REPORTS_EVENT"
    }


def _event_text(event: Event) -> str:
    return " ".join(
        x for x in (
            event.title, " ".join(str(x) for x in (event.actors or [])), event.action,
            event.object, event.summary, event.current_state,
        ) if x
    )


def _candidate_text(candidate: EventCandidateV1) -> str:
    return " ".join(
        x for x in (
            candidate.title, " ".join(candidate.actors), candidate.action, candidate.object,
            candidate.description, candidate.current_state,
        ) if x
    )


def retrieve_event_candidates(db: Session, candidate: EventCandidateV1, *, exclude_event_ids: set[UUID] | None = None, limit: int = 8) -> list[dict]:
    event_ids = _active_committed_event_ids(db)
    if exclude_event_ids:
        event_ids -= set(exclude_event_ids)
    if not event_ids:
        return []
    events = db.execute(
        select(Event).where(Event.id.in_(event_ids), Event.status != EventStatus.MERGED)
    ).scalars().all()
    ctext = _candidate_text(candidate)
    cactors = {_norm(x) for x in candidate.actors if _norm(x)}
    rows: list[dict] = []
    for event in events:
        title_score = _similarity(candidate.title, event.title)
        content_score = _similarity(ctext, _event_text(event))
        object_score = _similarity(candidate.object, event.object)
        actors = {_norm(x) for x in (event.actors or []) if _norm(x)}
        actor_score = len(cactors & actors) / max(1, len(cactors | actors)) if cactors and actors else 0.0
        time_score = 0.0
        if candidate.occurred_at and event.occurred_at:
            left, right = candidate.occurred_at, event.occurred_at
            if left.tzinfo is None:
                left = left.replace(tzinfo=timezone.utc)
            if right.tzinfo is None:
                right = right.replace(tzinfo=timezone.utc)
            hours = abs((left-right).total_seconds()) / 3600.0
            time_score = max(0.0, 1.0 - hours / (24.0*30.0))
        score = 0.35*title_score + 0.25*content_score + 0.20*object_score + 0.15*actor_score + 0.05*time_score
        if score <= 0.0:
            continue
        rows.append({
            "event_id": str(event.id), "title": event.title, "event_type": event.event_type,
            "actors": list(event.actors or []), "action": event.action, "object": event.object,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "time_context": event.time_context, "location": event.location, "summary": event.summary,
            "current_state": event.current_state, "retrieval_score": round(score, 4),
        })
    rows.sort(key=lambda row: (-row["retrieval_score"], row["event_id"]))
    return rows[:max(1, min(int(limit), 30))]


def resolve_event_candidate(candidate: EventCandidateV1, candidate_rows: list[dict], *, chat_fn=chat_json) -> tuple[EventResolutionV1, dict]:
    if not candidate_rows:
        return EventResolutionV1(
            decision="DIFFERENT_EVENT", rationale="No plausible existing Event candidate was retrieved."
        ), {"mode": "NO_CANDIDATES", "model": None, "validation_events": []}
    if not settings.llm_api_key and chat_fn is chat_json:
        return EventResolutionV1(
            decision="UNCERTAIN",
            rationale="LLM resolver unavailable; fail closed against cross-Source merge.",
            missing_evidence=["coarse event identity judgment"],
        ), {"mode": "CONSERVATIVE_NO_LLM", "model": None, "validation_events": []}

    payload = {
        "contract": EVENT_RESOLVER_CONTRACT,
        "new_event_candidate": candidate.model_dump(mode="json"),
        "existing_event_candidates": candidate_rows,
    }
    obj, meta, validation_events = chat_json_schema(
        [
            {"role": "system", "content": _RESOLVER_SYSTEM},
            {"role": "user", "content": "Resolve the new EventCandidate against the existing Events.\n\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True)},
        ],
        EventResolutionV1, chat_fn=chat_fn, timeout=45.0, thinking="disabled", reasoning_effort=None,
    )
    resolution = EventResolutionV1.model_validate(obj)
    allowed = {row["event_id"] for row in candidate_rows}
    if resolution.matched_event_id and resolution.matched_event_id not in allowed:
        raise ValueError("Event resolver selected an Event outside the retrieved candidate set")
    return resolution, {"mode": "LLM", "model": meta.get("model"), "meta": meta, "validation_events": validation_events}


def _latest_revision(db: Session, event_id: UUID) -> EventRevision | None:
    """Return the unique EventRevision chain head.

    Event Sourcing order must come from the parent chain, not timestamp
    resolution or UUID ordering. Multiple heads indicate a fork and fail closed.
    """
    rows = db.execute(
        select(EventRevision).where(EventRevision.event_id == event_id)
    ).scalars().all()
    if not rows:
        return None

    referenced_parent_ids = {
        row.parent_revision_id for row in rows if row.parent_revision_id is not None
    }
    heads = [row for row in rows if row.id not in referenced_parent_ids]
    if len(heads) != 1:
        raise RuntimeError(
            f"Event {event_id} revision history has {len(heads)} heads; refusing append"
        )
    return heads[0]


def _observation_revision(
    db: Session,
    *,
    event_id: UUID,
    observation_key: str,
) -> EventRevision | None:
    return db.execute(
        select(EventRevision).where(
            EventRevision.event_id == event_id,
            EventRevision.observation_key == observation_key,
        )
    ).scalar_one_or_none()


def _append_revision(
    db: Session,
    event: Event,
    *,
    source_id: UUID,
    candidate: EventCandidateV1,
    resolution: EventResolutionV1,
    kind: str,
    observation: EventObservationV01 | None = None,
) -> EventRevision:
    source = db.get(Source, source_id)
    if source is None:
        raise RuntimeError("EventRevision source is missing")
    observation = observation or materialize_event_observation(
        db,
        event=event,
        source=source,
    )

    existing_observation = _observation_revision(
        db,
        event_id=event.id,
        observation_key=observation.observation_key,
    )
    if existing_observation is not None:
        return existing_observation

    parent = _latest_revision(db, event.id)
    payload = {
        "contract": EVENT_REVISION_CONTRACT,
        "kind": kind,
        "source_id": str(source_id),
        "observation": observation.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "resolution": resolution.model_dump(mode="json"),
        "materialized_projection": {
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
        },
        # V0.1 remains the production snapshot until Phase17.0/17.1 gates
        # complete. EventState V0.2 is introduced as a separate target contract.
        "event_state": snapshot_event_state(db, event).model_dump(mode="json"),
    }
    digest = _stable_digest(payload)
    existing = db.execute(
        select(EventRevision).where(
            EventRevision.event_id == event.id,
            EventRevision.revision_digest == digest,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = EventRevision(
        workspace_id="local-default",
        event_id=event.id,
        parent_revision_id=parent.id if parent else None,
        observation_key=observation.observation_key,
        revision_payload=payload,
        revision_digest=digest,
        audit_run_id=None,
        authority_epoch=1,
    )
    db.add(row)
    db.flush()
    return row


def _attach_source(db: Session, *, event: Event, source: Source, cross_source_commitment: bool, resolution: EventResolutionV1) -> EventMembershipAssertion:
    active = active_authorized_memberships(db, source.id)
    for row in active:
        if row.event_id == event.id:
            if db.get(EventSource, (event.id, source.id)) is None:
                db.add(EventSource(event_id=event.id, source_id=source.id, relationship="REPORTS", confidence=0.8))
                db.flush()
            return row
    if active:
        raise RuntimeError("Source already has a different decision-committed Event; refusing implicit remap")
    if db.get(EventSource, (event.id, source.id)) is None:
        db.add(EventSource(event_id=event.id, source_id=source.id, relationship="REPORTS", confidence=0.8))
    assertion = EventMembershipAssertion(
        workspace_id="local-default", event_id=event.id, source_id=source.id, frame_ids=[],
        action="ASSERT", membership="REPORTS_EVENT",
        contextual_role_fields={
            "origin": "EVENT_PROCESSOR_V1", "cross_source_commitment": bool(cross_source_commitment),
            "resolution": resolution.decision, "resolver_contract": EVENT_RESOLVER_CONTRACT,
        },
        audit_run_id=None, authority_policy_version=EVENT_MEMBERSHIP_POLICY, authority_epoch=1,
        authority_status=("AUTHORIZED" if cross_source_commitment else "AUTHORIZED_SOURCE_LOCAL"),
        supersedes_assertion_id=None,
    )
    db.add(assertion)
    db.flush()
    return assertion


def _create_event(db: Session, source: Source, candidate: EventCandidateV1, resolution: EventResolutionV1) -> Event:
    event = Event(
        title=candidate.title, event_type=candidate.event_type, actors=list(candidate.actors),
        action=candidate.action, object=candidate.object, occurred_at=candidate.occurred_at,
        time_context=candidate.time_context, location=candidate.location, summary=candidate.description,
        current_state=candidate.current_state,
        attributes={
            **dict(candidate.attributes), "event_processor_contract": EVENT_PROCESSOR_CONTRACT,
            "creation_resolution": resolution.decision,
        },
        confidence=0.6, status=EventStatus.CANDIDATE,
    )
    db.add(event)
    db.flush()
    _attach_source(db, event=event, source=source, cross_source_commitment=False, resolution=resolution)
    _append_revision(db, event, source_id=source.id, candidate=candidate, resolution=resolution, kind="CREATE")
    return event


def _update_event_projection(event: Event, candidate: EventCandidateV1) -> None:
    event.actors = list(dict.fromkeys([*(event.actors or []), *candidate.actors]))
    if not event.action or event.action == "UNSPECIFIED":
        event.action = candidate.action
    if not event.object:
        event.object = candidate.object
    if event.occurred_at is None:
        event.occurred_at = candidate.occurred_at
    if not event.time_context:
        event.time_context = candidate.time_context
    if not event.location:
        event.location = candidate.location
    if candidate.current_state:
        event.current_state = candidate.current_state

    attrs = {**dict(event.attributes or {}), **dict(candidate.attributes or {})}
    descriptions = [
        str(value).strip()
        for value in list(attrs.get("source_descriptions") or [])
        if str(value).strip()
    ]
    for value in (event.summary, candidate.description):
        text = str(value or "").strip()
        if text and text not in descriptions:
            descriptions.append(text)
    if descriptions:
        attrs["source_descriptions"] = descriptions[-20:]
        # V1 avoids lossy overwrite. Keep the richest concise description as the
        # materialized summary while EventRevision preserves the full sequence.
        event.summary = max(descriptions, key=len)
    event.attributes = attrs


def process_event(db: Session, source: Source, extraction: ExtractionResult, *, chat_fn=chat_json) -> EventProcessingResult:
    candidate, candidate_exec = extract_event_candidate(source, extraction, chat_fn=chat_fn)
    existing_memberships = active_authorized_memberships(db, source.id)
    if len(existing_memberships) > 1:
        raise RuntimeError("Source has ambiguous decision-committed Event memberships")

    if len(existing_memberships) == 1:
        event = db.get(Event, existing_memberships[0].event_id)
        if event is None:
            raise RuntimeError("Existing Event membership references missing Event")
        resolution = EventResolutionV1(
            decision="SAME_EVENT", matched_event_id=str(event.id),
            rationale="Reprocessing an existing Source reuses its decision-committed Event identity.",
        )
        observation = materialize_event_observation(db, event=event, source=source)
        existing_observation = _observation_revision(
            db,
            event_id=event.id,
            observation_key=observation.observation_key,
        )
        if existing_observation is None:
            _update_event_projection(event, candidate)
            _append_revision(
                db,
                event,
                source_id=source.id,
                candidate=candidate,
                resolution=resolution,
                kind="SOURCE_REPROCESS_UPDATE",
                observation=observation,
            )
            db.flush()
        return EventProcessingResult(
            event=event, candidate=candidate, resolution=resolution, created=False,
            reused_existing_membership=True, candidate_rows=[],
            execution={
                "candidate": candidate_exec,
                "resolver": {"mode": "REUSE_EXISTING_MEMBERSHIP"},
                "observation": {
                    "observation_key": observation.observation_key,
                    "already_applied": existing_observation is not None,
                },
            },
        )

    legacy = safe_legacy_single_member_event(db, source.id)
    if legacy is not None:
        resolution = EventResolutionV1(
            decision="SAME_EVENT",
            matched_event_id=str(legacy.id),
            rationale="Safe single-member legacy Event adopted by Event Processor V1.",
        )
        _attach_source(
            db,
            event=legacy,
            source=source,
            cross_source_commitment=False,
            resolution=resolution,
        )
        _update_event_projection(legacy, candidate)
        _append_revision(
            db,
            legacy,
            source_id=source.id,
            candidate=candidate,
            resolution=resolution,
            kind="LEGACY_SINGLE_MEMBER_ADOPTION",
        )
        db.flush()
        return EventProcessingResult(
            event=legacy,
            candidate=candidate,
            resolution=resolution,
            created=False,
            reused_existing_membership=True,
            candidate_rows=[],
            execution={"candidate": candidate_exec, "resolver": {"mode": "ADOPT_SAFE_LEGACY_SINGLE_MEMBER"}},
        )

    candidate_rows = retrieve_event_candidates(db, candidate)
    resolution, resolver_exec = resolve_event_candidate(candidate, candidate_rows, chat_fn=chat_fn)
    if resolution.decision == "SAME_EVENT":
        event = db.get(Event, UUID(str(resolution.matched_event_id)))
        if event is None:
            raise RuntimeError("Resolver-selected Event no longer exists")
        _attach_source(db, event=event, source=source, cross_source_commitment=True, resolution=resolution)
        _update_event_projection(event, candidate)
        _append_revision(db, event, source_id=source.id, candidate=candidate, resolution=resolution, kind="UPDATE")
        db.flush()
        created = False
    else:
        event = _create_event(db, source, candidate, resolution)
        db.flush()
        created = True

    return EventProcessingResult(
        event=event, candidate=candidate, resolution=resolution, created=created,
        reused_existing_membership=False, candidate_rows=candidate_rows,
        execution={"candidate": candidate_exec, "resolver": resolver_exec},
    )
