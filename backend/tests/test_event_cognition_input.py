from __future__ import annotations

from uuid import uuid4

import pytest

from app.enums import SourceEdgeRelationship
from app.models.event import Event, EventEvidenceFrame, EventMembershipAssertion, EventSource
from app.models.source import Source, SourceEdge
from app.cognitive.research_aligned_contract import canonical_semantic_units
from app.services.event_cognition_input import (
    EVENT_COGNITION_INPUT_CONTRACT,
    EventCognitionInputError,
    build_event_cognition_input,
)


def _source(db, title: str) -> Source:
    source = Source(
        source_type="TEXT",
        title=title,
        content_text=title,
        fingerprint=f"phase17-{uuid4()}",
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(source)
    db.flush()
    return source


def _event(db, title: str = "Profiler result") -> Event:
    event = Event(
        title=title,
        event_type="RESEARCH_RESULT",
        actors=["Acme Research"],
        action="report profiler result",
        object="64x64 bf16 matmul",
        summary=title,
        current_state="reported",
        confidence=0.8,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    return event


def _member(db, event: Event, source: Source, *, status: str = "AUTHORIZED"):
    db.add(
        EventSource(
            event_id=event.id,
            source_id=source.id,
            relationship="REPORTS",
            confidence=0.9,
        )
    )
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source.id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={"phase17_test": True},
            audit_run_id=None,
            authority_policy_version="phase17-test",
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
    statement: str,
    unit_id: str | None = None,
    suffix: str | None = None,
    audited: bool = True,
) -> EventEvidenceFrame:
    suffix = suffix or str(uuid4())
    unit_id = unit_id or f"{source.id}:unit:{suffix}"
    payload = {
        "event_key": "phase17-event",
        "event_summary": statement,
        "rendered_event_text": statement,
    }
    if audited:
        payload["audited_semantic_units"] = [
            {
                "unit_id": unit_id,
                "statement": statement,
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
                "supports": [
                    {
                        "source_id": str(source.id),
                        "support_pointer": f"PARA {suffix}",
                        "support_excerpt": statement,
                    }
                ],
            }
        ]
    frame = EventEvidenceFrame(
        identity_key=f"phase17-frame-{uuid4()}",
        workspace_id="local-default",
        source_id=source.id,
        source_snapshot_id=None,
        analysis_run_id=None,
        frame_contract_version="event-evidence-frame-v0.3",
        semantic_input_digest=f"semantic-{suffix}",
        frame_payload=payload,
        frame_digest=f"frame-{suffix}",
    )
    db.add(frame)
    db.flush()
    return frame


def test_event_cognition_aggregates_authorized_member_evidence_without_text_dedup(db):
    event = _event(db)
    a = _source(db, "Publisher A")
    b = _source(db, "Publisher B")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    _member(db, event, b)
    statement = (
        "Profiler evidence shows kernel launch overhead dominates runtime for a small "
        "64x64 bf16 matrix multiplication with bias."
    )
    _frame(db, a, statement=statement, suffix="A")
    _frame(db, b, statement=statement, suffix="B")

    result = build_event_cognition_input(db, event.id)
    units = canonical_semantic_units(result.extraction)

    assert result.as_dict()["contract"] == EVENT_COGNITION_INPUT_CONTRACT
    assert len(result.member_source_ids) == 2
    assert len(units) == 2
    assert units[0]["unit_id"] != units[1]["unit_id"]
    assert {row["supports"][0]["source_id"] for row in units} == {str(a.id), str(b.id)}
    assert result.relational_context.independent_sources == 2
    assert result.relational_context.secondary_reports == 0


def test_event_cognition_same_event_does_not_override_repost_dependence(db):
    event = _event(db)
    a = _source(db, "Original")
    b = _source(db, "Repost")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    _member(db, event, b)
    statement = "The profiler result was reported."
    _frame(db, a, statement=statement, suffix="A")
    _frame(db, b, statement=statement, suffix="B")
    db.add(
        SourceEdge(
            source_id=b.id,
            target_id=a.id,
            relationship=SourceEdgeRelationship.REPOSTS,
            confidence=1.0,
            detected_by="AI",
            evidence="controlled provenance dependence",
        )
    )
    db.flush()

    result = build_event_cognition_input(db, event.id)

    assert len(result.member_source_ids) == 2
    assert result.relational_context.independent_sources == 1
    assert result.relational_context.secondary_reports == 1
    assert str(b.id) in result.relational_context.secondary_source_ids


def test_event_cognition_fails_closed_without_audited_units(db):
    event = _event(db)
    source = _source(db, "No audited units")
    _member(db, event, source, status="AUTHORIZED_SOURCE_LOCAL")
    _frame(db, source, statement="Summary only.", audited=False)

    with pytest.raises(EventCognitionInputError, match="unusable audited Event evidence"):
        build_event_cognition_input(db, event.id)


def test_event_cognition_rejects_conflicting_duplicate_unit_id(db):
    event = _event(db)
    a = _source(db, "Publisher A")
    b = _source(db, "Publisher B")
    _member(db, event, a, status="AUTHORIZED_SOURCE_LOCAL")
    _member(db, event, b)
    shared = "shared-unit"
    _frame(db, a, statement="Statement A.", unit_id=shared, suffix="A")
    _frame(db, b, statement="Statement B.", unit_id=shared, suffix="B")

    with pytest.raises(EventCognitionInputError, match="Conflicting duplicate semantic_unit_id"):
        build_event_cognition_input(db, event.id)


def test_event_cognition_digest_is_order_stable_and_event_state_sensitive(db, monkeypatch):
    import app.services.event_cognition_input as module

    event = _event(db)
    source = _source(db, "Publisher")
    _member(db, event, source, status="AUTHORIZED_SOURCE_LOCAL")
    _frame(db, source, statement="First evidence.", suffix="A")
    _frame(db, source, statement="Second evidence.", suffix="B")

    first = build_event_cognition_input(db, event.id)
    real = module.latest_event_evidence_frames_for_source

    def reversed_frames(session, source_id):
        return list(reversed(real(session, source_id)))

    monkeypatch.setattr(module, "latest_event_evidence_frames_for_source", reversed_frames)
    reordered = build_event_cognition_input(db, event.id)
    assert reordered.input_digest == first.input_digest
    assert [
        row["unit_id"] for row in canonical_semantic_units(reordered.extraction)
    ] == [
        row["unit_id"] for row in canonical_semantic_units(first.extraction)
    ]

    event.current_state = "corrected"
    db.flush()
    changed = build_event_cognition_input(db, event.id)
    assert changed.input_digest != first.input_digest
