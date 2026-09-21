from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Callable, Generic, Iterable, TypeVar
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import EventRevision
from app.services.event_observation import EventObservationV01


REPLAY_CONTRACT = "event-observation-replay-v0.1"


def _stable_digest(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class ObservationReplay:
    event_id: UUID
    observations: tuple[EventObservationV01, ...]
    stream_digest: str
    legacy_revision_count: int

    @property
    def latest_evidence_time(self) -> datetime | None:
        if not self.observations:
            return None
        return self.observations[-1].evidence_time


def ordered_revision_observations(
    db: Session,
    event_id: UUID,
) -> ObservationReplay:
    """Read durable V2 observations in semantic/evidence-time order.

    Legacy revisions are counted but not invented/backfilled here. They form the
    historical checkpoint that predates durable observation identity.
    """

    rows = db.execute(
        select(EventRevision).where(EventRevision.event_id == event_id)
    ).scalars().all()

    observations: list[EventObservationV01] = []
    legacy = 0
    seen: set[str] = set()

    for row in rows:
        payload = dict(row.revision_payload or {})
        raw = payload.get("observation")
        has_key = bool(row.observation_key)
        has_payload = isinstance(raw, dict)
        if not has_key and not has_payload:
            legacy += 1
            continue
        if has_key != has_payload:
            raise RuntimeError(
                f"EventRevision {row.id} has incomplete durable observation identity"
            )
        try:
            observation = EventObservationV01.model_validate(raw)
        except ValidationError as exc:
            raise RuntimeError(
                f"EventRevision {row.id} has invalid durable observation payload"
            ) from exc
        if observation.event_id != event_id:
            raise RuntimeError(
                f"EventRevision {row.id} observation belongs to another Event"
            )
        if observation.observation_key != row.observation_key:
            raise RuntimeError(
                f"EventRevision {row.id} observation_key mismatch"
            )
        if observation.observation_key in seen:
            raise RuntimeError(
                f"Duplicate Event observation key {observation.observation_key}"
            )
        seen.add(observation.observation_key)
        observations.append(observation)

    observations.sort(
        key=lambda row: (
            _utc(row.evidence_time),
            row.observation_key,
        )
    )
    digest = _stable_digest(
        {
            "contract": REPLAY_CONTRACT,
            "event_id": str(event_id),
            "observation_keys": [row.observation_key for row in observations],
            "evidence_times": [
                _utc(row.evidence_time).isoformat() for row in observations
            ],
        }
    )
    return ObservationReplay(
        event_id=event_id,
        observations=tuple(observations),
        stream_digest=digest,
        legacy_revision_count=legacy,
    )


def is_late_observation(
    replay: ObservationReplay,
    observation: EventObservationV01,
) -> bool:
    latest = replay.latest_evidence_time
    if latest is None:
        return False
    return _utc(observation.evidence_time) < _utc(latest)


T = TypeVar("T")


def replay_observation_stream(
    observations: Iterable[EventObservationV01],
    *,
    initial_state: T,
    reducer: Callable[[T, EventObservationV01], T],
) -> T:
    """Generic deterministic replay harness.

    Semantic state equality is intentionally deferred until Phase17.2 supplies
    the frozen Phi/R reducer. Phase17.1 validates ordering/exactly-once substrate.
    """

    ordered = sorted(
        observations,
        key=lambda row: (_utc(row.evidence_time), row.observation_key),
    )
    state = initial_state
    seen: set[str] = set()
    for observation in ordered:
        if observation.observation_key in seen:
            continue
        seen.add(observation.observation_key)
        state = reducer(state, observation)
    return state
