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
    normalized = {
        "contested": "CONTESTED",
        "resolved": "RESOLVED",
        "emerging": "EMERGING",
    }.get(status.lower(), "ACTIVE")
    return WorldStateV02(
        synopsis=synopsis,
        status=normalized,
        effective_at=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        active_semantic_unit_refs=refs,
    )


def _proposal(
    kind: str,
    world: WorldStateV02,
    *,
    supersession_pairs: tuple[dict, ...] = (),
):
    return StateTransitionProposalV01(
        transition_kind=kind,
        world_state=world,
        supersession_pairs=supersession_pairs,
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


def test_enrichment_may_compact_redundant_prior_support_refs(db):
    event = _event(db)
    a = _source(db, "early launch claim")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    initial = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uEarly",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev is reported as newly launched.", "early emergence", ("uEarly",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "stronger current launch description")
    _member(db, event, b)
    compacted = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initial,
        observation=_obs(event, b, "b", ("uCurrent",), 17),
        proposal=_proposal(
            "ENRICH",
            _world(
                "Jev is publicly launched and accumulating early validation.",
                "early validation",
                ("uCurrent",),
                17,
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert compacted.world_state.active_semantic_unit_refs == ("uCurrent",)
    assert "uEarly" not in compacted.world_state.active_semantic_unit_refs
    assert compacted.evidence_state.member_source_count == 2


def test_phi_contract_rejects_unbounded_synopsis():
    from pydantic import ValidationError
    from app.services.event_state_transition import StateTransitionProposalV02

    with pytest.raises(ValidationError, match="synopsis"):
        StateTransitionProposalV02(
            transition_kind="INITIALIZE",
            world_state=WorldStateV02(
                synopsis="x" * 2001,
                status="ACTIVE",
                effective_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
                active_semantic_unit_refs=("uA",),
            ),
            rationale="controlled compactness boundary",
        )


def test_key_point_composition_has_programmatic_synopsis_bound():
    from app.services.event_state_transition import (
        PHI_SYNOPSIS_MAX_CHARS,
        _compose_bounded_synopsis,
    )

    points = tuple(
        ("This is a deliberately overlong decision-relevant point " * 30) + str(i)
        for i in range(4)
    )
    synopsis = _compose_bounded_synopsis(points)

    assert 0 < len(synopsis) <= PHI_SYNOPSIS_MAX_CHARS


def test_phi_contract_rejects_noncanonical_phase_status():
    from pydantic import ValidationError
    from app.services.event_state_transition import StateTransitionProposalV02

    with pytest.raises(ValidationError, match="status"):
        StateTransitionProposalV02(
            transition_kind="INITIALIZE",
            world_state=WorldStateV02(
                synopsis="Jev is publicly introduced.",
                status="latest demo and validation headline",
                effective_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
                active_semantic_unit_refs=("uA",),
            ),
            rationale="controlled status compactness boundary",
        )


def test_reducer_rejects_enrich_phase_regression(db):
    from app.services.event_state_transition import StateTransitionProposalV02

    event = _event(db)
    a = _source(db, "active event")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    previous = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uA",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("The event is established.", "active", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "new detail")
    _member(db, event, b)
    proposal = StateTransitionProposalV02(
        transition_kind="ENRICH",
        world_state=WorldStateV02(
            synopsis="The established event has a new detail.",
            status="EMERGING",
            effective_at=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
            active_semantic_unit_refs=("uB",),
        ),
        rationale="illegal phase regression",
    )
    with pytest.raises(ValueError, match="Illegal Event phase transition"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=previous,
            observation=_obs(event, b, "b", ("uB",), 17),
            proposal=proposal,
            supporting_source_ids=[a.id, b.id],
        )


def test_contest_requires_contested_phase(db):
    from app.services.event_state_transition import StateTransitionProposalV02

    event = _event(db)
    a = _source(db, "old assertion")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    previous = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uA",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Claim A is current.", "active", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "conflicting assertion")
    _member(db, event, b)
    bad = StateTransitionProposalV02(
        transition_kind="CONTEST",
        world_state=WorldStateV02(
            synopsis="Claim A and claim B remain incompatible.",
            status="ACTIVE",
            effective_at=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
            active_semantic_unit_refs=("uA", "uB"),
        ),
        rationale="controlled invalid contest phase",
    )
    with pytest.raises(ValueError, match="status=CONTESTED"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=previous,
            observation=_obs(event, b, "b", ("uB",), 17),
            proposal=bad,
            supporting_source_ids=[a.id, b.id],
        )


def test_replace_current_contract_requires_explicit_supersession_pair():
    from pydantic import ValidationError
    from app.services.event_state_transition import StateTransitionProposalV02

    with pytest.raises(ValidationError, match="supersession pair"):
        StateTransitionProposalV02(
            transition_kind="REPLACE_CURRENT",
            world_state=_world(
                "New topic replaces the old focus without correcting it.",
                "reported",
                ("uNew",),
                18,
            ),
            rationale="topic shift is not a correction",
        )


def test_topic_shift_is_legal_as_enrich_with_support_compaction(db):
    event = _event(db)
    a = _source(db, "FSD demo")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    previous = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uFSD",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev is demonstrated in an FSD use case.", "early validation", ("uFSD",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "trading bot demo")
    _member(db, event, b)
    shifted = reduce_state_transition(
        db,
        event_id=event.id,
        previous=previous,
        observation=_obs(event, b, "b", ("uTrading",), 17),
        proposal=_proposal(
            "ENRICH",
            _world(
                "Jev is now also demonstrated in an automated trading use case.",
                "early validation",
                ("uTrading",),
                17,
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert shifted.world_state.active_semantic_unit_refs == ("uTrading",)
    assert shifted.evidence_state.member_source_count == 2


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
            supersession_pairs=(
                {
                    "previous_ref": "uOld",
                    "new_ref": "uCorrected",
                    "reason": "The author explicitly corrects 20% to 7%.",
                },
            ),
        ),
        supporting_source_ids=[a.id, b.id],
    ).next_state

    assert corrected.world_state.active_semantic_unit_refs == ("uCorrected",)
    assert "uOld" not in corrected.world_state.active_semantic_unit_refs


def test_reducer_rejects_supersession_pair_not_bound_to_previous_and_new_refs(db):
    event = _event(db)
    a = _source(db, "old claim")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    previous = reduce_state_transition(
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

    b = _source(db, "correction")
    _member(db, event, b)
    bad = _proposal(
        "REPLACE_CURRENT",
        _world("Corrected gain is 7%.", "corrected", ("uCorrected",), 18),
        supersession_pairs=(
            {
                "previous_ref": "uNotPreviouslyActive",
                "new_ref": "uCorrected",
                "reason": "invalid old support",
            },
        ),
    )
    with pytest.raises(ValueError, match="previous_ref"):
        reduce_state_transition(
            db,
            event_id=event.id,
            previous=previous,
            observation=_obs(event, b, "b", ("uCorrected",), 18),
            proposal=bad,
            supporting_source_ids=[a.id, b.id],
        )


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

    assert contested.world_state.status == "CONTESTED"
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
            "ENRICH",
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


def test_phi_requires_exact_hydration_for_previous_active_refs(db):
    from app.services.event_state_transition import estimate_state_transition

    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    previous = reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=_obs(event, a, "a", ("uA",), 16),
        proposal=_proposal(
            "INITIALIZE",
            _world("Jev launched.", "emerging", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "new evidence")
    _member(db, event, b)

    def should_not_call(*_args, **_kwargs):
        raise AssertionError("LLM must not be called with incomplete previous support hydration")

    with pytest.raises(ValueError, match="previous active support hydration"):
        estimate_state_transition(
            previous=previous,
            observation=_obs(event, b, "b", ("uB",), 17),
            previous_active_semantic_units=[],
            new_semantic_units=[
                {"unit_id": "uB", "statement": "New Jev evidence."},
            ],
            chat_fn=should_not_call,
        )


def test_enrich_without_new_support_normalizes_to_no_material_change(db):
    from app.services.event_state_transition import estimate_state_transition

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
            _world("Jev launched.", "announced", ("uA",), 16),
        ),
        supporting_source_ids=[a.id],
    ).next_state

    b = _source(db, "technical explanation")
    _member(db, event, b)
    obs_b = _obs(event, b, "b", ("uB",), 17)
    calls = {"count": 0}

    def fake_chat(_messages, **_kwargs):
        calls["count"] += 1
        return (
            {
                "contract": "event-state-transition-estimator-v1.5",
                "transition_kind": "ENRICH",
                "key_points": [
                    {
                        "text": "Jev launched and now has a technical explanation.",
                        "support_keys": ["P001"],
                    }
                ],
                "status": "ACTIVE",
                "effective_at": "2026-09-17T12:00:00Z",
                "rationale": "controlled missing-new-ref support error",
            },
            {"model": "fake"},
        )

    proposal = estimate_state_transition(
        previous=initial,
        observation=obs_b,
        previous_active_semantic_units=[
            {"unit_id": "uA", "statement": "Jev launched."},
        ],
        new_semantic_units=[
            {"unit_id": "uB", "statement": "Authors published technical details."},
        ],
        chat_fn=fake_chat,
    )
    assert calls["count"] == 1
    assert proposal.transition_kind == "NO_MATERIAL_CHANGE"
    assert proposal.world_state == initial.world_state

    reduced = reduce_state_transition(
        db,
        event_id=event.id,
        previous=initial,
        observation=obs_b,
        proposal=proposal,
        supporting_source_ids=[a.id, b.id],
    )
    assert reduced.next_state.world_state == initial.world_state


def test_phi_rejects_unknown_support_key(db):
    from app.services.event_state_transition import estimate_state_transition

    event = _event(db)
    a = _source(db, "launch")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    obs = _obs(event, a, "a", ("uA",), 16)
    calls = {"count": 0}

    def fake_chat(_messages, **_kwargs):
        calls["count"] += 1
        return (
            {
                "contract": "event-state-transition-estimator-v1.5",
                "transition_kind": "INITIALIZE",
                "key_points": [
                    {
                        "text": "Jev launched.",
                        "support_keys": ["X999"],
                    }
                ],
                "status": "ACTIVE",
                "effective_at": "2026-09-16T12:00:00Z",
                "rationale": "controlled unknown support-key error",
            },
            {"model": "fake"},
        )

    with pytest.raises(ValueError, match="unknown support key"):
        estimate_state_transition(
            previous=None,
            observation=obs,
            previous_active_semantic_units=[],
            new_semantic_units=[
                {"unit_id": "uA", "statement": "Jev launched."},
            ],
            chat_fn=fake_chat,
        )
    assert calls["count"] == 1
