from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.scheduler import RuntimeContext
from app.models.watch import Watch
from app.services.brain_world_model import (
    BrainWorldSnapshot,
    build_brain_world_snapshot,
    explicit_runtime_fact,
    model_inference_fact,
    runtime_view_from_brain_snapshot,
    trusted_bool,
)


def _now():
    return datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)


def test_explicit_runtime_context_becomes_authoritative_runtime_view(db):
    ctx = RuntimeContext(
        current_task="Write Phase 7 paper",
        session_topic="RAOS",
        available_attention_minutes=30,
        interruptibility="LOW",
        cognitive_capacity="NORMAL",
        deadline_at=_now() + timedelta(hours=2),
        captured_at=_now(),
    )
    db.add(ctx); db.flush()
    snap = build_brain_world_snapshot(runtime_context=ctx, db=db, kernel_snapshot_hash="k0", captured_at=_now())
    view = runtime_view_from_brain_snapshot(snap, now=_now())
    assert view.current_task == "Write Phase 7 paper"
    assert view.session_topic == "RAOS"
    assert view.available_attention_minutes == 30
    assert view.interruptibility == "LOW"
    assert view.deadline_minutes == 120.0
    assert snap.kernel_snapshot_hash == "k0"


def test_model_inference_cannot_masquerade_as_authoritative_user_state():
    advisory = model_inference_fact(
        "threatens_active_work", True, observed_at=_now(),
        provenance="impact model guessed active-work overlap", confidence=0.95,
    )
    snap = BrainWorldSnapshot(captured_at=_now(), runtime_facts=(), advisory_facts=(advisory,))
    assert trusted_bool(snap, "threatens_active_work", now=_now()) is False
    assert snap.authoritative_value("threatens_active_work", now=_now()) is None


def test_explicit_authoritative_signal_can_be_consumed():
    fact = explicit_runtime_fact(
        "threatens_active_work", True, observed_at=_now(), provenance="explicit trusted runtime signal"
    )
    snap = BrainWorldSnapshot(captured_at=_now(), runtime_facts=(fact,))
    assert trusted_bool(snap, "threatens_active_work", now=_now()) is True
def test_expired_authoritative_signal_is_not_current_state():
    fact = explicit_runtime_fact(
        "current_task", "stale task", observed_at=_now() - timedelta(hours=3),
        valid_until=_now() - timedelta(minutes=1), provenance="expired runtime observation",
    )
    snap = BrainWorldSnapshot(captured_at=_now(), runtime_facts=(fact,))
    assert snap.authoritative_value("current_task", now=_now()) is None
    assert runtime_view_from_brain_snapshot(snap, now=_now()).current_task is None


def test_snapshot_tracks_only_active_watch_obligations(db):
    active = Watch(target_type="EVENT", target_ref="a", status="ACTIVE", created_reason="keep watching")
    closed = Watch(target_type="EVENT", target_ref="b", status="CLOSED", created_reason="done")
    db.add_all([active, closed]); db.flush()
    snap = build_brain_world_snapshot(db=db, captured_at=_now())
    assert str(active.id) in snap.active_watch_ids
    assert str(closed.id) not in snap.active_watch_ids
def test_production_plan_records_auditable_brain_snapshot(client):
    from tests.conftest import add_text

    src = add_text(client, "A technical note about runtime scheduling.", title="brain-world-plan")
    response = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "Finish Phase 7C",
                "session_topic": "RAOS",
                "available_attention_minutes": 25,
                "interruptibility": "LOW",
            },
        },
    )
    assert response.status_code == 200, response.text
    debug = response.json()["attention_plan"]["score_debug"]
    snapshot = debug["brain_world_model"]
    facts = {fact["key"]: fact for fact in snapshot["runtime_facts"]}
    assert snapshot["version"] == "brain-world-model-v0.1"
    assert facts["current_task"]["value"] == "Finish Phase 7C"
    assert facts["current_task"]["authority"] == "AUTHORITATIVE"
    assert facts["current_task"]["source"] == "USER_EXPLICIT_RUNTIME"
    assert debug["features"]["threatens_active_work"] is False
def test_reschedule_records_current_brain_state_not_original_debug(client):
    from tests.conftest import add_text, analyze

    src = add_text(client, "A note about rescheduling and attention.", title="brain-reschedule")
    first = analyze(client, src["id"])
    first_debug = first["attention_plan"]["score_debug"]
    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "New current task"}},
    )
    assert planned.status_code == 200, planned.text
    debug = planned.json()["attention_plan"]["score_debug"]
    facts = {fact["key"]: fact for fact in debug["brain_world_model"]["runtime_facts"]}
    assert facts["current_task"]["value"] == "New current task"
    assert debug["brain_world_model"] != first_debug.get("brain_world_model")
def test_explicit_runtime_threat_reaches_brain_snapshot_and_features(client):
    from tests.conftest import add_text

    src = add_text(client, "A technical note about an active project risk.", title="brain-threat")
    response = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "Submit current paper",
                "threatens_active_work": True,
            },
        },
    )
    assert response.status_code == 200, response.text
    debug = response.json()["attention_plan"]["score_debug"]
    facts = {fact["key"]: fact for fact in debug["brain_world_model"]["runtime_facts"]}
    assert facts["threatens_active_work"]["value"] is True
    assert facts["threatens_active_work"]["authority"] == "AUTHORITATIVE"
    assert debug["features"]["threatens_active_work"] is True
