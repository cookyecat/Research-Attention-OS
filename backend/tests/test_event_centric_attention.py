from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models.event import Event, EventMembershipAssertion, EventSource
from app.models.scheduler import AttentionPlan
from app.services.event_membership import (
    SOURCE_LOCAL_AUTHORITY_STATUS,
    decision_event_for_source,
)
from app.services.event_processor import EVENT_MEMBERSHIP_POLICY
from app.services.ingestion import ingest_text
from app.services.pipeline import run_pipeline
from app.services.scheduler import RuntimeView
from app.testing.kernel_fixture import seed_mvp_kernel


def _assert_event_plan(db, source_id: UUID, result: dict) -> Event:
    plan = result["attention_plan"]
    assert plan is not None
    assert plan["candidate_type"] == "EVENT"

    event_id = UUID(plan["candidate_id"])
    event = db.get(Event, event_id)
    assert event is not None

    resolved = decision_event_for_source(db, source_id)
    assert resolved is not None
    assert resolved.id == event_id

    assertions = (
        db.execute(
            select(EventMembershipAssertion).where(
                EventMembershipAssertion.source_id == source_id,
                EventMembershipAssertion.event_id == event_id,
            )
        )
        .scalars()
        .all()
    )
    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion.action == "ASSERT"
    assert assertion.membership == "REPORTS_EVENT"
    assert assertion.authority_policy_version == EVENT_MEMBERSHIP_POLICY
    assert assertion.authority_status == SOURCE_LOCAL_AUTHORITY_STATUS
    assert assertion.contextual_role_fields["cross_source_commitment"] is False

    assert db.get(EventSource, (event_id, source_id)) is not None
    return event


def test_new_canonical_analysis_creates_event_attention_candidate(db):
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A technical report about embodied intelligence latency.",
        title="Event attention source",
    )

    result = run_pipeline(db, source.id, reprocess=True)

    event = _assert_event_plan(db, source.id, result)
    assert event.status == "CANDIDATE"
    assert result["attention_plan"]["score_debug"]["decision_candidate"]["candidate_type"] == "EVENT"


def test_identical_titles_do_not_create_cross_source_event_membership(db):
    seed_mvp_kernel(db)
    a = ingest_text(db, "First independent occurrence.", title="Same headline")
    b = ingest_text(db, "Second independent occurrence.", title="Same headline")

    ra = run_pipeline(db, a.id, reprocess=True)
    rb = run_pipeline(db, b.id, reprocess=True)

    ea = _assert_event_plan(db, a.id, ra)
    eb = _assert_event_plan(db, b.id, rb)
    assert ea.id != eb.id

    assert db.get(EventSource, (ea.id, b.id)) is None
    assert db.get(EventSource, (eb.id, a.id)) is None


