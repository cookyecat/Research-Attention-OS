from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.execution_integrity import execution_context
from app.models.analysis import AnalysisRun
from app.models.delivery import DeliveryEnvelope
from app.models.event import Event, EventMembershipAssertion, EventSource
from app.models.scheduler import AttentionPlan
from app.services.event_attention_migration import migrate_safe_source_attention_plans
from app.services.ingestion import ingest_text
from app.services.scheduler import get_decision_strategy


def _legacy_source_plan(db, source, *, event):
    authority = execution_context(
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
    )
    run = AnalysisRun(
        source_id=source.id,
        extra_source_ids=[],
        identity_key=f"phase16-legacy-{uuid4()}",
        extractor_version="legacy",
        matcher_version="legacy",
        evidence_reasoner_version="legacy",
        delta_version="legacy",
        scheduler_version="legacy",
        prompt_version="legacy",
        provider_version="legacy",
        embedding_model_version="none",
        pipeline_version="legacy",
        provider_type="rule",
        model_name=None,
        input_hash=f"input-{uuid4()}",
        kernel_snapshot_hash=f"kernel-{uuid4()}",
        status="COMPLETED",
        result_payload={"execution_authority": authority},
    )
    db.add(run)
    db.flush()
    plan = AttentionPlan(
        candidate_type="SOURCE",
        candidate_id=source.id,
        disposition="AWARE",
        processing_modes=[],
        urgency="NORMAL",
        cognitive_budget_minutes=None,
        kernel_target_ids=[],
        expected_output="NONE",
        reason="legacy source decision",
        watch_after_processing=False,
        scheduler_version="legacy",
        attention_policy_version="legacy",
        score_debug={},
        analysis_run_id=run.id,
    )
    db.add(plan)
    db.flush()
    return run, plan


def test_safe_identity_migration_is_idempotent_and_does_not_enqueue_delivery(db):
    source = ingest_text(db, "Legacy safe source.", title="Legacy safe")
    event = Event(
        title="Legacy safe event",
        event_type="PUBLICATION",
        summary="one-to-one legacy event",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    db.add(EventSource(event_id=event.id, source_id=source.id, relationship="REPORTS", confidence=0.7))
    db.flush()
    _run, source_plan = _legacy_source_plan(db, source, event=event)

    before_delivery = db.scalar(select(func.count()).select_from(DeliveryEnvelope))
    dry = migrate_safe_source_attention_plans(db, apply=False)
    assert dry["eligible_safe_single_member"] == 1
    assert dry["created_event_plans"] == 0
    assert db.scalar(select(func.count()).select_from(EventMembershipAssertion)) == 0

    applied = migrate_safe_source_attention_plans(db, apply=True)
    assert applied["created_event_plans"] == 1
    assert db.scalar(select(func.count()).select_from(DeliveryEnvelope)) == before_delivery

    event_plans = db.execute(
        select(AttentionPlan).where(
            AttentionPlan.candidate_type == "EVENT",
            AttentionPlan.candidate_id == event.id,
        )
    ).scalars().all()
    assert len(event_plans) == 1
    migrated = event_plans[0]
    assert migrated.analysis_run_id == source_plan.analysis_run_id
    assert migrated.disposition == source_plan.disposition
    assert migrated.score_debug["identity_migration"]["cognition_recomputed"] is False
    assert migrated.score_debug["identity_migration"]["delivery_reenqueued"] is False

    second = migrate_safe_source_attention_plans(db, apply=True)
    assert second["created_event_plans"] == 0
    assert second["already_event_migrated"] == 1


def test_multi_member_legacy_event_gets_separate_source_local_identity(db):
    a = ingest_text(db, "Legacy A.", title="Legacy shared")
    b = ingest_text(db, "Legacy B.", title="Legacy shared")
    event = Event(
        title="Legacy shared event",
        event_type="PUBLICATION",
        summary="unsafe multi-member legacy topology",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    db.add_all(
        [
            EventSource(event_id=event.id, source_id=a.id, relationship="REPORTS", confidence=0.7),
            EventSource(event_id=event.id, source_id=b.id, relationship="REPORTS", confidence=0.7),
        ]
    )
    db.flush()
    _legacy_source_plan(db, a, event=event)

    report = migrate_safe_source_attention_plans(db, apply=True)

    assert report["created_event_plans"] == 1
    assert report["needs_new_source_local_event"] == 1
    assert report["skipped_no_safe_event"] == 0

    assertions = db.execute(
        select(EventMembershipAssertion).where(EventMembershipAssertion.source_id == a.id)
    ).scalars().all()
    assert len(assertions) == 1
    local_event_id = assertions[0].event_id
    assert local_event_id != event.id

    event_plans = db.execute(
        select(AttentionPlan).where(
            AttentionPlan.candidate_type == "EVENT",
            AttentionPlan.candidate_id == local_event_id,
        )
    ).scalars().all()
    assert len(event_plans) == 1

    # Legacy shared topology is retained for audit, never treated as decision authority.
    assert db.get(EventSource, (event.id, a.id)) is not None
    assert db.get(EventSource, (event.id, b.id)) is not None
