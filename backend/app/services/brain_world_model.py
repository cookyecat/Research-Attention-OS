from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable

BRAIN_WORLD_MODEL_VERSION = "brain-world-model-v0.1"


class BrainStateAuthority(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    DERIVED = "DERIVED"
    ADVISORY = "ADVISORY"


class BrainStateSource(str, Enum):
    USER_EXPLICIT_RUNTIME = "USER_EXPLICIT_RUNTIME"
    SYSTEM_COMMITTED = "SYSTEM_COMMITTED"
    KERNEL_COMMITTED = "KERNEL_COMMITTED"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BrainStateFact:
    key: str
    value: Any
    source: BrainStateSource
    authority: BrainStateAuthority
    observed_at: datetime
    provenance: str
    valid_until: datetime | None = None
    confidence: float | None = None
    def is_fresh(self, *, now: datetime | None = None) -> bool:
        if self.valid_until is None:
            return True
        now = now or datetime.now(timezone.utc)
        return self.valid_until >= now

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "source": self.source.value,
            "authority": self.authority.value,
            "observed_at": self.observed_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "provenance": self.provenance,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class BrainWorldSnapshot:
    captured_at: datetime
    runtime_facts: tuple[BrainStateFact, ...]
    advisory_facts: tuple[BrainStateFact, ...] = ()
    kernel_snapshot_hash: str | None = None
    active_watch_ids: tuple[str, ...] = ()
    standing_radar_anchor: str | None = None
    def as_dict(self) -> dict[str, Any]:
        return {
            "version": BRAIN_WORLD_MODEL_VERSION,
            "captured_at": self.captured_at.isoformat(),
            "runtime_facts": [f.as_dict() for f in self.runtime_facts],
            "advisory_facts": [f.as_dict() for f in self.advisory_facts],
            "kernel_snapshot_hash": self.kernel_snapshot_hash,
            "active_watch_ids": list(self.active_watch_ids),
            "standing_radar_anchor": self.standing_radar_anchor,
        }

    def authoritative_value(self, key: str, *, now: datetime | None = None, default=None):
        candidates = [
            fact for fact in self.runtime_facts
            if fact.key == key
            and fact.authority == BrainStateAuthority.AUTHORITATIVE
            and fact.is_fresh(now=now)
        ]
        if not candidates:
            return default
        candidates.sort(key=lambda fact: fact.observed_at, reverse=True)
        return candidates[0].value


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
def explicit_runtime_fact(
    key: str,
    value: Any,
    *,
    observed_at: datetime,
    provenance: str,
    valid_until: datetime | None = None,
) -> BrainStateFact:
    return BrainStateFact(
        key=key,
        value=value,
        source=BrainStateSource.USER_EXPLICIT_RUNTIME,
        authority=BrainStateAuthority.AUTHORITATIVE,
        observed_at=_utc(observed_at),
        valid_until=_utc(valid_until) if valid_until else None,
        provenance=provenance,
        confidence=1.0,
    )


def model_inference_fact(
    key: str,
    value: Any,
    *,
    observed_at: datetime | None = None,
    provenance: str,
    confidence: float | None = None,
) -> BrainStateFact:
    return BrainStateFact(
        key=key,
        value=value,
        source=BrainStateSource.MODEL_INFERENCE,
        authority=BrainStateAuthority.DERIVED,
        observed_at=_utc(observed_at),
        provenance=provenance,
        confidence=confidence,
    )


def _runtime_context_facts(ctx) -> tuple[BrainStateFact, ...]:
    if ctx is None:
        return ()
    observed_at = _utc(getattr(ctx, "captured_at", None))
    provenance = f"runtime_context:{getattr(ctx, 'id', 'transient')}"
    values = {
        "current_task": getattr(ctx, "current_task", None),
        "session_topic": getattr(ctx, "session_topic", None),
        "available_attention_minutes": getattr(ctx, "available_attention_minutes", None),
        "interruptibility": getattr(ctx, "interruptibility", None),
        "cognitive_capacity": getattr(ctx, "cognitive_capacity", None),
        "deadline_at": getattr(ctx, "deadline_at", None),
        "threatens_active_work": getattr(ctx, "threatens_active_work", None),
    }
    return tuple(
        explicit_runtime_fact(key, value, observed_at=observed_at, provenance=provenance)
        for key, value in values.items()
        if value is not None
    )
def _runtime_view_facts(view, *, observed_at: datetime) -> tuple[BrainStateFact, ...]:
    if view is None:
        return ()
    values = {
        "current_task": getattr(view, "current_task", None),
        "session_topic": getattr(view, "session_topic", None),
        "available_attention_minutes": getattr(view, "available_attention_minutes", None),
        "interruptibility": getattr(view, "interruptibility", None),
        "cognitive_capacity": getattr(view, "cognitive_capacity", None),
        "deadline_minutes": getattr(view, "deadline_minutes", None),
        "threatens_active_work": getattr(view, "threatens_active_work", None),
    }
    return tuple(
        explicit_runtime_fact(
            key, value, observed_at=observed_at, provenance="explicit runtime view override"
        )
        for key, value in values.items() if value is not None
    )


def active_watch_ids(db) -> tuple[str, ...]:
    if db is None:
        return ()
    from sqlalchemy import select
    from app.models.watch import Watch

    rows = db.execute(select(Watch.id).where(Watch.status == "ACTIVE")).scalars().all()
    return tuple(sorted(str(value) for value in rows))


def build_brain_world_snapshot(
    *,
    runtime_context=None,
    runtime_view=None,
    db=None,
    kernel_snapshot_hash: str | None = None,
    advisory_facts: Iterable[BrainStateFact] = (),
    standing_radar_anchor: str | None = None,
    captured_at: datetime | None = None,
) -> BrainWorldSnapshot:
    captured_at = _utc(captured_at)
    return BrainWorldSnapshot(
        captured_at=captured_at,
        runtime_facts=(
            _runtime_context_facts(runtime_context)
            if runtime_context is not None
            else _runtime_view_facts(runtime_view, observed_at=captured_at)
        ),
        advisory_facts=tuple(advisory_facts),
        kernel_snapshot_hash=kernel_snapshot_hash,
        active_watch_ids=active_watch_ids(db),
        standing_radar_anchor=standing_radar_anchor,
    )
def runtime_view_from_brain_snapshot(snapshot: BrainWorldSnapshot, *, now: datetime | None = None):
    from app.services.scheduler import RuntimeView

    now = _utc(now)
    deadline_at = snapshot.authoritative_value("deadline_at", now=now)
    deadline_minutes = snapshot.authoritative_value("deadline_minutes", now=now)
    if isinstance(deadline_at, datetime):
        deadline_minutes = (_utc(deadline_at) - now).total_seconds() / 60.0
    return RuntimeView(
        current_task=snapshot.authoritative_value("current_task", now=now),
        session_topic=snapshot.authoritative_value("session_topic", now=now),
        available_attention_minutes=snapshot.authoritative_value("available_attention_minutes", now=now),
        interruptibility=snapshot.authoritative_value("interruptibility", now=now, default="MEDIUM"),
        cognitive_capacity=snapshot.authoritative_value("cognitive_capacity", now=now, default="NORMAL"),
        deadline_minutes=deadline_minutes,
        threatens_active_work=snapshot.authoritative_value("threatens_active_work", now=now),
    )


def trusted_bool(snapshot: BrainWorldSnapshot, key: str, *, now: datetime | None = None) -> bool:
    return bool(snapshot.authoritative_value(key, now=_utc(now), default=False))
