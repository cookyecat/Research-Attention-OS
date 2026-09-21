from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.acquisition import AcquisitionObservation, InformationSnapshot
from app.models.event import Event, EventEvidenceFrame
from app.models.source import Source
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.event_state import active_event_source_ids
from app.services.source_graph import freeze_analysis_relational_context


EVENT_OBSERVATION_CONTRACT = "event-observation-v0.1"
OBSERVATION_KEY_CONTRACT = "event-observation-key-v0.1"


def _stable_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EventObservationV01(BaseModel):
    """Stable logical observation consumed by one Event-keyed recursive filter."""

    contract: str = EVENT_OBSERVATION_CONTRACT
    event_id: UUID
    observation_key: str = Field(min_length=16, max_length=128)

    source_id: UUID
    source_snapshot_id: UUID | None = None
    frame_ids: tuple[UUID, ...] = ()
    semantic_input_digests: tuple[str, ...] = ()

    evidence_time: datetime
    ingest_time: datetime
    world_time: datetime | None = None

    provenance_digest: str
    audited_semantic_unit_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def normalize(self):
        object.__setattr__(
            self,
            "frame_ids",
            tuple(sorted(set(self.frame_ids), key=str)),
        )
        object.__setattr__(
            self,
            "semantic_input_digests",
            tuple(sorted({str(value).strip() for value in self.semantic_input_digests if str(value).strip()})),
        )
        object.__setattr__(
            self,
            "audited_semantic_unit_refs",
            tuple(sorted({str(value).strip() for value in self.audited_semantic_unit_refs if str(value).strip()})),
        )
        object.__setattr__(self, "evidence_time", _as_utc(self.evidence_time))
        object.__setattr__(self, "ingest_time", _as_utc(self.ingest_time))
        object.__setattr__(self, "world_time", _as_utc(self.world_time))
        return self


def _latest_snapshot(db: Session, source_id: UUID) -> InformationSnapshot | None:
    return db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.raos_source_id == source_id)
        .order_by(InformationSnapshot.captured_at.desc(), InformationSnapshot.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _snapshot_for_frames(
    db: Session,
    *,
    source_id: UUID,
    frames: list[EventEvidenceFrame],
) -> InformationSnapshot | None:
    """Bind Observation content identity to the Snapshot actually audited.

    Falling back to the latest Source snapshot is legal only when the frame
    batch carries no snapshot identity. A mixed-snapshot frame batch is an
    integrity violation and fails closed.
    """
    snapshot_ids = {
        frame.source_snapshot_id
        for frame in frames
        if frame.source_snapshot_id is not None
    }
    if len(snapshot_ids) > 1:
        raise RuntimeError(
            f"Source {source_id} latest EventEvidenceFrame batch spans "
            f"{len(snapshot_ids)} snapshots"
        )
    if len(snapshot_ids) == 1:
        snapshot_id = next(iter(snapshot_ids))
        snapshot = db.get(InformationSnapshot, snapshot_id)
        if snapshot is None:
            raise RuntimeError(
                f"EventEvidenceFrame references missing InformationSnapshot {snapshot_id}"
            )
        if snapshot.raos_source_id != source_id:
            raise RuntimeError(
                f"EventEvidenceFrame snapshot {snapshot_id} belongs to another Source"
            )
        return snapshot
    return _latest_snapshot(db, source_id)


def _fallback_observed_at(
    db: Session,
    snapshot: InformationSnapshot | None,
) -> datetime | None:
    if snapshot is None:
        return None
    return db.execute(
        select(AcquisitionObservation.observed_at)
        .where(AcquisitionObservation.external_item_id == snapshot.external_item_id)
        .order_by(AcquisitionObservation.observed_at.asc(), AcquisitionObservation.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def _semantic_unit_refs(frames: list[EventEvidenceFrame]) -> tuple[str, ...]:
    refs: set[str] = set()
    for frame in frames:
        payload = dict(frame.frame_payload or {})
        for row in payload.get("audited_semantic_units") or []:
            if not isinstance(row, dict):
                continue
            unit_id = str(row.get("unit_id") or "").strip()
            if unit_id:
                refs.add(unit_id)
    return tuple(sorted(refs))


def observation_key_for(
    *,
    event_id: UUID,
    source: Source,
    snapshot: InformationSnapshot | None,
    semantic_input_digests: tuple[str, ...] | list[str],
) -> str:
    """Stable identity of admitted evidence, independent of runtime/frame row UUIDs."""

    content_identity = None
    if snapshot is not None and snapshot.content_hash:
        content_identity = f"snapshot-content:{snapshot.content_hash}"
    elif source.content_hash:
        content_identity = f"source-content:{source.content_hash}"
    else:
        content_identity = f"source-fingerprint:{source.fingerprint}"

    return _stable_digest(
        {
            "contract": OBSERVATION_KEY_CONTRACT,
            "event_id": str(event_id),
            "source_id": str(source.id),
            "content_identity": content_identity,
            "semantic_input_digests": sorted(
                {str(value).strip() for value in semantic_input_digests if str(value).strip()}
            ),
        }
    )


def materialize_event_observation(
    db: Session,
    *,
    event: Event,
    source: Source,
) -> EventObservationV01:
    """Build one replay-stable observation from already persisted audited evidence."""

    frames = latest_event_evidence_frames_for_source(db, source.id)
    semantic_digests = tuple(
        sorted({str(frame.semantic_input_digest) for frame in frames})
    )
    refs = _semantic_unit_refs(frames)
    snapshot = _snapshot_for_frames(
        db,
        source_id=source.id,
        frames=frames,
    )

    fallback_observed = _fallback_observed_at(db, snapshot)
    evidence_time = (
        source.published_at
        or fallback_observed
        or (snapshot.captured_at if snapshot is not None else None)
        or source.ingested_at
    )
    ingest_time = (
        snapshot.captured_at
        if snapshot is not None and snapshot.captured_at is not None
        else source.ingested_at
    )

    event_source_ids = active_event_source_ids(db, event.id)
    relational = freeze_analysis_relational_context(db, event_source_ids)

    return EventObservationV01(
        event_id=event.id,
        observation_key=observation_key_for(
            event_id=event.id,
            source=source,
            snapshot=snapshot,
            semantic_input_digests=semantic_digests,
        ),
        source_id=source.id,
        source_snapshot_id=(snapshot.id if snapshot is not None else None),
        frame_ids=tuple(frame.id for frame in frames),
        semantic_input_digests=semantic_digests,
        evidence_time=evidence_time,
        ingest_time=ingest_time,
        world_time=event.occurred_at,
        provenance_digest=relational.digest,
        audited_semantic_unit_refs=refs,
    )
