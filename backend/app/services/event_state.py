from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import Disposition
from app.models.event import Event, EventMembershipAssertion
from app.services.event_membership import AUTHORIZED_MEMBERSHIP_STATUSES
from app.services.source_graph import freeze_analysis_relational_context


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------

# Historical experimental contract retained for existing EventRevision payloads.
EVENT_STATE_V01_CONTRACT = "event-state-v0.1"

# Phase17 target representation contract.
EVENT_STATE_CONTRACT = "event-state-v0.2"
FILTER_STATE_CONTRACT = "event-filter-state-v0.1"

RECURSIVE_FILTER_CONTRACT = "recursive-event-state-filter-v0.1"
HYSTERESIS_CONTRACT = "hysteretic-attention-controller-v0.1"


def _stable_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# V0.2 canonical target: Identity stays on Event; dynamic State stays small.
# ---------------------------------------------------------------------------


class WorldStateV02(BaseModel):
    """Compact current projection of one already-identified Event.

    Event identity fields (actors/action/object/time/location/type) intentionally
    do not live here. They remain on Event / EventCandidate.
    """

    synopsis: str = Field(min_length=1, max_length=8000)
    status: str | None = Field(default=None, max_length=256)
    effective_at: datetime | None = None
    active_semantic_unit_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def normalize_refs(self):
        refs = tuple(sorted({str(value).strip() for value in self.active_semantic_unit_refs if str(value).strip()}))
        object.__setattr__(self, "active_semantic_unit_refs", refs)
        return self


class EvidenceStateV02(BaseModel):
    """Current structural support for WorldState, never a truth probability."""

    member_source_count: int = Field(ge=0)
    independent_source_count: int = Field(ge=0)
    secondary_report_count: int = Field(ge=0)
    relational_digest: str
    active_support_digest: str


class EventStateV02(BaseModel):
    contract: str = EVENT_STATE_CONTRACT
    event_id: UUID
    world_state: WorldStateV02
    evidence_state: EvidenceStateV02
    state_digest: str

    @model_validator(mode="after")
    def validate_digest(self):
        expected = event_state_v02_digest(
            event_id=self.event_id,
            world_state=self.world_state,
            evidence_state=self.evidence_state,
        )
        if self.state_digest != expected:
            raise ValueError("event-state-v0.2 digest mismatch")
        return self


class FilterStateV01(BaseModel):
    """Algorithm-internal recursive state, separate from Event world ontology."""

    contract: str = FILTER_STATE_CONTRACT
    momentum: float | None = Field(default=None, ge=0.0)
    momentum_updated_at: datetime | None = None
    last_applied_observation_key: str | None = None
    algorithm_state_digest: str | None = None


def event_state_v02_digest(
    *,
    event_id: UUID,
    world_state: WorldStateV02,
    evidence_state: EvidenceStateV02,
) -> str:
    return _stable_digest(
        {
            "contract": EVENT_STATE_CONTRACT,
            "event_id": str(event_id),
            "world_state": world_state.model_dump(mode="json"),
            "evidence_state": evidence_state.model_dump(mode="json"),
        }
    )


def make_event_state_v02(
    *,
    event_id: UUID,
    world_state: WorldStateV02,
    evidence_state: EvidenceStateV02,
) -> EventStateV02:
    return EventStateV02(
        event_id=event_id,
        world_state=world_state,
        evidence_state=evidence_state,
        state_digest=event_state_v02_digest(
            event_id=event_id,
            world_state=world_state,
            evidence_state=evidence_state,
        ),
    )


def structural_evidence_state_v02(
    db: Session,
    event_id: UUID,
    *,
    active_semantic_unit_refs: tuple[str, ...] | list[str] = (),
    supporting_source_ids: tuple[UUID, ...] | list[UUID] | set[UUID] | None = None,
) -> EvidenceStateV02:
    source_ids = (
        active_event_source_ids(db, event_id)
        if supporting_source_ids is None
        else sorted(set(supporting_source_ids), key=str)
    )
    authorized = set(active_event_source_ids(db, event_id))
    unauthorized = set(source_ids) - authorized
    if unauthorized:
        raise ValueError(
            "EvidenceState contains non-authorized Event source ids: "
            + ", ".join(sorted(str(value) for value in unauthorized))
        )
    relational = freeze_analysis_relational_context(db, source_ids)
    active_support_digest = _stable_digest(
        {
            "event_id": str(event_id),
            "active_semantic_unit_refs": sorted(
                {str(value).strip() for value in active_semantic_unit_refs if str(value).strip()}
            ),
            "member_source_ids": [str(value) for value in source_ids],
            "relational_digest": relational.digest,
        }
    )
    return EvidenceStateV02(
        member_source_count=len(source_ids),
        independent_source_count=relational.independent_sources,
        secondary_report_count=relational.secondary_reports,
        relational_digest=relational.digest,
        active_support_digest=active_support_digest,
    )


