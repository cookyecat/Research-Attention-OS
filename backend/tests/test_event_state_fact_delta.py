from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state_fact_delta import (
    CurrentFactV01,
    FactDeltaV01,
    FactSupersessionV01,
    apply_fact_delta,
)


def _event(db) -> Event:
    row = Event(
        title="Jev emergence",
        event_type="MODEL_LAUNCH",
        actors=["Jev team"],
        action="launch and early validation",
        object="Jev",
        summary="Jev emergence.",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(row)
    db.flush()
    return row
def _source(db, label: str) -> Source:
    row = Source(
        source_type="TEXT",
        title=label,
        content_text=label,
        fingerprint=f"phase17-fact-delta-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    return row


def _member(db, event: Event, source: Source, *, local: bool = False):
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
            authority_policy_version="phase17-fact-delta-test",
            authority_epoch=1,
            authority_status="AUTHORIZED_SOURCE_LOCAL" if local else "AUTHORIZED",
            supersedes_assertion_id=None,
        )
    )
    db.flush()
def _obs(
    event: Event,
    source: Source,
    key: str,
    refs: tuple[str, ...],
    day: int,
) -> EventObservationV01:
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


def _fact(fid: str, text: str, refs: tuple[str, ...]) -> CurrentFactV01:
    return CurrentFactV01(
        fact_id=fid,
        text=text,
        support_refs=refs,
    )


def test_initial_fact_add_materializes_emerging_state(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, local=True)
    obs = _obs(event, a, "a", ("uLaunch",), 16)
    delta = FactDeltaV01(
        kind="ADD",
        add_facts=(
            _fact("fact0001", "Jev has been publicly released.", ("uLaunch",)),
        ),
    )
    result = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs,
        delta=delta,
        supporting_source_ids=[a.id],
    )

    assert result.fact_state.status == "EMERGING"
    assert len(result.fact_state.facts) == 1
    assert result.event_state.world_state.active_semantic_unit_refs == ("uLaunch",)
    assert result.event_state.world_state.synopsis == "Jev has been publicly released."


def test_none_preserves_facts_but_evidence_state_advances(db):
    event = _event(db)
    a = _source(db, "launch")
    b = _source(db, "duplicate report")
    _member(db, event, a, local=True)
    _member(db, event, b)

    first = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uLaunch",), 16),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(
                _fact("fact0001", "Jev has been publicly released.", ("uLaunch",)),
            ),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_fact_delta(
        db,
        event_id=event.id,
        previous=first.fact_state,
        observation=_obs(event, b, "b", (), 17),
        delta=None,
        supporting_source_ids=[a.id, b.id],
    )

    assert second.fact_state == first.fact_state
    assert second.event_state.world_state == first.event_state.world_state
    assert second.event_state.evidence_state.member_source_count == 2
    assert second.event_state.state_digest != first.event_state.state_digest


def test_add_can_merge_examples_into_one_broader_current_fact(db):
    event = _event(db)
    a = _source(db, "Mario demo")
    b = _source(db, "DOOM demo")
    _member(db, event, a, local=True)
    _member(db, event, b)

    first = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uMario",), 16),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(
                _fact(
                    "fact0001",
                    "Jev has a live game demo.",
                    ("uMario",),
                ),
            ),
        ),
        supporting_source_ids=[a.id],
    )

    merged = _fact(
        "fact0002",
        "Jev has multiple live game demonstrations.",
        ("uMario", "uDoom"),
    )
    second = apply_fact_delta(
        db,
        event_id=event.id,
        previous=first.fact_state,
        observation=_obs(event, b, "b", ("uDoom",), 17),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(merged,),
            retire_fact_ids=("fact0001",),
        ),
        supporting_source_ids=[a.id, b.id],
    )

    assert len(second.fact_state.facts) == 1
    assert second.fact_state.facts[0].fact_id == "fact0002"
    assert second.fact_state.facts[0].support_refs == ("uDoom", "uMario")
    assert second.event_state.world_state.active_semantic_unit_refs == (
        "uDoom",
        "uMario",
    )
    assert second.fact_state.status == "ACTIVE"


