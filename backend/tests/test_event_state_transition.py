from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state import WorldStateV02
from app.services.event_state_transition import (
    StateTransitionProposalV01,
    reduce_state_transition,
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
        fingerprint=f"phase17-transition-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(source)
    db.flush()
    return source


def _member(db, event: Event, source: Source, *, status: str = "AUTHORIZED"):
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
            authority_policy_version="phase17-transition-test",
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
        source_snapshot_id=None,
        frame_ids=(),
        semantic_input_digests=(f"sem-{key}",),
        evidence_time=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, day, 12, 1, tzinfo=timezone.utc),
        world_time=None,
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=refs,
    )


def _world(synopsis: str, status: str, refs: tuple[str, ...], day: int):
    return WorldStateV02(
        synopsis=synopsis,
        status=status,
        effective_at=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        active_semantic_unit_refs=refs,
    )


def _proposal(kind: str, world: WorldStateV02):
    return StateTransitionProposalV01(
        transition_kind=kind,
        world_state=world,
        rationale=f"controlled {kind}",
    )


def test_initialize_then_corroboration_changes_evidence_not_world_state(db):
    event = _event(db)
    a = _source(db, "initial Jev report")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    obs_a = _obs(event, a, "a", ("uA",), 16)

    initialized = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=obs_a,
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev has been publicly introduced.", "early emergence", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    )
    assert initialized.next_state.evidence_state.member_source_count == 1

    b = _source(db, "independent Jev report")
    _member(db, event, b)
    obs_b = _obs(event, b, "b", ("uB",), 17)

    corroborated = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initialized.next_state,
        observation=obs_b,
        proposal=_proposal(
            "NO_MATERIAL_CHANGE",
            initialized.next_state.world_state,
        ),
        supporting_source_ids=[a.id, b.id],
    )

    assert corroborated.next_state.world_state == initialized.next_state.world_state
    assert corroborated.next_state.evidence_state.member_source_count == 2
    assert corroborated.next_state.evidence_state.independent_source_count == 2
    assert corroborated.next_state.state_digest != initialized.next_state.state_digest


