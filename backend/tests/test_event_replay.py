from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.services.event_observation import EventObservationV01
from app.services.event_replay import replay_observation_stream


def _obs(event_id, key: str, when: str) -> EventObservationV01:
    return EventObservationV01(
        event_id=event_id,
        observation_key=key,
        source_id=uuid4(),
        source_snapshot_id=None,
        frame_ids=(),
        semantic_input_digests=(f"sem-{key}",),
        evidence_time=datetime.fromisoformat(when).replace(tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, 21, tzinfo=timezone.utc),
        world_time=None,
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=(f"unit-{key}",),
    )


def test_replay_orders_by_evidence_time_not_arrival_order():
    event_id = uuid4()
    later = _obs(event_id, "b" * 64, "2026-09-20T10:00:00")
    earlier = _obs(event_id, "a" * 64, "2026-09-18T10:00:00")

    result = replay_observation_stream(
        [later, earlier],
        initial_state=[],
        reducer=lambda state, obs: [*state, obs.observation_key],
    )

    assert result == [earlier.observation_key, later.observation_key]


def test_replay_is_exactly_once_even_if_input_contains_duplicate_observation():
    event_id = uuid4()
    first = _obs(event_id, "a" * 64, "2026-09-18T10:00:00")
    second = _obs(event_id, "b" * 64, "2026-09-19T10:00:00")

    result = replay_observation_stream(
        [first, second, first],
        initial_state=0,
        reducer=lambda state, _obs: state + 1,
    )

    assert result == 2


def test_persisted_revision_replay_uses_evidence_time_not_parent_order(db):
    from app.models.event import Event, EventRevision
    from app.services.event_replay import ordered_revision_observations

    event = Event(
        title="Jev emergence",
        event_type="MODEL_LAUNCH",
        actors=["Jev team"],
        action="launch",
        object="Jev",
        summary="Jev emergence",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()

    later = _obs(event.id, "b" * 64, "2026-09-20T10:00:00")
    earlier = _obs(event.id, "a" * 64, "2026-09-18T10:00:00")

    r1 = EventRevision(
        workspace_id="local-default",
        event_id=event.id,
        parent_revision_id=None,
        observation_key=later.observation_key,
        revision_payload={
            "contract": "event-revision-v2",
            "observation": later.model_dump(mode="json"),
        },
        revision_digest="rev-later",
        audit_run_id=None,
        authority_epoch=1,
    )
    db.add(r1)
    db.flush()

    r2 = EventRevision(
        workspace_id="local-default",
        event_id=event.id,
        parent_revision_id=r1.id,
        observation_key=earlier.observation_key,
        revision_payload={
            "contract": "event-revision-v2",
            "observation": earlier.model_dump(mode="json"),
        },
        revision_digest="rev-earlier",
        audit_run_id=None,
        authority_epoch=1,
    )
    db.add(r2)
    db.flush()

    replay = ordered_revision_observations(db, event.id)

    assert [row.observation_key for row in replay.observations] == [
        earlier.observation_key,
        later.observation_key,
    ]
    assert replay.legacy_revision_count == 0
