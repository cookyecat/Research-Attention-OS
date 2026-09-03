"""Cognitive Impact Replay / Attribution Harness — experimental integrity."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm.attributes import flag_modified

from app.cognitive.client import LLMTimeoutError
from app.models.analysis import AnalysisRun
from app.models.source import Source
from app.services.impact_replay import (
    ImpactReplayConfig,
    compare_replays,
    repeatability_report,
    replay_analysis_run,
)
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
    body = resp.json()
    attr = body["attribution"]
    assert "likely_stage" in attr
    assert "attribution_sufficient" in attr
    assert "observed" in attr
    assert attr["raw_count"] >= attr["grounded_count"]
    assert attr["discarded_count"] == len(attr["discarded"])
    assert body["input_fidelity"] == "EXACT"
    assert body["frozen_input"]["input_fidelity"] == "EXACT"
    targets = body["frozen_input"]["kernel_targets"]
    assert isinstance(targets, list)
    for target in targets:
        for field in ("id", "type", "title", "proposition", "scope"):
            assert field in target


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


def test_ab_rule_thinking_is_not_an_effective_variable(client: TestClient):
    """thinking on a rule provider is requested, not executed. Must not claim single-variable control."""
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
    assert cmp["config_b"]["thinking"] == "enabled"
    assert "thinking" in cmp["declared_variable_diff"]
    assert cmp["variable_diff"] == {}
    assert cmp["controlled_single_variable"] is False
    assert cmp["causal_comparison"] is False
    assert "declared_experiment_variable_not_effective" in cmp["invalid_reasons"]
    assert "label" in cmp["ignored_fields"]
    assert "raw_effects" in cmp["diff"]


def test_replay_survives_live_kernel_and_source_edits(client: TestClient, db):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    assert result["impact_input"]["input_fidelity"] == "EXACT"
    first = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "before-edit"})
    assert first.status_code == 200, first.text
    before = first.json()
    assert before["input_fidelity"] == "EXACT"
    frozen_targets = before["frozen_input"]["kernel_targets"]
    original_props = {t["id"]: (t["proposition"], t["scope"], t["title"]) for t in frozen_targets}

    db.expire_all()
    from sqlalchemy import select
    from app.models.kernel import KernelNode

    for node in db.execute(select(KernelNode)).scalars():
        payload = dict(node.payload or {})
        payload["proposition"] = "Drifted proposition"
        payload["scope"] = "drifted-scope"
        node.title = f"Drifted {node.title}"
        node.payload = payload
        flag_modified(node, "payload")
    source = db.get(Source, UUID(result["source_id"]))
    assert source is not None
    source.content_text = "Completely unrelated source text after the AnalysisRun completed."
    source.title = "drifted-source"
    db.commit()

    second = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "after-edit"})
    assert second.status_code == 200, second.text
    after = second.json()
    assert after["input_fingerprint"] == before["input_fingerprint"]
    assert after["input_fidelity"] == "EXACT"
    assert after["stages"]["raw_effects"] == before["stages"]["raw_effects"]
    assert after["stages"]["grounded_effects"] == before["stages"]["grounded_effects"]
    assert after["stages"]["primary_update"] == before["stages"]["primary_update"]
    later_props = {t["id"]: (t["proposition"], t["scope"], t["title"]) for t in after["frozen_input"]["kernel_targets"]}
    assert later_props == original_props
    assert "Drifted proposition" not in {t["proposition"] for t in after["frozen_input"]["kernel_targets"]}


def test_missing_stored_freeze_is_reconstructed_not_exact(client: TestClient, db):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    db.expire_all()
    run = db.get(AnalysisRun, UUID(run_id))
    payload = dict(run.result_payload or {})
    assert "impact_input" in payload
    del payload["impact_input"]
    run.result_payload = payload
    flag_modified(run, "result_payload")
    db.commit()

    resp = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["input_fidelity"] == "RECONSTRUCTED"
    assert body["frozen_input"]["input_fidelity"] == "RECONSTRUCTED"
    assert body["frozen_input"]["reconstruction_gaps"]
    assert body["attribution"]["attribution_sufficient"] is False
    assert "input_reconstructed" in body["attribution"]["insufficient_reasons"]
    assert body["attribution"]["likely_stage"] is None


def test_label_is_not_an_experimental_variable(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    resp = client.post(
        f"/analysis/{run_id}/impact-replay/ab",
        json={
            "a": {"provider": "rule", "label": "alpha"},
            "b": {"provider": "rule", "label": "beta"},
        },
    )
    assert resp.status_code == 200, resp.text
    cmp = resp.json()["comparison"]
    assert cmp["same_input"] is True
    assert cmp["variable_diff"] == {}
    assert cmp["declared_variable_diff"] == {}
    assert cmp["controlled_single_variable"] is False
    assert "no_effective_variable_difference" in cmp["invalid_reasons"]
    assert "label" in cmp["ignored_fields"]


META = {"latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1, "model": "fake-impact"}


def _impact_payload(*, magnitude: float, reason: str) -> dict:
    return {
        "effects": [
            {
                "target_kernel_node_id": None,
                "operation": "OPEN_NEW",
                "change_magnitude": magnitude,
                "epistemic_strength": 0.3,
                "target_importance": 0.55,
                "reason": reason,
                "exploration_candidate": True,
            }
        ],
        "attention_cost": 2.0,
        "exploration_candidate": True,
        "evidence_maturity": 0.4,
        "threatens_active_work": False,
        "marketing_heavy": False,
        "high_quality_technical": True,
        "foundational_paper": False,
    }


def test_model_thinking_ab_is_controlled_single_variable(client: TestClient, db):
    result = _analyze_run(client)
    run_id = UUID(result["analysis_run"]["id"])

    def chat(messages, **_kwargs):
        return _impact_payload(magnitude=0.55, reason="stable model output"), META

    db.expire_all()
    a = replay_analysis_run(
        db,
        run_id,
        config=ImpactReplayConfig(provider="model", thinking="disabled", label="off"),
        chat_fn=chat,
        persist=True,
    )
    b = replay_analysis_run(
        db,
        run_id,
        config=ImpactReplayConfig(provider="model", thinking="enabled", label="on"),
        chat_fn=chat,
        persist=True,
    )
    db.commit()
    cmp = compare_replays(a, b)
    assert a["input_fingerprint"] == b["input_fingerprint"]
    assert a["input_fidelity"] == "EXACT"
    assert cmp["same_input"] is True
    assert cmp["exact_frozen_input"] is True
    assert set(cmp["variable_diff"]) == {"thinking"}
    assert cmp["variable_diff"]["thinking"]["a"] == "disabled"
    assert cmp["variable_diff"]["thinking"]["b"] == "enabled"
    assert cmp["single_effective_variable"] is True
    assert cmp["controlled_single_variable"] is True
    assert cmp["causal_comparison"] is True
    assert cmp["execution_valid"] is True
    assert cmp["invalid_reasons"] == []


def test_fallback_timeout_invalidates_controlled_ab(client: TestClient, db):
    result = _analyze_run(client)
    run_id = UUID(result["analysis_run"]["id"])

    def boom(messages, **kwargs):
        raise LLMTimeoutError(float(kwargs.get("timeout") or 1.0))

    db.expire_all()
    a = replay_analysis_run(
        db,
        run_id,
        config=ImpactReplayConfig(provider="model", thinking="disabled", label="a"),
        chat_fn=boom,
        persist=True,
    )
    b = replay_analysis_run(
        db,
        run_id,
        config=ImpactReplayConfig(provider="model", thinking="enabled", label="b"),
        chat_fn=boom,
        persist=True,
    )
    db.commit()
    cmp = compare_replays(a, b)
    assert a["runtime"]["fallback_used"] is True
    assert b["runtime"]["fallback_used"] is True
    assert a["runtime"]["error_type"] == "timeout"
    assert cmp["causal_comparison"] is False
    assert cmp["controlled_single_variable"] is False
    assert cmp["execution_valid"] is False
    reasons = " ".join(cmp["invalid_reasons"])
    assert "fallback" in reasons or "timeout" in reasons


def test_llm_stage_jitter_is_model_repeatability_not_harness_failure(client: TestClient, db):
    result = _analyze_run(client)
    run_id = UUID(result["analysis_run"]["id"])

    class Jitter:
        def __init__(self):
            self.n = 0

        def __call__(self, messages, **_kwargs):
            self.n += 1
            return _impact_payload(magnitude=0.4 if self.n == 1 else 0.8, reason=f"draw-{self.n}"), META

    db.expire_all()
    chat = Jitter()
    first = replay_analysis_run(
        db, run_id, config=ImpactReplayConfig(provider="model", label="draw-1"), chat_fn=chat, persist=True
    )
    second = replay_analysis_run(
        db, run_id, config=ImpactReplayConfig(provider="model", label="draw-2"), chat_fn=chat, persist=True
    )
    db.commit()
    report = repeatability_report(first, second)
    assert report["input_reproducible"] is True
    assert report["stages_identical"] is False
    assert report["deterministic"] is False
    assert report["model_repeatable"] is False
    assert report["harness_ok"] is True
    assert first["attribution"]["likely_stage"] is None
    assert "model_output_variance_possible" in first["attribution"]["insufficient_reasons"]


def test_rule_twice_still_requires_stage_identity(client: TestClient):
    result = _analyze_run(client)
    run_id = result["analysis_run"]["id"]
    first = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "t1"}).json()
    second = client.post(f"/analysis/{run_id}/impact-replay", json={"provider": "rule", "label": "t2"}).json()
    report = repeatability_report(first, second)
    assert report["input_reproducible"] is True
    assert report["stages_identical"] is True
    assert report["deterministic"] is True
    assert report["harness_ok"] is True