# ---------------------------------------------------------------------------
# V0.1 historical compatibility. Do not extend this contract.
# ---------------------------------------------------------------------------


class WorldStateV01(BaseModel):
    title: str
    event_type: str | None = None
    actors: tuple[str, ...] = ()
    action: str | None = None
    object: str | None = None
    occurred_at: datetime | None = None
    time_context: str | None = None
    location: str | None = None
    summary: str | None = None
    current_state: str | None = None
    status: str


class EvidenceStateV01(BaseModel):
    member_source_count: int = Field(ge=0)
    independent_source_count: int = Field(ge=0)
    secondary_report_count: int = Field(ge=0)
    relational_digest: str
    arrival_momentum: float | None = Field(default=None, ge=0.0)
    momentum_model: str | None = None
    momentum_updated_at: datetime | None = None
    last_evidence_key: str | None = None


class EventStateV01(BaseModel):
    contract: str = EVENT_STATE_V01_CONTRACT
    event_id: UUID
    world_state: WorldStateV01
    evidence_state: EvidenceStateV01
    history_head_revision_id: UUID | None = None
    state_digest: str

    @model_validator(mode="after")
    def validate_digest(self):
        expected = event_state_v01_digest(
            event_id=self.event_id,
            world_state=self.world_state,
            evidence_state=self.evidence_state,
            history_head_revision_id=self.history_head_revision_id,
        )
        if self.state_digest != expected:
            raise ValueError("event-state-v0.1 digest mismatch")
        return self


class EvidenceObservationV01Legacy(BaseModel):
    evidence_key: str = Field(min_length=1)
    observed_at: datetime
    member_source_count: int = Field(ge=0)
    independent_source_count: int = Field(ge=0)
    secondary_report_count: int = Field(ge=0)
    relational_digest: str
    innovation: float = Field(ge=0.0)


class EventStateDeltaV01(BaseModel):
    contract: str = RECURSIVE_FILTER_CONTRACT
    world_state: WorldStateV01
    evidence_observation: EvidenceObservationV01Legacy


# Historical import alias retained for existing eval/tests.
EvidenceObservationV01 = EvidenceObservationV01Legacy


def world_state_from_event(event: Event) -> WorldStateV01:
    return WorldStateV01(
        title=event.title,
        event_type=event.event_type,
        actors=tuple(sorted(str(value) for value in (event.actors or []))),
        action=event.action,
        object=event.object,
        occurred_at=event.occurred_at,
        time_context=event.time_context,
        location=event.location,
        summary=event.summary,
        current_state=event.current_state,
        status=str(event.status),
    )


def active_event_source_ids(db: Session, event_id: UUID) -> list[UUID]:
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
    return sorted(
        (
            source_id
            for source_id, row in latest.items()
            if str(row.action).upper() == "ASSERT"
            and str(row.membership).upper() == "REPORTS_EVENT"
        ),
        key=str,
    )


def structural_evidence_state(
    db: Session,
    event_id: UUID,
    *,
    arrival_momentum: float | None = None,
    momentum_model: str | None = None,
    momentum_updated_at: datetime | None = None,
    last_evidence_key: str | None = None,
) -> EvidenceStateV01:
    source_ids = active_event_source_ids(db, event_id)
    relational = freeze_analysis_relational_context(db, source_ids)
    return EvidenceStateV01(
        member_source_count=len(source_ids),
        independent_source_count=relational.independent_sources,
        secondary_report_count=relational.secondary_reports,
        relational_digest=relational.digest,
        arrival_momentum=(
            float(arrival_momentum) if arrival_momentum is not None else None
        ),
        momentum_model=momentum_model,
        momentum_updated_at=momentum_updated_at,
        last_evidence_key=last_evidence_key,
    )


def event_state_v01_digest(
    *,
    event_id: UUID,
    world_state: WorldStateV01,
    evidence_state: EvidenceStateV01,
    history_head_revision_id: UUID | None,
) -> str:
    return _stable_digest(
        {
            "contract": EVENT_STATE_V01_CONTRACT,
            "event_id": str(event_id),
            "world_state": world_state.model_dump(mode="json"),
            "evidence_state": evidence_state.model_dump(mode="json"),
            "history_head_revision_id": (
                str(history_head_revision_id) if history_head_revision_id else None
            ),
        }
    )


# Historical public alias retained for existing tests/writers.
event_state_digest = event_state_v01_digest


def make_event_state(
    *,
    event_id: UUID,
    world_state: WorldStateV01,
    evidence_state: EvidenceStateV01,
    history_head_revision_id: UUID | None = None,
) -> EventStateV01:
    return EventStateV01(
        event_id=event_id,
        world_state=world_state,
        evidence_state=evidence_state,
        history_head_revision_id=history_head_revision_id,
        state_digest=event_state_v01_digest(
            event_id=event_id,
            world_state=world_state,
            evidence_state=evidence_state,
            history_head_revision_id=history_head_revision_id,
        ),
    )


