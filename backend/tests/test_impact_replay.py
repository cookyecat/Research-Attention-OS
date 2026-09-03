"""Cognitive Impact Replay / Attribution Harness v0.1."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import add_text, analyze


def _analyze_run(client: TestClient) -> dict:
    src = add_text(client, "A technical paper about motor intelligence latency.", title="impact-replay")
    result = analyze(client, src["id"])
    return result


def test_replay_is_reproducible_on_frozen_input(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    first = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "r1"})
    second = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "r2"})
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    a, b = first.json(), second.json()
    assert a["input_fingerprint"] == b["input_fingerprint"]
    assert a["stages"]["raw_effects"] == b["stages"]["raw_effects"]
    assert a["stages"]["grounded_effects"] == b["stages"]["grounded_effects"]
    assert a["stages"]["primary_update"] == b["stages"]["primary_update"]
    assert a["id"] != b["id"]


def test_replay_exposes_raw_grounded_primary_stages(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    resp = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule"})
    assert resp.status_code == 200, resp.text
    stages = resp.json()["stages"]
    assert "frozen_input" in stages
    assert isinstance(stages["raw_effects"], list)
    assert isinstance(stages["grounded_effects"], list)
    assert "operation" in stages["primary_update"]
    assert "target_node_id" in stages["primary_update"]
    attr = resp.json()["attribution"]
    assert "likely_stage" in attr
    assert attr["raw_count"] >= attr["grounded_count"]
    assert attr["discarded_count"] == len(attr["discarded"])


def test_replay_does_not_mutate_run_kernel_plan_or_feedback(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    before = client.get(f"/analysis/{run_id}").json()
    plans_before = client.get(f"/analysis/{run_id}/attention-plans").json()
    kernel_before = client.get("/kernel").json()
    feedback_before = client.get(f"/analysis/{run_id}/feedback").json()

    resp = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "immutable"})
    assert resp.status_code == 200, resp.text

    after = client.get(f"/analysis/{run_id}").json()
    plans_after = client.get(f"/analysis/{run_id}/attention-plans").json()
    kernel_after = client.get("/kernel").json()
    feedback_after = client.get(f"/analysis/{run_id}/feedback").json()

    assert after["update"] == before["update"]
    assert after["disposition"] == before["disposition"]
    assert after["delta_content"] == before["delta_content"]
    assert after["attention_plan"]["id"] == before["attention_plan"]["id"]
    assert after["original_attention_plan"] == before["original_attention_plan"]
    assert plans_after["attention_plans"] == plans_before["attention_plans"]
    assert kernel_after == kernel_before
    assert feedback_after == feedback_before

    listed = client.get(f"/analysis/{run_id}/impact-replays").json()
    assert len(listed) >= 1
    assert listed[0]["analysis_run_id"] == run_id


def test_replay_does_not_re_run_extraction_or_matching(client: TestClient, monkeypatch):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]

    def boom(*_a, **_k):
        raise AssertionError("Impact replay must not re-run extraction/matching")

    monkeypatch.setattr("app.services.extraction.extract_from_text", boom)
    monkeypatch.setattr("app.services.matching.match_kernel", boom)
    monkeypatch.setattr("app.cognitive.model_provider.ModelBackedCognitiveProvider.extract_information", boom)
    monkeypatch.setattr("app.cognitive.model_provider.ModelBackedCognitiveProvider.match_kernel", boom)

    resp = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule"})
    assert resp.status_code == 200, resp.text


def test_ab_same_input_single_runtime_variable(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    resp = client.post(
        f"/analysis/{run_id}/impact-replay/ab",
        json={
            "a": {"provider": "rule", "label": "baseline"},
            "b": {"provider": "rule", "thinking": "enabled", "label": "thinking-on"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    cmp = body["comparison"]
    assert cmp["same_input"] is True
    assert body["a"]["input_fingerprint"] == body["b"]["input_fingerprint"]
    assert cmp["config_a"]["provider"] == "rule"
    assert cmp["config_b"]["thinking"] == "enabled"
    assert cmp["config_a"].get("thinking") != cmp["config_b"].get("thinking")
    assert "raw_effects" in cmp["diff"]
    assert "grounded_effects" in cmp["diff"]
    assert "primary_update" in cmp["diff"]
