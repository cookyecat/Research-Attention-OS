from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.enums import Disposition, SourceEdgeRelationship
from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source, SourceEdge
from app.services.event_state import (
    EvidenceObservationV01,
    EventStateDeltaV01,
    HysteresisThresholdsV01,
    leaky_accumulate,
    make_event_state,
    reduce_event_state,
    structural_evidence_state,
    world_state_from_event,
    hysteretic_attention_transition,
)


def _source(db, title: str) -> Source:
    row = Source(
        source_type="TEXT",
        title=title,
        content_text=title,
        fingerprint=f"phase17-state-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    return row


def _event(db) -> Event:
    row = Event(
        title="Jev emergence",
        event_type="MODEL_LAUNCH",
        actors=["Jev team"],
        action="launch and early validation",
        object="Jev",
        time_context="multi-day episode",
        summary="Jev launch and early validation episode.",
        current_state="launched",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(row)
    db.flush()
    return row


def _member(db, event: Event, source: Source, status: str):
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
            authority_policy_version="phase17-test",
            authority_epoch=1,
            authority_status=status,
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _thresholds() -> HysteresisThresholdsV01:
    return HysteresisThresholdsV01(
        exit_aware=0.10,
        enter_aware=0.20,
        exit_watch=0.35,
        enter_watch=0.50,
        exit_engage=0.65,
        enter_engage=0.80,
    )


def test_structural_evidence_state_respects_provenance_dependence(db):
    event = _event(db)
    original = _source(db, "original")
    repost = _source(db, "repost")
    _member(db, event, original, "AUTHORIZED_SOURCE_LOCAL")
    _member(db, event, repost, "AUTHORIZED")
    db.add(
        SourceEdge(
            source_id=repost.id,
            target_id=original.id,
            relationship=SourceEdgeRelationship.REPOSTS,
            confidence=1.0,
            detected_by="AI",
            evidence="controlled repost",
        )
    )
    db.flush()

    state = structural_evidence_state(db, event.id)

    assert state.member_source_count == 2
    assert state.independent_source_count == 1
    assert state.secondary_report_count == 1


def test_recursive_filter_is_immediately_idempotent_for_same_evidence_key(db):
    event = _event(db)
    now = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    world = world_state_from_event(event)
    delta = EventStateDeltaV01(
        world_state=world,
        evidence_observation=EvidenceObservationV01(
            evidence_key="source-A",
            observed_at=now,
            member_source_count=1,
            independent_source_count=1,
            secondary_report_count=0,
            relational_digest="r1",
            innovation=1.0,
        ),
    )

    first = reduce_event_state(
        None,
        delta,
        event_id=event.id,
        retention_per_hour=0.9,
    )
    replay = reduce_event_state(
        first,
        delta,
        event_id=event.id,
        retention_per_hour=0.9,
    )

    assert replay.state_digest == first.state_digest
    assert replay.evidence_state.arrival_momentum == first.evidence_state.arrival_momentum


def test_recursive_filter_updates_current_state_without_full_history_bag(db):
    event = _event(db)
    t0 = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
    first_world = world_state_from_event(event)
    first = reduce_event_state(
        None,
        EventStateDeltaV01(
            world_state=first_world,
            evidence_observation=EvidenceObservationV01(
                evidence_key="A",
                observed_at=t0,
                member_source_count=1,
                independent_source_count=1,
                secondary_report_count=0,
                relational_digest="r1",
                innovation=1.0,
            ),
        ),
        event_id=event.id,
        retention_per_hour=0.5,
    )

    event.current_state = "independently validated"
    event.summary = "Jev now has independent workflow validation."
    second_world = world_state_from_event(event)
    second = reduce_event_state(
        first,
        EventStateDeltaV01(
            world_state=second_world,
            evidence_observation=EvidenceObservationV01(
                evidence_key="B",
                observed_at=t0 + timedelta(hours=1),
                member_source_count=2,
                independent_source_count=2,
                secondary_report_count=0,
                relational_digest="r2",
                innovation=1.0,
            ),
        ),
        event_id=event.id,
        retention_per_hour=0.5,
    )

    assert second.world_state.current_state == "independently validated"
    assert "independent workflow validation" in second.world_state.summary
    assert second.evidence_state.member_source_count == 2
    assert second.evidence_state.arrival_momentum == pytest.approx(1.5)
    assert second.state_digest != first.state_digest


def test_leaky_accumulator_decays_old_momentum():
    assert leaky_accumulate(
        8.0,
        0.0,
        elapsed_hours=3.0,
        retention_per_hour=0.5,
    ) == pytest.approx(1.0)

    assert leaky_accumulate(
        8.0,
        2.0,
        elapsed_hours=3.0,
        retention_per_hour=0.5,
    ) == pytest.approx(3.0)


def test_hysteresis_prevents_boundary_chatter():
    thresholds = _thresholds()

    # Same signal, different history: memory is the point.
    assert (
        hysteretic_attention_transition(Disposition.AWARE, 0.45, thresholds)
        == Disposition.AWARE
    )
    assert (
        hysteretic_attention_transition(Disposition.WATCH, 0.45, thresholds)
        == Disposition.WATCH
    )

    # Small fluctuations within the WATCH band do not chatter.
    state = Disposition.WATCH
    for signal in (0.49, 0.46, 0.40, 0.48, 0.44):
        state = hysteretic_attention_transition(state, signal, thresholds)
        assert state == Disposition.WATCH


def test_hysteresis_allows_real_up_and_down_transitions():
    thresholds = _thresholds()

    assert (
        hysteretic_attention_transition(Disposition.AWARE, 0.55, thresholds)
        == Disposition.WATCH
    )
    assert (
        hysteretic_attention_transition(Disposition.WATCH, 0.85, thresholds)
        == Disposition.ENGAGE
    )
    assert (
        hysteretic_attention_transition(Disposition.ENGAGE, 0.70, thresholds)
        == Disposition.ENGAGE
    )
    assert (
        hysteretic_attention_transition(Disposition.ENGAGE, 0.60, thresholds)
        == Disposition.WATCH
    )
    assert (
        hysteretic_attention_transition(Disposition.WATCH, 0.30, thresholds)
        == Disposition.AWARE
    )