def snapshot_event_state(db: Session, event: Event) -> EventStateV01:
    """Historical V0.1 writer retained until Phase17.1 rollout."""
    return make_event_state(
        event_id=event.id,
        world_state=world_state_from_event(event),
        evidence_state=structural_evidence_state(db, event.id),
    )


# ---------------------------------------------------------------------------
# Generic recursive/filter primitives retained for ablation.
# ---------------------------------------------------------------------------


def leaky_accumulate(
    previous: float,
    innovation: float,
    *,
    elapsed_hours: float,
    retention_per_hour: float,
) -> float:
    if previous < 0 or innovation < 0:
        raise ValueError("leaky accumulator values must be non-negative")
    if elapsed_hours < 0:
        raise ValueError("elapsed_hours must be non-negative")
    if not 0.0 < retention_per_hour <= 1.0:
        raise ValueError("retention_per_hour must be in (0, 1]")
    decayed = previous * math.pow(retention_per_hour, elapsed_hours)
    return decayed + innovation


def reduce_event_state(
    previous: EventStateV01 | None,
    delta: EventStateDeltaV01,
    *,
    event_id: UUID,
    retention_per_hour: float,
    history_head_revision_id: UUID | None = None,
) -> EventStateV01:
    """Historical V0.1 recursive-filter primitive retained for ablation tests."""
    observation = delta.evidence_observation

    if (
        previous is not None
        and previous.evidence_state.last_evidence_key == observation.evidence_key
    ):
        return previous.model_copy(deep=True)

    previous_momentum = (
        (previous.evidence_state.arrival_momentum or 0.0)
        if previous is not None
        else 0.0
    )
    previous_time = (
        previous.evidence_state.momentum_updated_at if previous is not None else None
    )
    if previous_time is None:
        elapsed_hours = 0.0
    else:
        current = observation.observed_at
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        prior = previous_time
        if prior.tzinfo is None:
            prior = prior.replace(tzinfo=timezone.utc)
        elapsed_hours = max(0.0, (current - prior).total_seconds() / 3600.0)

    momentum = leaky_accumulate(
        previous_momentum,
        observation.innovation,
        elapsed_hours=elapsed_hours,
        retention_per_hour=retention_per_hour,
    )
    evidence_state = EvidenceStateV01(
        member_source_count=observation.member_source_count,
        independent_source_count=observation.independent_source_count,
        secondary_report_count=observation.secondary_report_count,
        relational_digest=observation.relational_digest,
        arrival_momentum=momentum,
        momentum_model=f"leaky-integrator-retention-{retention_per_hour:.6g}-per-hour",
        momentum_updated_at=observation.observed_at,
        last_evidence_key=observation.evidence_key,
    )
    return make_event_state(
        event_id=event_id,
        world_state=delta.world_state,
        evidence_state=evidence_state,
        history_head_revision_id=history_head_revision_id,
    )


class HysteresisThresholdsV01(BaseModel):
    enter_aware: float = Field(ge=0.0, le=1.0)
    exit_aware: float = Field(ge=0.0, le=1.0)
    enter_watch: float = Field(ge=0.0, le=1.0)
    exit_watch: float = Field(ge=0.0, le=1.0)
    enter_engage: float = Field(ge=0.0, le=1.0)
    exit_engage: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bands(self):
        if not (
            self.exit_aware < self.enter_aware
            <= self.exit_watch
            < self.enter_watch
            <= self.exit_engage
            < self.enter_engage
        ):
            raise ValueError(
                "thresholds must form ordered hysteresis bands: "
                "exit_aware < enter_aware <= exit_watch < enter_watch "
                "<= exit_engage < enter_engage"
            )
        return self


_ATTENTION_ORDER = (
    Disposition.DROP,
    Disposition.AWARE,
    Disposition.WATCH,
    Disposition.ENGAGE,
)


def hysteretic_attention_transition(
    previous: Disposition,
    signal: float,
    thresholds: HysteresisThresholdsV01,
) -> Disposition:
    if not 0.0 <= signal <= 1.0:
        raise ValueError("signal must be normalized to [0, 1]")

    enter = {
        Disposition.AWARE: thresholds.enter_aware,
        Disposition.WATCH: thresholds.enter_watch,
        Disposition.ENGAGE: thresholds.enter_engage,
    }
    exit_threshold = {
        Disposition.AWARE: thresholds.exit_aware,
        Disposition.WATCH: thresholds.exit_watch,
        Disposition.ENGAGE: thresholds.exit_engage,
    }

    index = _ATTENTION_ORDER.index(previous)

    while index < len(_ATTENTION_ORDER) - 1:
        next_level = _ATTENTION_ORDER[index + 1]
        if signal < enter[next_level]:
            break
        index += 1

    while index > 0:
        current_level = _ATTENTION_ORDER[index]
        if signal >= exit_threshold[current_level]:
            break
        index -= 1

    return _ATTENTION_ORDER[index]
