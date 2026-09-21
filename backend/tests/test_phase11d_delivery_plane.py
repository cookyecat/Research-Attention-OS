from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select

from app.models.analysis import AnalysisRun
from app.models.delivery import DeliveryEnvelope
from app.models.scheduler import AttentionPlan
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.execution_integrity import execution_context
from app.services.scheduler import get_decision_strategy
from app.services.delivery import (
    delivery_metrics,
    delivery_policy,
    ensure_delivery_envelope,
    list_visible_deliveries,
    pending_realtime_deliveries,
)


def _plan(db, *, disposition: str, urgency: str = "NORMAL") -> AttentionPlan:
    candidate_id = uuid4()
    authority = execution_context(
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
    )
    run = AnalysisRun(
        source_id=candidate_id,
        extra_source_ids=[],
        identity_key=f"delivery-test-{uuid4()}",
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
    )
    db.add(run); db.flush()
    row = AttentionPlan(
        candidate_type="SOURCE",
        candidate_id=candidate_id,
        disposition=disposition,
        processing_modes=[],
        urgency=urgency,
        cognitive_budget_minutes=None,
        kernel_target_ids=[],
        expected_output="NONE",
        reason=f"test {disposition}",
        watch_after_processing=False,
        scheduler_version="test",
        attention_policy_version="test",
        score_debug={},
        analysis_run_id=run.id,
    )
    db.add(row); db.flush()
    return row


def test_delivery_policy_four_dispositions():
    assert delivery_policy("DROP", "NORMAL").delivery_class == "SUPPRESSED"
    assert delivery_policy("AWARE", "NORMAL").channels == ("IN_APP_DIGEST",)
    assert delivery_policy("WATCH", "BACKGROUND").state == "HELD"
    assert delivery_policy("ENGAGE", "NORMAL").channels == ("IN_APP_REALTIME",)
    assert delivery_policy("ENGAGE", "PRIORITY").channels == ("IN_APP_REALTIME", "EMAIL", "PUSH")


def test_envelope_enqueue_is_idempotent_and_non_authoritative(db):
    plan = _plan(db, disposition="WATCH", urgency="BACKGROUND")
    first, created1 = ensure_delivery_envelope(db, plan)
    second, created2 = ensure_delivery_envelope(db, plan)
    assert created1 is True and created2 is False
    assert first.id == second.id
    assert first.state == "HELD"
    assert first.disposition == plan.disposition == "WATCH"
    assert len(db.execute(select(DeliveryEnvelope)).scalars().all()) == 1


def test_external_channels_fail_closed_when_unconfigured(db, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "delivery_email_to", None)
    monkeypatch.setattr(settings, "delivery_smtp_host", None)
    monkeypatch.setattr(settings, "delivery_push_webhook_url", None)
    plan = _plan(db, disposition="ENGAGE", urgency="PREEMPT")
    envelope, _ = ensure_delivery_envelope(db, plan)
    assert envelope.channel_status["IN_APP_REALTIME"]["state"] == "PENDING"
    assert envelope.channel_status["EMAIL"]["state"] == "UNAVAILABLE"
    assert envelope.channel_status["PUSH"]["state"] == "UNAVAILABLE"
    assert plan.disposition == "ENGAGE"


def test_metrics_count_interruption_only_after_realtime_send(db):
    from app.services.delivery import mark_delivery_channel
    plan = _plan(db, disposition="ENGAGE")
    envelope, _ = ensure_delivery_envelope(db, plan)
    assert delivery_metrics(db)["human_interruptions"] == 0
    mark_delivery_channel(db, envelope, "IN_APP_REALTIME", state="SENT")
    metrics = delivery_metrics(db)
    assert metrics["human_interruptions"] == 1
    assert metrics["by_delivery_class"]["INTERRUPT"] == 1


def test_delivery_api_acknowledge_and_dismiss(client, db):
    plan = _plan(db, disposition="AWARE")
    envelope, _ = ensure_delivery_envelope(db, plan)
    db.commit()
    r = client.post(f"/deliveries/{envelope.id}/acknowledge")
    assert r.status_code == 200
    assert r.json()["state"] == "ACKNOWLEDGED"

    plan2 = _plan(db, disposition="AWARE")
    envelope2, _ = ensure_delivery_envelope(db, plan2)
    db.commit()
    r2 = client.post(f"/deliveries/{envelope2.id}/dismiss")
    assert r2.status_code == 200
    assert r2.json()["state"] == "DISMISSED"


def test_websocket_delivers_only_interrupt_envelopes(client, db):
    aware = _plan(db, disposition="AWARE")
    engage = _plan(db, disposition="ENGAGE")
    aware_env, _ = ensure_delivery_envelope(db, aware)
    engage_env, _ = ensure_delivery_envelope(db, engage)
    db.commit()
    with client.websocket_connect("/deliveries/ws") as ws:
        message = ws.receive_json()
        assert message["id"] == str(engage_env.id)
        assert message["delivery_class"] == "INTERRUPT"
    db.refresh(engage_env)
    db.refresh(aware_env)
    assert engage_env.channel_status["IN_APP_REALTIME"]["state"] == "SENT"
    assert aware_env.state == "PASSIVE"


def test_non_authoritative_envelope_is_not_visible_or_realtime(db):
    plan = AttentionPlan(
        candidate_type="SOURCE",
        candidate_id=uuid4(),
        disposition="ENGAGE",
        processing_modes=[],
        urgency="PRIORITY",
        cognitive_budget_minutes=None,
        kernel_target_ids=[],
        expected_output="NONE",
        reason="unauthorized delivery probe",
        watch_after_processing=False,
        scheduler_version="test",
        attention_policy_version="test",
        score_debug={},
        analysis_run_id=None,
    )
    db.add(plan); db.flush()
    envelope, _ = ensure_delivery_envelope(db, plan)
    db.flush()
    assert envelope.delivery_class == "INTERRUPT"
    assert list_visible_deliveries(db) == []
    assert pending_realtime_deliveries(db) == []


