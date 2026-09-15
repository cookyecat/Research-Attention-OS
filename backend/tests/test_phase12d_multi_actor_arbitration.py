from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.models.acquisition import SourceDefinition
from app.models.scheduler import AttentionPlan
from app.models.watch import Watch, WatchDelegation
from app.services.active_acquisition import ActiveQueryBundleSpec


def _delegation_count(db, watch_id: str, status: str | None = None) -> int:
    stmt = select(func.count()).select_from(WatchDelegation).where(WatchDelegation.watch_id == UUID(watch_id))
    if status:
        stmt = stmt.where(WatchDelegation.status == status)
    return db.execute(stmt).scalar_one()


def test_two_agents_share_one_canonical_watch(client, db):
    a = client.post("/agent/v1/watch", json={
        "actor_id": "agent-a", "topic": "  Google   EnvHarness ",
        "target_type": "TREND", "active_acquisition": False,
    })
    b = client.post("/agent/v1/watch", json={
        "actor_id": "agent-b", "topic": "google envharness",
        "target_type": "TREND", "active_acquisition": False,
    })
    assert a.status_code == 200, a.text
    assert b.status_code == 200, b.text
    assert a.json()["watch"]["id"] == b.json()["watch"]["id"]
    assert b.json()["shared_watch_reused"] is True
    watch_id = a.json()["watch"]["id"]
    assert _delegation_count(db, watch_id, "ACTIVE") == 2
    assert b.json()["watch"]["delegation_count"] == 2


def test_same_actor_watch_delegation_is_idempotent(client, db):
    body = {"actor_id": "agent-idempotent", "topic": "RAOS actor arbitration", "active_acquisition": False}
    first = client.post("/agent/v1/watch", json=body)
    second = client.post("/agent/v1/watch", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["watch"]["id"] == second.json()["watch"]["id"]
    assert second.json()["delegation_created"] is False
    assert _delegation_count(db, first.json()["watch"]["id"], "ACTIVE") == 1


def test_different_trigger_semantics_fail_closed_without_duplicate_watch(client, db):
    first = client.post("/agent/v1/watch", json={
        "actor_id": "agent-trigger-a", "topic": "Shared Trigger Target",
        "triggers": ["NEW_EVIDENCE"], "active_acquisition": False,
    })
    assert first.status_code == 200
    watch_id = first.json()["watch"]["id"]
    second = client.post("/agent/v1/watch", json={
        "actor_id": "agent-trigger-b", "topic": "Shared Trigger Target",
        "triggers": ["FUNDING_EVENT"], "active_acquisition": False,
    })
    assert second.status_code == 409
    same = db.execute(select(Watch).where(Watch.target_ref == "Shared Trigger Target")).scalars().all()
    assert len(same) == 1
    assert str(same[0].id) == watch_id


def test_cancelling_one_actor_keeps_shared_watch_until_last_delegation(client, db):
    first = client.post("/agent/v1/watch", json={
        "actor_id": "agent-cancel-a", "topic": "Shared Cancel Target", "active_acquisition": False,
    }).json()
    watch_id = first["watch"]["id"]
    client.post("/agent/v1/watch", json={
        "actor_id": "agent-cancel-b", "topic": "Shared Cancel Target", "active_acquisition": False,
    })
    bundle = SourceDefinition(
        name="shared test bundle", source_type="ACTIVE_QUERY_BUNDLE",
        locator=ActiveQueryBundleSpec(
            watch_id=watch_id, intent="Shared Cancel Target", queries=("Shared Cancel Target",)
        ).to_locator(),
        enabled=True, poll_interval_seconds=1800,
    )
    db.add(bundle); db.commit()

    one = client.post(f"/agent/v1/watch/{watch_id}/cancel", json={"actor_id": "agent-cancel-a"})
    assert one.status_code == 200, one.text
    assert one.json()["watch"]["status"] == "ACTIVE"
    assert one.json()["remaining_active_delegations"] == 1
    db.refresh(bundle)
    assert bundle.enabled is True

    last = client.post(f"/agent/v1/watch/{watch_id}/cancel", json={"actor_id": "agent-cancel-b"})
    assert last.status_code == 200, last.text
    assert last.json()["watch"]["status"] == "CANCELLED"
    assert last.json()["remaining_active_delegations"] == 0
    assert last.json()["active_acquisition_disabled"] is True
    db.refresh(bundle)
    assert bundle.enabled is False


def test_core_owned_watch_survives_last_agent_delegation_cancel(client, db):
    candidate_id = uuid4()
    plan = AttentionPlan(
        candidate_type="SOURCE", candidate_id=candidate_id, disposition="WATCH",
        processing_modes=[], urgency="NORMAL", cognitive_budget_minutes=1,
        kernel_target_ids=[], expected_output="WATCH", reason="core-owned watch",
        watch_after_processing=True, scheduler_version="test", attention_policy_version="test",
        score_debug={},
    )
    db.add(plan); db.flush()
    watch = Watch(
        target_type="TREND", target_ref="Core owned target", status="ACTIVE",
        created_reason="core-owned", kernel_target_ids=[], attention_plan_id=plan.id,
    )
    db.add(watch); db.flush()
    delegation = WatchDelegation(
        watch_id=watch.id, declared_actor_id="agent-core-guest", status="ACTIVE",
        request_context={}, created_reason="guest delegation",
    )
    db.add(delegation); db.commit()

    response = client.post(f"/agent/v1/watch/{watch.id}/cancel", json={"actor_id": "agent-core-guest"})
    assert response.status_code == 200, response.text
    assert response.json()["remaining_active_delegations"] == 0
    assert response.json()["watch"]["status"] == "ACTIVE"


def test_agent_watch_request_cannot_smuggle_attention_authority(client):
    response = client.post("/agent/v1/watch", json={
        "actor_id": "agent-bad", "topic": "No direct authority",
        "active_acquisition": False, "disposition": "ENGAGE",
    })
    assert response.status_code == 422