def test_supersede_replaces_current_fact(db):
    event = _event(db)
    a = _source(db, "old size")
    b = _source(db, "correction")
    _member(db, event, a, local=True)
    _member(db, event, b)

    first = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uOld",), 16),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(
                _fact("fact0001", "The model has 32B parameters.", ("uOld",)),
            ),
        ),
        supporting_source_ids=[a.id],
    )

    new_fact = _fact(
        "fact0002",
        "The model has 27B parameters.",
        ("uNew",),
    )
    second = apply_fact_delta(
        db,
        event_id=event.id,
        previous=first.fact_state,
        observation=_obs(event, b, "b", ("uNew",), 17),
        delta=FactDeltaV01(
            kind="SUPERSEDE",
            add_facts=(new_fact,),
            retire_fact_ids=("fact0001",),
            supersession_pairs=(
                FactSupersessionV01(
                    previous_fact_id="fact0001",
                    new_fact_id="fact0002",
                    reason="Authors explicitly corrected 32B to 27B.",
                ),
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    )

    assert [f.text for f in second.fact_state.facts] == [
        "The model has 27B parameters."
    ]
    assert second.event_state.world_state.active_semantic_unit_refs == ("uNew",)


def test_contest_keeps_both_current_facts(db):
    event = _event(db)
    a = _source(db, "positive reproduction")
    b = _source(db, "negative reproduction")
    _member(db, event, a, local=True)
    _member(db, event, b)

    first = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uPositive",), 16),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(
                _fact(
                    "fact0001",
                    "An independent reproduction reports a strong gain.",
                    ("uPositive",),
                ),
            ),
        ),
        supporting_source_ids=[a.id],
    )
    second = apply_fact_delta(
        db,
        event_id=event.id,
        previous=first.fact_state,
        observation=_obs(event, b, "b", ("uNegative",), 17),
        delta=FactDeltaV01(
            kind="CONTEST",
            add_facts=(
                _fact(
                    "fact0002",
                    "Another reproduction fails under comparable conditions.",
                    ("uNegative",),
                ),
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    )

    assert len(second.fact_state.facts) == 2
    assert second.fact_state.status == "CONTESTED"
    assert second.event_state.world_state.active_semantic_unit_refs == (
        "uNegative",
        "uPositive",
    )
def test_persisted_fact_delta_replays_to_same_fact_and_event_digests(db):
    event = _event(db)
    a = _source(db, "Mario demo")
    b = _source(db, "DOOM demo")
    _member(db, event, a, local=True)
    _member(db, event, b)
    obs_a = _obs(event, a, "a", ("uMario",), 16)
    obs_b = _obs(event, b, "b", ("uDoom",), 17)

    delta_a = FactDeltaV01(
        kind="ADD",
        add_facts=(
            _fact("fact0001", "Jev has a live game demo.", ("uMario",)),
        ),
    )
    delta_b = FactDeltaV01(
        kind="ADD",
        add_facts=(
            _fact(
                "fact0002",
                "Jev has multiple live game demonstrations.",
                ("uMario", "uDoom"),
            ),
        ),
        retire_fact_ids=("fact0001",),
    )

    online_a = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs_a,
        delta=delta_a,
        supporting_source_ids=[a.id],
    )
    online_b = apply_fact_delta(
        db,
        event_id=event.id,
        previous=online_a.fact_state,
        observation=obs_b,
        delta=delta_b,
        supporting_source_ids=[a.id, b.id],
    )

    replay_a = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=obs_a,
        delta=FactDeltaV01.model_validate(delta_a.model_dump(mode="json")),
        supporting_source_ids=[a.id],
    )
    replay_b = apply_fact_delta(
        db,
        event_id=event.id,
        previous=replay_a.fact_state,
        observation=obs_b,
        delta=FactDeltaV01.model_validate(delta_b.model_dump(mode="json")),
        supporting_source_ids=[a.id, b.id],
    )

    assert replay_b.fact_state.state_digest == online_b.fact_state.state_digest
    assert replay_b.event_state.state_digest == online_b.event_state.state_digest
    assert replay_b == online_b


def test_fact_delta_rejects_unsupported_future_support(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, local=True)
    obs = _obs(event, a, "a", ("uA",), 16)
    with pytest.raises(ValueError, match="unsupported semantic refs"):
        apply_fact_delta(
            db,
            event_id=event.id,
            previous=None,
            observation=obs,
            delta=FactDeltaV01(
                kind="ADD",
                add_facts=(
                    _fact(
                        "fact0001",
                        "Invented unsupported fact.",
                        ("uFuture",),
                    ),
                ),
            ),
            supporting_source_ids=[a.id],
        )


def test_add_retirement_cannot_forget_retired_fact_support(db):
    event = _event(db)
    a = _source(db, "Mario and DOOM demos")
    b = _source(db, "Tetris demo")
    _member(db, event, a, local=True)
    _member(db, event, b)

    first = apply_fact_delta(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uMario", "uDoom"), 16),
        delta=FactDeltaV01(
            kind="ADD",
            add_facts=(
                _fact(
                    "fact0001",
                    "Jev has multiple live game demonstrations.",
                    ("uMario", "uDoom"),
                ),
            ),
        ),
        supporting_source_ids=[a.id],
    )

    with pytest.raises(ValueError, match="ADD retirement must preserve all support"):
        apply_fact_delta(
            db,
            event_id=event.id,
            previous=first.fact_state,
            observation=_obs(event, b, "b", ("uTetris",), 17),
            delta=FactDeltaV01(
                kind="ADD",
                add_facts=(
                    _fact(
                        "fact0002",
                        "Jev has a Tetris demonstration.",
                        ("uTetris",),
                    ),
                ),
                retire_fact_ids=("fact0001",),
            ),
            supporting_source_ids=[a.id, b.id],
        )
