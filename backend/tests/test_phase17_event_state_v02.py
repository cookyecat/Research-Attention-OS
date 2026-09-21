from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.acquisition import ExternalInformationItem, InformationSnapshot
from app.models.event import Event, EventEvidenceFrame, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import (
    EventObservationV01,
    materialize_event_observation,
    observation_key_for,
)
from app.services.event_state import (
    EvidenceStateV02,
    FilterStateV01,
    WorldStateV02,
    make_event_state_v02,
    structural_evidence_state_v02,
)


def _event(db) -> Event:
    row = Event(
        title="Jev emergence",
        event_type="MODEL_LAUNCH",
        actors=["Jev team"],
        action="launch and early validation",
        object="Jev",
        occurred_at=datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc),
        time_context="multi-day episode",
        location=None,
        summary="Jev launch and early validation episode.",
        current_state="early emergence",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(row)
    db.flush()
    return row


def _source(db, title: str, *, published_at: datetime | None = None) -> Source:
    row = Source(
        source_type="TEXT",
        title=title,
        content_text=title,
        published_at=published_at,
        fingerprint=f"phase17-v02-{uuid4()}",
        content_hash=f"content-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    return row


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
            authority_policy_version="phase17-v02-test",
            authority_epoch=1,
            authority_status=status,
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _frame(
    db,
    source: Source,
    *,
    unit_id: str,
    semantic_digest: str,
    source_snapshot_id=None,
) -> EventEvidenceFrame:
    row = EventEvidenceFrame(
        identity_key=f"phase17-v02-frame-{uuid4()}",
        workspace_id="local-default",
        source_id=source.id,
        source_snapshot_id=source_snapshot_id,
        analysis_run_id=None,
        frame_contract_version="event-evidence-frame-v0.3",
        semantic_input_digest=semantic_digest,
        frame_payload={
            "audited_semantic_units": [
                {
                    "unit_id": unit_id,
                    "statement": f"statement {unit_id}",
                    "supports": [{"source_id": str(source.id)}],
                }
            ]
        },
        frame_digest=f"frame-{uuid4()}",
    )
    db.add(row)
    db.flush()
    return row


def test_event_state_v02_is_minimal_and_identity_free():
    event_id = uuid4()
    world = WorldStateV02(
        synopsis="Jev is in early public emergence.",
        status="early emergence",
        effective_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        active_semantic_unit_refs=("u2", "u1", "u2"),
    )
    evidence = EvidenceStateV02(
        member_source_count=1,
        independent_source_count=1,
        secondary_report_count=0,
        relational_digest="rel",
        active_support_digest="support",
    )
    state = make_event_state_v02(
        event_id=event_id,
        world_state=world,
        evidence_state=evidence,
    )

    assert state.contract == "event-state-v0.2"
    assert state.world_state.active_semantic_unit_refs == ("u1", "u2")
    assert set(state.world_state.model_dump()) == {
        "synopsis",
        "status",
        "effective_at",
        "active_semantic_unit_refs",
    }
    serialized = state.model_dump(mode="json")
    for forbidden in (
        "actors",
        "action",
        "object",
        "time_context",
        "location",
        "event_type",
        "history_head_revision_id",
        "arrival_momentum",
        "last_evidence_key",
    ):
        assert forbidden not in str(serialized)


def test_filter_state_is_separate_from_event_state():
    filt = FilterStateV01(
        momentum=3.5,
        momentum_updated_at=datetime(2026, 9, 17, tzinfo=timezone.utc),
        last_applied_observation_key="obs",
    )
    assert filt.contract == "event-filter-state-v0.1"
    assert filt.momentum == 3.5


def test_structural_evidence_v02_uses_active_refs_in_support_digest(db):
    event = _event(db)
    source = _source(db, "Jev launch")
    _member(db, event, source)

    one = structural_evidence_state_v02(
        db,
        event.id,
        active_semantic_unit_refs=["u1"],
    )
    same = structural_evidence_state_v02(
        db,
        event.id,
        active_semantic_unit_refs=["u1", "u1"],
    )
    changed = structural_evidence_state_v02(
        db,
        event.id,
        active_semantic_unit_refs=["u2"],
    )

    assert one.member_source_count == 1
    assert one.independent_source_count == 1
    assert one.active_support_digest == same.active_support_digest
    assert changed.active_support_digest != one.active_support_digest


def test_observation_key_ignores_runtime_and_frame_row_identity(db):
    event = _event(db)
    source = _source(db, "Jev technical note")

    first = observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=None,
        semantic_input_digests=["d2", "d1", "d1"],
    )
    second = observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=None,
        semantic_input_digests=["d1", "d2"],
    )

    assert first == second


def test_materialized_observation_separates_world_evidence_and_ingest_time(db):
    event = _event(db)
    published = datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc)
    source = _source(db, "Jev author presentation", published_at=published)
    _member(db, event, source)
    _frame(db, source, unit_id="unit-B", semantic_digest="sem-B")

    observation = materialize_event_observation(db, event=event, source=source)

    assert isinstance(observation, EventObservationV01)
    assert observation.contract == "event-observation-v0.1"
    assert observation.evidence_time == published
    assert observation.ingest_time >= published
    assert observation.world_time == event.occurred_at
    assert observation.semantic_input_digests == ("sem-B",)
    assert observation.audited_semantic_unit_refs == ("unit-B",)
    assert observation.observation_key


def test_observation_key_changes_when_admitted_semantics_change(db):
    event = _event(db)
    source = _source(db, "Jev report")

    a = observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=None,
        semantic_input_digests=["semantic-A"],
    )
    b = observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=None,
        semantic_input_digests=["semantic-B"],
    )

    assert a != b


def test_materialized_observation_binds_content_identity_to_audited_frame_snapshot(db):
    event = _event(db)
    published = datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc)
    source = _source(db, "Jev versioned report", published_at=published)
    _member(db, event, source)

    item = ExternalInformationItem(
        identity_key=f"phase17-v02-item-{uuid4()}",
        item_type="ARTICLE",
        title="Jev versioned report",
        published_at=published,
    )
    db.add(item)
    db.flush()

    audited_at = datetime(2026, 9, 17, 4, 0, tzinfo=timezone.utc)
    newer_at = datetime(2026, 9, 18, 4, 0, tzinfo=timezone.utc)
    audited_snapshot = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=source.id,
        captured_at=audited_at,
        content_hash="snapshot-audited",
        snapshot_metadata={},
    )
    newer_snapshot = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=source.id,
        captured_at=newer_at,
        content_hash="snapshot-newer",
        snapshot_metadata={},
    )
    db.add_all([audited_snapshot, newer_snapshot])
    db.flush()

    _frame(
        db,
        source,
        unit_id="unit-audited",
        semantic_digest="sem-audited",
        source_snapshot_id=audited_snapshot.id,
    )

    observation = materialize_event_observation(db, event=event, source=source)

    assert observation.source_snapshot_id == audited_snapshot.id
    assert observation.ingest_time == audited_at
    assert observation.observation_key == observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=audited_snapshot,
        semantic_input_digests=["sem-audited"],
    )
    assert observation.observation_key != observation_key_for(
        event_id=event.id,
        source=source,
        snapshot=newer_snapshot,
        semantic_input_digests=["sem-audited"],
    )
