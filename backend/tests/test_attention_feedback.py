"""Human Feedback Loop v0.1 — Confirm / Correct on AttentionPlan."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm.attributes import flag_modified

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.models.analysis import AnalysisRun
from app.services.attention_feedback import merge_correction, public_update, system_prediction_from_plan
from tests.acceptance.test_cases import CASE_J
from tests.conftest import add_text, analyze, kernel_index
from tests.fakes import SemanticFakeChat


def _plan_id_from_analysis(result: dict) -> str:
    plan = result.get("latest_attention_plan") or result.get("attention_plan") or {}
    pid = plan.get("id")
    assert pid, "expected attention plan id on analysis response"
    return pid


def _freeze_run_prediction(db, run_id: str, **fields) -> dict:
    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    payload.update(fields)
    run.result_payload = payload
    flag_modified(run, "result_payload")
    db.commit()
    return payload


def _freeze_plan_judgment(
    db,
    plan_id: str,
    *,
    operation: str,
    target_node_id: str | None = None,
    node_type: str | None = None,
    reason: str = "frozen test judgment",
) -> None:
    from app.models.scheduler import AttentionPlan

    plan = db.get(AttentionPlan, UUID(str(plan_id)))
    debug = dict(plan.score_debug or {})
    matches = []
    if target_node_id and node_type:
        matches = [
            {
                "node_id": target_node_id,
                "node_type": node_type,
                "title": node_type,
                "score": 0.9,
                "reason": "frozen locate",
                "structural": False,
                "relevance_type": "TOPIC",
            }
        ]
    debug["matches"] = matches
    debug["cognitive_impact"] = {
        "effects": [
            {
                "operation": operation,
                "target_kernel_node_id": target_node_id,
                "change_magnitude": 0.9,
                "epistemic_strength": 0.8,
                "target_importance": 0.7,
                "reason": reason,
                "target_node_type": node_type,
            }
        ]
    }
    plan.score_debug = debug
    flag_modified(plan, "score_debug")
    db.commit()


class _Run:
    def __init__(self, payload: dict):
        self.result_payload = payload


class _Plan:
    def __init__(self, disposition: str, score_debug=None):
        self.disposition = disposition
        self.score_debug = score_debug or {}


def test_public_update_null_means_no_cognitive_update():
    assert public_update(None) is None
    assert public_update({"operation": None, "target_node_id": None}) is None
    assert public_update({"operation": "OPEN_NEW", "target_node_id": "x"}) == {
        "operation": "OPEN_NEW",
        "target_node_id": None,
    }


def test_system_prediction_uses_plan_frozen_judgment_not_raw_payload():
    target = str(uuid4())
    plan = _Plan(
        "ENGAGE",
        score_debug={
            "cognitive_impact": {
                "effects": [
                    {
                        "operation": "OPEN_NEW",
                        "target_kernel_node_id": None,
                        "change_magnitude": 0.9,
                        "epistemic_strength": 0.8,
                        "target_importance": 0.7,
                        "reason": "new branch",
                    }
                ]
            }
        },
    )
    run = _Run(
        {
            "disposition": "WATCH",
            "update": {"operation": "CHALLENGE", "target_node_id": target},
            "delta_content": "frozen-delta",
            "attention_plan": {
                "disposition": "ENGAGE",
                "update": {"operation": "CHALLENGE", "target_node_id": target},
            },
        }
    )
    pred = system_prediction_from_plan(plan, run)
    assert pred == {
        "disposition": "ENGAGE",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "delta_content": "new branch",
    }


def test_system_prediction_interprets_frozen_impact_when_payload_update_absent():
    run = _Run(
        {
            "disposition": "AWARE",
            "attention_plan": {
                "disposition": "AWARE",
                "score_debug": {
                    "cognitive_impact": {
                        "effects": [
                            {
                                "operation": "OPEN_NEW",
                                "target_kernel_node_id": None,
                                "change_magnitude": 0.9,
                                "epistemic_strength": 0.8,
                                "target_importance": 0.7,
                                "reason": "current interpretation",
                            }
                        ]
                    }
                },
            },
        }
    )
    pred = system_prediction_from_plan(_Plan("AWARE"), run)
    assert pred["disposition"] == "AWARE"
    assert pred["update"] == {"operation": "OPEN_NEW", "target_node_id": None}
    assert pred["delta_content"] == "current interpretation"


def test_merge_omitted_update_keeps_system_update():
    system = {
        "disposition": "WATCH",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "delta_content": "hello",
    }
    merged = merge_correction(system, {"disposition": "AWARE"})
    assert merged["update"] == {"operation": "OPEN_NEW", "target_node_id": None}
    assert merged["disposition"] == "AWARE"
    assert merged["delta_content"] == "hello"


def test_merge_explicit_null_update_clears_cognitive_update():
    system = {
        "disposition": "WATCH",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "delta_content": "hello",
    }
    merged = merge_correction(system, {"update": None})
    assert merged["update"] is None
    assert merged["disposition"] == "WATCH"


def test_merge_omitted_target_keeps_system_target():
    target = str(uuid4())
    system = {
        "disposition": "ENGAGE",
        "update": {"operation": "REINFORCE", "target_node_id": target},
        "delta_content": "",
    }
    merged = merge_correction(system, {"update": {"operation": "CHALLENGE"}})
    assert merged["update"] == {"operation": "CHALLENGE", "target_node_id": target}


def test_merge_unknown_operation_rejected_not_coerced_to_null():
    system = {
        "disposition": "WATCH",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "delta_content": "hello",
    }
    for illegal in ("REFINE", "NO_MATERIAL_CHANGE", "NOT_A_REAL_OP"):
        try:
            merge_correction(system, {"update": {"operation": illegal}})
        except HTTPException as exc:
            assert exc.status_code == 422, illegal
        else:
            raise AssertionError(f"expected 422 for operation {illegal}")


def test_merge_explicit_open_new_target_rejected_not_stripped():
    system = {
        "disposition": "WATCH",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "delta_content": "hello",
    }
    try:
        merge_correction(
            system,
            {"update": {"operation": "OPEN_NEW", "target_node_id": str(uuid4())}},
        )
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("expected 422 for explicit OPEN_NEW target")


def test_merge_explicit_null_target_on_targeted_op_rejected():
    system = {
        "disposition": "ENGAGE",
        "update": {"operation": "REINFORCE", "target_node_id": str(uuid4())},
        "delta_content": "",
    }
    try:
        merge_correction(system, {"update": {"operation": "CHALLENGE", "target_node_id": None}})
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("expected 422 for explicit null target on CHALLENGE")


def test_confirm_feedback_preserves_system_prediction(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fb-confirm")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    original_disposition = result["attention_plan"]["disposition"]
    original_update = public_update(result["update"])

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
    assert body["system_prediction"]["update"] == original_update
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


def test_correct_to_no_cognitive_update(client: TestClient, db):
    src = add_text(client, "A new temporal abstraction for tactile control.", title="fb-null-update")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    run_id = result["analysis_run"]["id"]
    _freeze_plan_judgment(
        db,
        plan_id,
        operation="OPEN_NEW",
        reason="system thought this opened a branch",
    )
    _freeze_run_prediction(
        db,
        run_id,
        disposition="WATCH",
        update={"operation": "OPEN_NEW", "target_node_id": None},
        delta_content="system thought this opened a branch",
    )

    omitted = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "disposition": "AWARE"},
    )
    assert omitted.status_code == 200, omitted.text
    assert omitted.json()["user_correction"]["update"] == {"operation": "OPEN_NEW", "target_node_id": None}

    cleared = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": None},
    )
    assert cleared.status_code == 200, cleared.text
    body = cleared.json()
    assert body["user_correction"]["update"] is None
    assert body["system_prediction"]["update"] == {"operation": "OPEN_NEW", "target_node_id": None}
    assert "update" in body["corrected_fields"]


def test_omitted_update_differs_from_explicit_null(client: TestClient, db):
    src = add_text(client, "Latency paper.", title="fb-omit-vs-null")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    belief = client.post(
        "/kernel/nodes",
        json={"node_type": "BELIEF", "title": "Held belief for omit/null", "payload": {"proposition": "x"}},
    ).json()
    _freeze_plan_judgment(
        db,
        plan_id,
        operation="REINFORCE",
        target_node_id=belief["id"],
        node_type="BELIEF",
        reason="frozen",
    )
    _freeze_run_prediction(
        db,
        result["analysis_run"]["id"],
        disposition="ENGAGE",
        update={"operation": "REINFORCE", "target_node_id": belief["id"]},
        delta_content="frozen",
    )

    keep = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "delta_content": "only delta changed"},
    )
    assert keep.status_code == 200, keep.text
    assert keep.json()["user_correction"]["update"]["operation"] == "REINFORCE"
    assert keep.json()["user_correction"]["update"]["target_node_id"] == belief["id"]

    clear = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": None},
    )
    assert clear.status_code == 200, clear.text
    assert clear.json()["user_correction"]["update"] is None


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
    assert "delta_content" in body["corrected_fields"] or "update.operation" in body["corrected_fields"] or "update" in body["corrected_fields"]


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


def test_system_prediction_ignores_mutated_payload_update(client: TestClient, db):
    src = add_text(client, "Motor intelligence latency evaluation paper.", title="fb-frozen")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    plan_disp = result["attention_plan"]["disposition"]
    visible_update = public_update(result["update"])
    visible_delta = result.get("delta_content") or ""
    other = "WATCH" if plan_disp != "WATCH" else "AWARE"
    bogus = str(uuid4())
    _freeze_run_prediction(
        db,
        result["analysis_run"]["id"],
        disposition=other,
        update={"operation": "CHALLENGE", "target_node_id": bogus},
        delta_content="immutable-run-output",
    )

    resp = client.post(f"/analysis/attention-plans/{plan_id}/feedback", json={"kind": "CONFIRM"})
    assert resp.status_code == 200, resp.text
    pred = resp.json()["system_prediction"]
    assert pred["disposition"] == plan_disp
    assert pred["disposition"] != other
    assert public_update(pred["update"]) == visible_update
    assert pred["delta_content"] == visible_delta
    assert public_update(pred["update"]) != {"operation": "CHALLENGE", "target_node_id": bogus}


def test_correct_target_need_not_be_matcher_hit(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fb-off-hit")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    created = client.post(
        "/kernel/nodes",
        json={
            "node_type": "BELIEF",
            "title": "Unrelated tactile-only belief",
            "payload": {"proposition": "Tactile-only controllers never transfer."},
        },
    )
    assert created.status_code == 200, created.text
    node_id = created.json()["id"]
    assert node_id not in {m["node_id"] for m in result["kernel_matches"]}

    resp = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "REINFORCE", "target_node_id": node_id}},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_correction"]["update"] == {
        "operation": "REINFORCE",
        "target_node_id": node_id,
    }


def test_correct_target_rejects_missing_and_ineligible_nodes(client: TestClient):
    src = add_text(client, "Motor intelligence latency evaluation paper.", title="fb-bad-target")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    index = kernel_index(client)

    missing = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "CHALLENGE", "target_node_id": str(uuid4())}},
    )
    assert missing.status_code == 422

    project = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "REINFORCE", "target_node_id": index["P1"]["id"]}},
    )
    assert project.status_code == 422

    goal = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "CHALLENGE", "target_node_id": index["G1"]["id"]}},
    )
    assert goal.status_code == 422


def test_feedback_targets_latest_plan_not_original(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fb-latest")
    first = analyze(client, src["id"])
    original_id = first["attention_plan"]["id"]
    run_id = first["analysis_run"]["id"]
    planned = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {"current_task": "later", "interruptibility": "LOW", "cognitive_capacity": "LOW"},
        },
    )
    assert planned.status_code == 200, planned.text
    latest_id = planned.json()["attention_plan"]["id"]
    assert latest_id != original_id

    stale = client.post(f"/analysis/attention-plans/{original_id}/feedback", json={"kind": "CONFIRM"})
    assert stale.status_code == 422

    ok = client.post(f"/analysis/attention-plans/{latest_id}/feedback", json={"kind": "CONFIRM"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["attention_plan_id"] == latest_id
    assert ok.json()["system_prediction"]["disposition"] == planned.json()["attention_plan"]["disposition"]
    assert public_update(ok.json()["system_prediction"]["update"]) == public_update(first["update"])

    stored = client.get(f"/analysis/by-source/{src['id']}").json()
    assert stored["original_attention_plan"]["id"] == original_id
    assert stored["latest_attention_plan"]["id"] == latest_id
    assert stored["latest_attention_feedback"]["attention_plan_id"] == latest_id
    assert stored["attention_plan"]["id"] == original_id


def test_http_omitted_target_keeps_system_target(client: TestClient, db):
    src = add_text(client, "Motor intelligence latency evaluation paper.", title="fb-omit-target")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    belief = client.post(
        "/kernel/nodes",
        json={"node_type": "BELIEF", "title": "Held target", "payload": {"proposition": "y"}},
    ).json()
    _freeze_plan_judgment(
        db,
        plan_id,
        operation="REINFORCE",
        target_node_id=belief["id"],
        node_type="BELIEF",
        reason="frozen",
    )
    _freeze_run_prediction(
        db,
        result["analysis_run"]["id"],
        disposition="ENGAGE",
        update={"operation": "REINFORCE", "target_node_id": belief["id"]},
        delta_content="frozen",
    )

    keep_target = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "CHALLENGE"}},
    )
    assert keep_target.status_code == 200, keep_target.text
    assert keep_target.json()["user_correction"]["update"] == {
        "operation": "CHALLENGE",
        "target_node_id": belief["id"],
    }

    null_target = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "CHALLENGE", "target_node_id": None}},
    )
    assert null_target.status_code == 422


def test_http_unknown_operation_and_illegal_open_new_target_rejected(client: TestClient):
    src = add_text(client, "Motor intelligence latency evaluation paper.", title="fb-illegal-op")
    result = analyze(client, src["id"])
    plan_id = _plan_id_from_analysis(result)
    belief = client.post(
        "/kernel/nodes",
        json={"node_type": "BELIEF", "title": "Target for illegal OPEN_NEW", "payload": {"proposition": "z"}},
    ).json()

    unknown = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "REFINE"}},
    )
    assert unknown.status_code == 422

    retired = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={"kind": "CORRECT", "update": {"operation": "NO_MATERIAL_CHANGE"}},
    )
    assert retired.status_code == 422

    illegal_open = client.post(
        f"/analysis/attention-plans/{plan_id}/feedback",
        json={
            "kind": "CORRECT",
            "update": {"operation": "OPEN_NEW", "target_node_id": belief["id"]},
        },
    )
    assert illegal_open.status_code == 422


def test_reschedule_system_prediction_uses_latest_plan_disposition(client: TestClient, monkeypatch):
    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=SemanticFakeChat()),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)
    src = add_text(client, CASE_J, title="fb-reschedule-disp")
    first = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "reading",
                "interruptibility": "HIGH",
                "cognitive_capacity": "HIGH",
            },
        },
    )
    assert first.status_code == 200, first.text
    original = first.json()["attention_plan"]
    original_update = public_update(first.json()["update"])
    original_delta = first.json().get("delta_content") or ""
    deadline = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    planned = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "camera-ready",
                "interruptibility": "LOW",
                "cognitive_capacity": "LOW",
                "deadline_at": deadline,
            },
        },
    )
    assert planned.status_code == 200, planned.text
    latest = planned.json()["attention_plan"]
    assert latest["id"] != original["id"]
    assert latest["disposition"] != original["disposition"]

    ok = client.post(f"/analysis/attention-plans/{latest['id']}/feedback", json={"kind": "CONFIRM"})
    assert ok.status_code == 200, ok.text
    pred = ok.json()["system_prediction"]
    assert pred["disposition"] == latest["disposition"]
    assert pred["disposition"] != original["disposition"]
    assert public_update(pred["update"]) == original_update
    assert pred["delta_content"] == original_delta
    assert planned.json()["analysis_run"]["id"] == first.json()["analysis_run"]["id"]
