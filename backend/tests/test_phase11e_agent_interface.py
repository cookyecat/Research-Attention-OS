from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.models.acquisition import SourceDefinition
from app.models.analysis import AnalysisRun
from app.models.delivery import DeliveryEnvelope
from app.models.scheduler import AttentionPlan
from app.models.watch import Watch
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.execution_integrity import execution_context
from app.services.scheduler import get_decision_strategy
from app.services.active_acquisition import ActiveQueryBundleSpec, project_watch_observation_intent


def _plan(db, *, candidate_id, disposition, minutes=0, created_at=None):
    authority = execution_context(
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
    )
    run = AnalysisRun(
        source_id=candidate_id,
        extra_source_ids=[],
        identity_key=f"agent-interface-test-{uuid4()}",
        extractor_version="test",
        matcher_version="test",
        evidence_reasoner_version="test",
        delta_version="test",
        scheduler_version="test",
        prompt_version="test",
        provider_version="test",
        embedding_model_version="none",
        pipeline_version="test",
        provider_type="rule",
        model_name=None,
        input_hash=f"input-{uuid4()}",
        kernel_snapshot_hash=f"kernel-{uuid4()}",
        status="COMPLETED",
        result_payload={"execution_authority": authority},
        completed_at=created_at or datetime.now(timezone.utc),
    )
    db.add(run); db.flush()
    row = AttentionPlan(
        candidate_type="SOURCE",
        candidate_id=candidate_id,
        disposition=disposition,
        processing_modes=[],
        urgency="NORMAL",
        cognitive_budget_minutes=minutes,
        kernel_target_ids=[],
        expected_output="NONE",
        reason=f"agent test {disposition}",
        watch_after_processing=False,
        scheduler_version="test",
        attention_policy_version="test",
        score_debug={},
        analysis_run_id=run.id,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(row); db.flush()
    return row


def test_today_is_read_only_and_excludes_drop_watch(client, db):
    candidate_ids = [uuid4() for _ in range(4)]
    for candidate_id, disposition in zip(candidate_ids, ["DROP", "WATCH", "AWARE", "ENGAGE"]):
        _plan(db, candidate_id=candidate_id, disposition=disposition)
    db.commit()
    before = db.execute(select(func.count()).select_from(AnalysisRun)).scalar_one()
    response = client.get("/agent/v1/today")
    assert response.status_code == 200
    dispositions = {row["disposition"] for row in response.json()["items"]}
    assert dispositions == {"AWARE", "ENGAGE"}
    after = db.execute(select(func.count()).select_from(AnalysisRun)).scalar_one()
    assert after == before


def test_attention_returns_latest_plan_per_candidate(client, db):
    candidate_id = uuid4()
    now = datetime.now(timezone.utc)
    _plan(db, candidate_id=candidate_id, disposition="AWARE", created_at=now - timedelta(minutes=2))
    latest = _plan(db, candidate_id=candidate_id, disposition="ENGAGE", created_at=now)
    db.commit()
    response = client.get("/agent/v1/attention")
    assert response.status_code == 200
    matching = [row for row in response.json()["items"] if row["candidate_id"] == str(candidate_id)]
    assert len(matching) == 1
    assert matching[0]["id"] == str(latest.id)
    assert matching[0]["disposition"] == "ENGAGE"


def test_agent_analyze_uses_canonical_pipeline_and_delivery(client, db):
    source = client.post("/sources", json={
        "source_type": "TEXT",
        "title": "Agent interface analysis probe",
        "content_text": "A bounded research observation for canonical analysis.",
    }).json()
    response = client.post("/agent/v1/analyze", json={"source_id": source["id"]})
    assert response.status_code == 200, response.text
    plan_id = response.json()["analysis"]["attention_plan"]["id"]
    envelope = db.execute(
        select(DeliveryEnvelope).where(DeliveryEnvelope.attention_plan_id == UUID(plan_id))
    ).scalars().first()
    assert envelope is not None
    assert envelope.disposition == response.json()["analysis"]["attention_plan"]["disposition"]


def test_capabilities_declares_single_attention_authority(client):
    response = client.get("/agent/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    contract = body["authority_contract"]
    assert contract["attention_authority"] == "canonical_raos_only"
    assert contract["agent_interface_may_assign_attention"] is False
    assert "why" in contract["read_only_commands"]
    assert contract["cognition_commands"] == ["analyze"]


def test_named_watch_projection_is_self_contained(db):
    watch = Watch(
        target_type="TREND",
        target_ref="Google EnvHarness",
        status="ACTIVE",
        created_reason="Phase 11E named WATCH regression",
        kernel_target_ids=[],
    )
    db.add(watch); db.flush()
    projection = project_watch_observation_intent(db, watch)
    assert projection.status == "READY"
    assert projection.intent == "Google EnvHarness"


def test_why_is_read_only_and_does_not_reanalyze(client, db):
    source = client.post("/sources", json={
        "source_type": "TEXT",
        "title": "Agent why regression",
        "content_text": "A small bounded observation for explanation testing.",
    }).json()
    analyzed = client.post("/agent/v1/analyze", json={"source_id": source["id"]})
    assert analyzed.status_code == 200
    before = db.execute(select(func.count()).select_from(AnalysisRun)).scalar_one()
    response = client.get(f"/agent/v1/why/{source['id']}")
    assert response.status_code == 200, response.text
    assert response.json()["reanalysis_performed"] is False
    after = db.execute(select(func.count()).select_from(AnalysisRun)).scalar_one()
    assert after == before


def test_agent_watch_can_be_cancelled_without_deleting_history(client, db):
    created = client.post("/agent/v1/watch", json={
        "topic": "Google EnvHarness",
        "target_type": "TREND",
        "active_acquisition": False,
    })
    assert created.status_code == 200, created.text
    watch_id = created.json()["watch"]["id"]
    cancelled = client.post(f"/agent/v1/watch/{watch_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["watch"]["status"] == "CANCELLED"
    assert db.get(Watch, UUID(watch_id)) is not None


def test_agent_facade_has_no_second_attention_or_llm_authority():
    from app.api import agent as agent_api

    source = inspect.getsource(agent_api)
    assert "AttentionPlan(" not in source
    assert "chat_json(" not in source
    assert "openai" not in source.casefold()
    assert "deepseek" not in source.casefold()
