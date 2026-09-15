from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import add_text, analyze


def _plan_id(result: dict) -> str:
    return (result.get("latest_attention_plan") or result["attention_plan"])["id"]


def _new_plan(client: TestClient, title: str) -> tuple[dict, str]:
    src = add_text(client, "A technical result about agent control and evaluation.", title=title)
    result = analyze(client, src["id"])
    return result, _plan_id(result)


def _different_disposition(current: str) -> str:
    return "WATCH" if current != "WATCH" else "AWARE"


def test_confirm_is_non_learning_confirmation(client: TestClient) -> None:
    _, plan_id = _new_plan(client, "p12a-confirm")
    body = client.post(f"/analysis/attention-plans/{plan_id}/feedback", json={"kind": "CONFIRM"}).json()
    attr = body["attribution"]
    assert attr["causal_scope"] == "NONE"
    assert attr["feedback_class"] == "CONFIRMATION"
    assert attr["evidence_provenance"] == "HUMAN_EXPLICIT"
    assert attr["personalization_eligible"] is False


def test_disposition_only_without_scope_fails_closed_to_unresolved(client: TestClient) -> None:
    result, plan_id = _new_plan(client, "p12a-unresolved")
    current = result["attention_plan"]["disposition"]
    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "disposition": _different_disposition(current)},
    )
    assert resp.status_code == 200, resp.text
    attr = resp.json()["attribution"]
    assert attr["feedback_class"] == "ATTENTION_POLICY_CORRECTION"
    assert attr["causal_scope"] == "UNRESOLVED"
    assert attr["personalization_eligible"] is False


def test_explicit_user_policy_residual_is_eligible_only_for_human_disposition_correction(client: TestClient) -> None:
    result, plan_id = _new_plan(client, "p12a-user-residual")
    current = result["attention_plan"]["disposition"]
    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={
            "kind": "CORRECT",
            "disposition": _different_disposition(current),
            "causal_scope": "USER_POLICY_RESIDUAL",
            "evidence_provenance": "HUMAN_EXPLICIT",
            "attribution_rationale": "Cognition and runtime are correct; I still want a different allocation.",
        },
    )
    assert resp.status_code == 200, resp.text
    attr = resp.json()["attribution"]
    assert attr["causal_scope"] == "USER_POLICY_RESIDUAL"
    assert attr["scope_source"] == "EXPLICIT"
    assert attr["personalization_eligible"] is True


def test_cognitive_adjudication_is_not_personalization(client: TestClient) -> None:
    _, plan_id = _new_plan(client, "p12a-cognition")
    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "delta_content": "Human adjudication: the cognitive interpretation is different."},
    )
    assert resp.status_code == 200, resp.text
    attr = resp.json()["attribution"]
    assert attr["feedback_class"] == "COGNITIVE_ADJUDICATION"
    assert attr["causal_scope"] == "COGNITION_ERROR"
    assert attr["scope_source"] == "CONSERVATIVE_DERIVATION"
    assert attr["personalization_eligible"] is False


def test_user_policy_residual_rejects_cognitive_correction(client: TestClient) -> None:
    _, plan_id = _new_plan(client, "p12a-reject-mixed")
    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={
            "kind": "CORRECT",
            "delta_content": "Different cognition",
            "causal_scope": "USER_POLICY_RESIDUAL",
        },
    )
    assert resp.status_code == 422
    assert "disposition-only" in resp.text


def test_proxy_or_passive_provenance_never_trains_personalization(client: TestClient) -> None:
    result, plan_id = _new_plan(client, "p12a-proxy")
    current = result["attention_plan"]["disposition"]
    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={
            "kind": "CORRECT",
            "disposition": _different_disposition(current),
            "causal_scope": "USER_POLICY_RESIDUAL",
            "evidence_provenance": "ASSISTANT_PROXY",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["attribution"]["personalization_eligible"] is False