def test_safe_legacy_single_member_event_is_backfilled_not_duplicated(db):
    seed_mvp_kernel(db)
    source = ingest_text(db, "Legacy single member evidence.", title="Legacy single")
    legacy = Event(
        title="Legacy event",
        event_type="PUBLICATION",
        summary="Historical single-member working topology.",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(legacy)
    db.flush()
    db.add(
        EventSource(
            event_id=legacy.id,
            source_id=source.id,
            relationship="REPORTS",
            confidence=0.7,
        )
    )
    db.flush()

    result = run_pipeline(db, source.id, reprocess=True)

    event = _assert_event_plan(db, source.id, result)
    assert event.id == legacy.id
    assert db.query(Event).count() == 1


def test_legacy_multi_member_event_is_not_silently_decision_authorized(db):
    seed_mvp_kernel(db)
    a = ingest_text(db, "Legacy member A.", title="Legacy shared")
    b = ingest_text(db, "Legacy member B.", title="Legacy shared")
    legacy = Event(
        title="Legacy shared event",
        event_type="PUBLICATION",
        summary="Unsafe historical multi-member working topology.",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(legacy)
    db.flush()
    db.add_all(
        [
            EventSource(event_id=legacy.id, source_id=a.id, relationship="REPORTS", confidence=0.7),
            EventSource(event_id=legacy.id, source_id=b.id, relationship="REPORTS", confidence=0.7),
        ]
    )
    db.flush()

    result = run_pipeline(db, a.id, reprocess=True)

    event = _assert_event_plan(db, a.id, result)
    assert event.id != legacy.id
    # Historical working topology is preserved but is not the decision candidate.
    assert db.get(EventSource, (legacy.id, a.id)) is not None
    assert db.get(EventSource, (legacy.id, b.id)) is not None


def test_runtime_reschedule_preserves_event_candidate_identity(db):
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A source whose runtime schedule changes without changing the world event.",
        title="Runtime reschedule event",
    )
    first = run_pipeline(db, source.id, reprocess=True)
    event_id = first["attention_plan"]["candidate_id"]

    second = run_pipeline(
        db,
        source.id,
        runtime=RuntimeView(
            current_task="focused work",
            interruptibility="LOW",
            cognitive_capacity="NORMAL",
        ),
    )

    assert second["attention_plan"]["candidate_type"] == "EVENT"
    assert second["attention_plan"]["candidate_id"] == event_id

    plans = (
        db.execute(
            select(AttentionPlan)
            .where(AttentionPlan.analysis_run_id == UUID(first["analysis_run"]["id"]))
            .order_by(AttentionPlan.created_at)
        )
        .scalars()
        .all()
    )
    assert len(plans) >= 2
    assert all(str(plan.candidate_type) == "EVENT" for plan in plans)
    assert {plan.candidate_id for plan in plans} == {UUID(event_id)}



def test_http_current_attention_exposes_event_and_representative_source(client):
    source = client.post(
        "/sources",
        json={
            "source_type": "TEXT",
            "title": "Event-centric API probe",
            "content_text": "A technical report about motor intelligence latency and energy tradeoffs.",
        },
    ).json()
    analyzed = client.post(
        "/analysis/extract",
        json={"source_id": source["id"], "extra_source_ids": []},
    )
    assert analyzed.status_code == 200, analyzed.text
    plan = analyzed.json()["attention_plan"]
    assert plan["candidate_type"] == "EVENT"

    rows = client.get("/kernel/attention").json()
    event_row = next(row for row in rows if row["id"] == plan["id"])
    assert event_row["candidate_type"] == "EVENT"
    assert event_row["candidate_id"] == plan["candidate_id"]
    assert event_row["representative_source_id"] == source["id"]
    assert event_row["event"]["id"] == plan["candidate_id"]
    assert event_row["event"]["title"]

    compact_rows = client.get("/kernel/attention?compact=true").json()
    compact_event = next(
        row for row in compact_rows
        if row["id"] == plan["id"]
    )
    assert compact_event["candidate_type"] == "EVENT"
    assert compact_event["representative_source_id"] == source["id"]
    assert source["id"] in compact_event["source_ids"]

    agent = client.get("/agent/v1/attention").json()
    agent_row = next(row for row in agent["items"] if row["id"] == plan["id"])
    assert agent_row["candidate_type"] == "EVENT"
    assert agent_row["representative_source_id"] == source["id"]
    assert agent_row["event"]["id"] == plan["candidate_id"]



def test_current_projection_suppresses_historical_source_plan_when_event_plan_exists(db):
    from datetime import datetime, timedelta, timezone

    from app.models.scheduler import AttentionPlan
    from app.services.current_attention import current_attention_plans

    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A source with historical Source-centric Attention history.",
        title="Current projection event",
    )
    result = run_pipeline(db, source.id, reprocess=True)
    event_plan_id = UUID(result["attention_plan"]["id"])
    event_id = UUID(result["attention_plan"]["candidate_id"])
    event_plan = db.get(AttentionPlan, event_plan_id)
    assert event_plan is not None

    historical = AttentionPlan(
        candidate_type="SOURCE",
        candidate_id=source.id,
        disposition=event_plan.disposition,
        processing_modes=list(event_plan.processing_modes or []),
        urgency=event_plan.urgency,
        cognitive_budget_minutes=event_plan.cognitive_budget_minutes,
        kernel_target_ids=list(event_plan.kernel_target_ids or []),
        expected_output=event_plan.expected_output,
        reason="historical source-centric identity",
        watch_after_processing=event_plan.watch_after_processing,
        scheduler_version=event_plan.scheduler_version,
        attention_policy_version=event_plan.attention_policy_version,
        runtime_context_id=event_plan.runtime_context_id,
        runtime_snapshot=event_plan.runtime_snapshot,
        score_debug=dict(event_plan.score_debug or {}),
        analysis_run_id=event_plan.analysis_run_id,
        created_at=(event_plan.created_at or datetime.now(timezone.utc)) + timedelta(minutes=1),
    )
    db.add(historical)
    db.flush()

    current = current_attention_plans(db)
    assert any(
        str(plan.candidate_type) == "EVENT" and plan.candidate_id == event_id
        for plan in current
    )
    assert not any(
        str(plan.candidate_type) == "SOURCE" and plan.candidate_id == source.id
        for plan in current
    )