def test_pipeline_created_attention_plan_owns_delivery_envelope(client, db):
    # Use the ordinary production analysis path; Delivery must be a side effect
    # of persisted AttentionPlan creation, not an alternate decision path.
    source = client.post('/sources', json={
        'source_type': 'TEXT',
        'title': 'Phase 11D delivery integration probe',
        'content_text': 'A routine low-impact observation with no material new evidence.'
    }).json()
    result = client.post('/analysis/extract', json={'source_id': source['id']})
    assert result.status_code == 200, result.text
    plan_id = result.json()['attention_plan']['id']
    row = db.execute(select(DeliveryEnvelope).where(DeliveryEnvelope.attention_plan_id == UUID(plan_id))).scalars().first()
    assert row is not None
    assert row.disposition == result.json()['attention_plan']['disposition']


def test_external_worker_ignores_unavailable_channels(db, monkeypatch):
    from sqlalchemy.orm import sessionmaker
    import app.db as app_db
    from app.config import settings
    from app.delivery_worker import deliver_external_once

    # The worker imports app.db.SessionLocal at call time. Keep this regression
    # isolated from any real/dogfood database state by binding it to this test DB.
    monkeypatch.setattr(
        app_db,
        "SessionLocal",
        sessionmaker(bind=db.get_bind(), autoflush=False, expire_on_commit=False),
    )
    monkeypatch.setattr(settings, 'delivery_email_to', None)
    monkeypatch.setattr(settings, 'delivery_smtp_host', None)
    monkeypatch.setattr(settings, 'delivery_push_webhook_url', None)
    plan = _plan(db, disposition='ENGAGE', urgency='PRIORITY')
    envelope, _ = ensure_delivery_envelope(db, plan)
    db.commit()
    counts = deliver_external_once(limit=10)
    assert counts == {'checked': 0, 'email_sent': 0, 'push_sent': 0, 'failed': 0, 'authority_blocked': 0}
    db.refresh(envelope)
    assert envelope.channel_status['EMAIL']['state'] == 'UNAVAILABLE'
    assert envelope.channel_status['PUSH']['state'] == 'UNAVAILABLE'


def test_email_transport_supports_multiple_recipients(monkeypatch):
    from app.config import settings
    from app.services.delivery_transports import _email_recipients

    monkeypatch.setattr(
        settings,
        "delivery_email_to",
        "alpha@example.com, beta@example.org",
    )
    assert _email_recipients() == ["alpha@example.com", "beta@example.org"]


def test_email_transport_supports_implicit_ssl(db, monkeypatch):
    import app.services.delivery_transports as transports
    from app.config import settings

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout): sent.update(host=host, port=port)
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def login(self, username, password): sent.update(username=username, password=password)
        def send_message(self, message): sent.update(to=message["To"]); return {}
    monkeypatch.setattr(settings, "delivery_email_to", "alpha@example.com;beta@example.org")
    monkeypatch.setattr(settings, "delivery_smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "delivery_smtp_port", 465)
    monkeypatch.setattr(settings, "delivery_smtp_username", "sender@example.test")
    monkeypatch.setattr(settings, "delivery_smtp_password", "secret")
    monkeypatch.setattr(settings, "delivery_smtp_from", "sender@example.test")
    monkeypatch.setattr(settings, "delivery_smtp_ssl", True)
    monkeypatch.setattr(settings, "delivery_smtp_starttls", False)
    monkeypatch.setattr(transports.smtplib, "SMTP_SSL", FakeSMTP)

    plan = _plan(db, disposition="ENGAGE", urgency="PRIORITY")
    envelope, _ = ensure_delivery_envelope(db, plan)
    transports.send_email_delivery(envelope)

    assert sent["host"] == "smtp.example.test"
    assert sent["port"] == 465
    assert sent["username"] == "sender@example.test"
    assert "alpha@example.com" in sent["to"]
    assert "beta@example.org" in sent["to"]

def test_email_transport_rejects_partial_recipient_failure(db, monkeypatch):
    import app.services.delivery_transports as transports
    from app.config import settings

    class FakeSMTP:
        def __init__(self, host, port, timeout): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def login(self, username, password): pass
        def send_message(self, message): return {"beta@example.org": (550, b"rejected")}

    monkeypatch.setattr(settings, "delivery_email_to", "alpha@example.com,beta@example.org")
    monkeypatch.setattr(settings, "delivery_smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "delivery_smtp_port", 465)
    monkeypatch.setattr(settings, "delivery_smtp_username", "sender@example.test")
    monkeypatch.setattr(settings, "delivery_smtp_password", "secret")
    monkeypatch.setattr(settings, "delivery_smtp_ssl", True)
    monkeypatch.setattr(settings, "delivery_smtp_starttls", False)
    monkeypatch.setattr(transports.smtplib, "SMTP_SSL", FakeSMTP)

    plan = _plan(db, disposition="ENGAGE", urgency="PRIORITY")
    envelope, _ = ensure_delivery_envelope(db, plan)
    try:
        transports.send_email_delivery(envelope)
    except transports.DeliveryTransportError as exc:
        assert "refused 1 recipient" in str(exc)
    else:
        raise AssertionError("partial SMTP refusal must not report success")
