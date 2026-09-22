from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state_delta import (
    StateDeltaV01,
    apply_state_delta,
)


def _event(db) -> Event:
    event = Event(
        title="Jev emergence",
        event_type="MODEL_LAUNCH",
        actors=["Jev team"],
        action="launch and early validation",
        object="Jev",
        summary="Jev emergence.",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    return event
def _source(db, label: str) -> Source:
    source = Source(
        source_type="TEXT",
        title=label,
        content_text=label,
        fingerprint=f"phase17-delta-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(source)
    db.flush()
    return source


def _member(db, event: Event, source: Source, *, status: str = "AUTHORIZED_SOURCE_LOCAL"):
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source.id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={},
            audit_run_id=None,
            authority_policy_version="phase17-delta-test",
            authority_epoch=1,
            authority_status=status,
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _obs(event: Event, source: Source, key: str, refs: tuple[str, ...], day: int):
    return EventObservationV01(
        event_id=event.id,
        observation_key=key * 64,
        source_id=source.id,
        semantic_input_digests=(f"sem-{key}",),
        evidence_time=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, day, 12, 1, tzinfo=timezone.utc),
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=refs,
    )


def _units(*pairs):
    return {ref: {"unit_id": ref, "statement": statement} for ref, statement in pairs}


def test_initial_add_materializes_emerging_state(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a)
    obs = _obs(event, a, "a", ("uLaunch",), 16)
    units = _units(("uLaunch", "Jev was publicly released."))

    result = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs,
        delta=StateDeltaV01(kind="ADD", activate_refs=("uLaunch",)),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    )

    assert result.delta_kind == "ADD"
    assert result.next_state.world_state.status == "EMERGING"
    assert result.next_state.world_state.active_semantic_unit_refs == ("uLaunch",)
    assert result.next_state.world_state.synopsis == "Jev was publicly released."


def test_none_preserves_world_state_but_advances_evidence_state(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "duplicate report")
    _member(db, event, a)
    _member(db, event, b)
    units = _units(("uLaunch", "Jev was publicly released."))

    first = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=StateDeltaV01(kind="ADD", activate_refs=("uLaunch",)),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state

    second = apply_state_delta(
        db,
        event_id=event.id,
        previous=first,
        observation=_obs(event, b, "b", (), 17),
        delta=None,
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    assert second.world_state == first.world_state
    assert second.evidence_state.member_source_count == 2
    assert second.state_digest != first.state_digest


def test_add_can_compact_redundant_previous_support(db):
    event = _event(db)
    a = _source(db, "early demo")
    b = _source(db, "broader current evidence")
    _member(db, event, a)
    _member(db, event, b)
    units = _units(
        ("uOld", "Jev was shown in one early demo."),
        ("uNew", "Jev has now been demonstrated across multiple live tasks."),
    )
    first = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uOld",), 16),
        delta=StateDeltaV01(kind="ADD", activate_refs=("uOld",)),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state

    second = apply_state_delta(
        db,
        event_id=event.id,
        previous=first,
        observation=_obs(event, b, "b", ("uNew",), 17),
        delta=StateDeltaV01(
            kind="ADD",
            activate_refs=("uNew",),
            retire_refs=("uOld",),
        ),
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    assert second.world_state.status == "ACTIVE"
    assert second.world_state.active_semantic_unit_refs == ("uNew",)


def test_supersede_retires_corrected_support(db):
    event = _event(db)
    a = _source(db, "old report")
    b = _source(db, "author correction")
    _member(db, event, a)
    _member(db, event, b)
    units = _units(
        ("uOld", "The model has 32B parameters."),
        ("uNew", "The authors corrected the model size to 27B parameters."),
    )
    first = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uOld",), 16),
        delta=StateDeltaV01(kind="ADD", activate_refs=("uOld",)),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state

    delta = StateDeltaV01(
        kind="SUPERSEDE",
        activate_refs=("uNew",),
        retire_refs=("uOld",),
        supersession_pairs=(
            {
                "previous_ref": "uOld",
                "new_ref": "uNew",
                "reason": "The authors explicitly corrected the earlier size.",
            },
        ),
    )
    second = apply_state_delta(
        db,
        event_id=event.id,
        previous=first,
        observation=_obs(event, b, "b", ("uNew",), 17),
        delta=delta,
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    assert second.world_state.active_semantic_unit_refs == ("uNew",)
    assert "32B" not in second.world_state.synopsis
    assert "27B" in second.world_state.synopsis


def test_contest_keeps_previous_and_new_live_sides(db):
    event = _event(db)
    a = _source(db, "positive reproduction")
    b = _source(db, "negative reproduction")
    _member(db, event, a)
    _member(db, event, b)
    units = _units(
        ("uPositive", "Independent reproduction reports a strong gain."),
        ("uNegative", "Another reproduction fails under comparable conditions."),
    )
    first = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uPositive",), 16),
        delta=StateDeltaV01(kind="ADD", activate_refs=("uPositive",)),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state

    second = apply_state_delta(
        db,
        event_id=event.id,
        previous=first,
        observation=_obs(event, b, "b", ("uNegative",), 17),
        delta=StateDeltaV01(kind="CONTEST", activate_refs=("uNegative",)),
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    assert second.world_state.status == "CONTESTED"
    assert second.world_state.active_semantic_unit_refs == ("uNegative", "uPositive")


def test_persisted_deltas_replay_to_identical_digest(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "new demo")
    _member(db, event, a)
    _member(db, event, b)
    units = _units(
        ("uA", "Jev launched."),
        ("uB", "A live demo was published."),
    )
    obs_a = _obs(event, a, "a", ("uA",), 16)
    obs_b = _obs(event, b, "b", ("uB",), 17)
    delta_a = StateDeltaV01(kind="ADD", activate_refs=("uA",))
    delta_b = StateDeltaV01(kind="ADD", activate_refs=("uB",))

    online_a = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs_a,
        delta=delta_a,
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state
    online_b = apply_state_delta(
        db,
        event_id=event.id,
        previous=online_a,
        observation=obs_b,
        delta=delta_b,
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    replay_a = apply_state_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs_a,
        delta=StateDeltaV01.model_validate(delta_a.model_dump(mode="json")),
        supporting_source_ids=[a.id],
        semantic_units_by_ref=units,
    ).next_state
    replay_b = apply_state_delta(
        db,
        event_id=event.id,
        previous=replay_a,
        observation=obs_b,
        delta=StateDeltaV01.model_validate(delta_b.model_dump(mode="json")),
        supporting_source_ids=[a.id, b.id],
        semantic_units_by_ref=units,
    ).next_state

    assert replay_b.state_digest == online_b.state_digest
    assert replay_b == online_b


def test_delta_rejects_activation_outside_new_observation(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a)
    obs = _obs(event, a, "a", ("uA",), 16)

    with pytest.raises(ValueError, match="activate_refs"):
        apply_state_delta(
            db,
            event_id=event.id,
            previous=None,
            observation=obs,
            delta=StateDeltaV01(kind="ADD", activate_refs=("uInvented",)),
            supporting_source_ids=[a.id],
            semantic_units_by_ref=_units(("uInvented", "Invented.")),
        )