def test_enrichment_keeps_previous_active_refs_and_adds_new_ref(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    initial = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uA",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev launched.", "early emergence", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "author presentation")
    _member(db, event, b)
    enriched = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initial,
        observation=_obs(event, b, "b", ("uB",), 18),
        proposal=_proposal(
            "ENRICH",
            _world(
                "Jev launched and now has a first-party mechanism explanation.",
                "early emergence",
                ("uA", "uB"),
                18,
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert enriched.world_state.active_semantic_unit_refs == ("uA", "uB")


def test_correction_replaces_current_ref_but_preserves_history_outside_state(db):
    event = _event(db)
    a = _source(db, "initial benchmark claim")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    initial = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uOld",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Reported gain is 20%.", "reported", ("uOld",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "author correction")
    _member(db, event, b)
    corrected = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initial,
        observation=_obs(event, b, "b", ("uCorrected",), 18),
        proposal=_proposal(
            "REPLACE_CURRENT",
            _world("Corrected reported gain is 7%.", "corrected", ("uCorrected",), 18),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert corrected.world_state.active_semantic_unit_refs == ("uCorrected",)
    assert "uOld" not in corrected.world_state.active_semantic_unit_refs


def test_unresolved_contradiction_keeps_both_supported_sides_active(db):
    event = _event(db)
    a = _source(db, "positive reproduction")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    initial = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uPositive",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Independent reproduction reports a strong result.", "reported", ("uPositive",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "failed reproduction")
    _member(db, event, b)
    contested = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initial,
        observation=_obs(event, b, "b", ("uNegative",), 18),
        proposal=_proposal(
            "CONTEST",
            _world(
                "Independent reproductions currently conflict.",
                "contested",
                ("uPositive", "uNegative"),
                18,
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert contested.world_state.status == "contested"
    assert contested.world_state.active_semantic_unit_refs == ("uNegative", "uPositive")


def test_reducer_rejects_unsupported_or_semantically_invalid_transition(db):
    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    obs = _obs(event, a, "a", ("uA",), 16)

    with pytest.raises(ValueError, match="unsupported semantic refs"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=None,
            observation=obs,
            proposal=_proposal(
                "INITIALIZE",
                _world("Invented unsupported state.", "bad", ("uInvented",), 16),
            ),
            supporting_source_ids=[a.id],
        )

    initial = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=obs,
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev launched.", "early emergence", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "new source")
    _member(db, event, b)
    with pytest.raises(ValueError, match="NO_MATERIAL_CHANGE"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=initial,
            observation=_obs(event, b, "b", ("uB",), 17),
            proposal=_proposal(
                "NO_MATERIAL_CHANGE",
                _world("Sneaky changed synopsis.", "early emergence", ("uA",), 17),
            ),
            supporting_source_ids=[a.id, b.id],
        )


def test_replay_prefix_has_no_future_source_leakage_and_is_digest_deterministic(db):
    event = _event(db)
    a = _source(db, "t0")
    b = _source(db, "t1")
    c = _source(db, "t2")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    _member(db, event, b)
    _member(db, event, c)

    obs_a = _obs(event, a, "a", ("uA",), 16)
    obs_b = _obs(event, b, "b", ("uB",), 17)
    obs_c = _obs(event, c, "c", ("uC",), 18)

    proposals = [
        _proposal(
            "INITIALIZE",
            _world("Jev launched.", "early emergence", ("uA",), 16),
        ),
        _proposal(
            "ENRICH",
            _world(
                "Jev has broader independent discussion.",
                "early emergence",
                ("uA", "uB"),
                17,
            ),
        ),
        _proposal(
            "REPLACE_CURRENT",
            _world(
                "Jev now has stronger independent validation.",
                "early validation",
                ("uB", "uC"),
                18,
            ),
        ),
    ]
    observations = [obs_a, obs_b, obs_c]
    prefixes = [[a.id], [a.id, b.id], [a.id, b.id, c.id]]

    def run_once():
        state = None
        states = []
        for observation, proposal, source_ids in zip(observations, proposals, prefixes):
            state = reduce_state_transition(
                db,
                event_id=event.id,
                previous=state,
                observation=observation,
                proposal=proposal,
                supporting_source_ids=source_ids,
            ).next_state
            states.append(state)
        return states

    first = run_once()
    second = run_once()

    assert [row.evidence_state.member_source_count for row in first] == [1, 2, 3]
    assert [row.state_digest for row in first] == [row.state_digest for row in second]


def test_phi_output_is_schema_valid_but_reducer_remains_support_authority(db):
    from app.services.event_state_transition import estimate_state_transition

    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    obs = _obs(event, a, "a", ("uA",), 16)

    def fake_chat(messages, **_kwargs):
        assert "Semantic State Delta Estimator" in messages[0]["content"]
        return (
            {
                "contract": "event-state-transition-estimator-v0.1",
                "transition_kind": "INITIALIZE",
                "world_state": {
                    "synopsis": "Unsupported invented claim.",
                    "status": "invented",
                    "effective_at": "2026-09-16T12:00:00Z",
                    "active_semantic_unit_refs": ["uInvented"],
                },
                "rationale": "controlled invalid model proposal",
            },
            {"model": "fake"},
        )

    proposal = estimate_state_transition(
        previous=None,
        observation=obs,
        new_semantic_units=[
            {"unit_id": "uA", "statement": "Jev launched."},
        ],
        chat_fn=fake_chat,
    )
    assert proposal.world_state.active_semantic_unit_refs == ("uInvented",)

    with pytest.raises(ValueError, match="unsupported semantic refs"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=None,
            observation=obs,
            proposal=proposal,
            supporting_source_ids=[a.id],
        )
