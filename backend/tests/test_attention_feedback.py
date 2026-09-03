"""Human Feedback Loop v0.1 — Confirm / Correct on AttentionPlan."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import add_text, analyze


def _plan_id_from_analysis(result: dict) -> str:
    plan = result.get("attention_plan") or result.get("latest_attention_plan") or {}
    pid = plan.get("id")
    assert pid, "expected attention plan id on analysis response"
    return pid


def test_confirm_feedback_preserves_system_prediction(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fb-confirm")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    original_disposition = result["attention_plan"]["disposition"]
    original_update = result["update"]

    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CONFIRM"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kind"] == "CONFIRM"
    assert body["corrected_fields"] == []
    assert body["system_prediction"]["disposition"] == original_disposition
    assert body["user_correction"]["disposition"] == original_disposition
    assert body["user_correction"]["update"]["operation"] == original_update.get("operation")
    assert body["system_prediction"] == body["user_correction"]

    hydrated = client.get(f"/analysis/by-source/{src['id']}").json()
    assert hydrated["latest_attention_feedback"]["kind"] == "CONFIRM"
    assert hydrated["attention_plan"]["disposition"] == original_disposition


def test_correct_feedback_changes_only_specified_fields(client: TestClient):
    src = add_text(client, "Motor intelligence latency evaluation paper.", title="fb-correct")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    original = result["attention_plan"]["disposition"]

    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "disposition": "WATCH" if original != "WATCH" else "AWARE"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kind"] == "CORRECT"
    assert "disposition" in body["corrected_fields"]
    assert body["user_correction"]["disposition"] != body["system_prediction"]["disposition"]
    assert body["user_correction"]["update"] == body["system_prediction"]["update"]

    run_id = result["analysis_run"]["id"]
    run_resp = client.get(f"/analysis/{run_id}").json()
    assert run_resp["attention_plan"]["disposition"] == original


def test_correct_open_new_delta_content(client: TestClient):
    src = add_text(client, "A new temporal abstraction for tactile control.", title="fb-open")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)

    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={
            "kind": "CORRECT",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "Human adjudication: this opens a new tactile-control branch.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user_correction"]["update"]["operation"] == "OPEN_NEW"
    assert body["user_correction"]["update"]["target_node_id"] is None
    assert "delta_content" in body["corrected_fields"] or "update.operation" in body["corrected_fields"]


def test_correct_with_no_changes_rejected(client: TestClient):
    src = add_text(client, "Latency paper.", title="fb-noop")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    disposition = result["attention_plan"]["disposition"]

    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "disposition": disposition},
    )
    assert resp.status_code == 422


def test_list_feedback_by_run(client: TestClient):
    src = add_text(client, "Collective intelligence world models.", title="fb-list")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    run_id = result["analysis_run"]["id"]
    client.post(f"/analysis/attention-plans/{plan_id}/feedback", json={"kind": "CONFIRM"})
    listed = client.get(f"/analysis/{run_id}/feedback").json()
    assert len(listed) >= 1
    assert listed[0]["analysis_run_id"] == run_id


def test_feedback_does_not_mutate_analysis_run_payload(client: TestClient):
    src = add_text(client, "Embodied motor control benchmark.", title="fb-immutable")
    result = analyze(client, src["id"])
    run_id = result["analysis_run"]["id"]
    before = client.get(f"/analysis/{run_id}").json()
    plan_id = _plan_id_from_analysis(result)
    client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "disposition": "AWARE"},
    )
    after = client.get(f"/analysis/{run_id}").json()
    assert after["attention_plan"]["disposition"] == before["attention_plan"]["disposition"]
    assert after["update"] == before["update"]
    assert after["delta_content"] == before["delta_content"]
