"""Analysis provenance: frozen Δ_t fail-closed, DROP ≠ no change, identity coverage."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm.attributes import flag_modified

from app.enums import SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.scheduler import AttentionPlan
from app.models.source import Source, SourceEdge
from app.services.analysis_runs import compute_identity, input_hash
from app.services.attention_feedback import public_update
from app.services.source_graph import analysis_relational_context_digest, persist_source_edge
from tests.conftest import add_observation, add_text, analyze, kernel_index


def _commit_source(db, source_id: str, **fields) -> None:
    row = db.get(Source, UUID(str(source_id)))
    for key, value in fields.items():
        setattr(row, key, value)
    db.commit()


def test_input_hash_covers_title_and_type():
    class S:
        def __init__(self, **kw):
            self.id = kw.get("id", uuid4())
            self.content_hash = kw.get("content_hash", "h")
            self.content_text = kw.get("content_text", "body")
            self.source_type = kw.get("source_type", "TEXT")
            self.title = kw.get("title", "t")

    base = S()
    extra = S(title="extra", source_type="TEXT")
    a = input_hash(base, [extra])
    assert a != input_hash(S(title="other"), [extra])
    assert a != input_hash(S(source_type="PAPER"), [extra])
    extra_renamed = S(id=extra.id, content_hash=extra.content_hash, content_text=extra.content_text, title="renamed", source_type="TEXT")
    assert a != input_hash(base, [extra_renamed])
    extra_typed = S(id=extra.id, content_hash=extra.content_hash, content_text=extra.content_text, title="extra", source_type="MANUAL_OBSERVATION")
    assert a != input_hash(base, [extra_typed])
    extra2 = S()
    assert input_hash(base, [extra, extra2]) == input_hash(base, [extra2, extra])


def test_identity_includes_relational_digest():
    base = dict(
        input_digest="in",
        kernel_digest="k",
        provider_type="rule",
        model_name=None,
        embedding_model_version="none",
    )
    assert compute_identity(**base) != compute_identity(**base, relational_digest="other")
    assert compute_identity(**base, relational_digest="x") == compute_identity(**base, relational_digest="x")


def test_source_title_change_creates_new_analysis_run(client: TestClient, db):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-title")
    first = analyze(client, src["id"])
    _commit_source(db, src["id"], title="prov-title-changed")
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]
    assert second["analysis_run"]["input_hash"] != first["analysis_run"]["input_hash"]


def test_source_type_change_creates_new_analysis_run(client: TestClient, db):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-type")
    first = analyze(client, src["id"])
    _commit_source(db, src["id"], source_type="MANUAL_OBSERVATION")
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]


def test_extra_source_title_and_type_change_identity(client: TestClient, db):
    primary = add_text(client, "Primary motor intelligence latency paper.", title="prov-primary")
    extra = add_text(client, "Supporting observation about latency.", title="prov-extra")
    first = analyze(client, primary["id"], extra_ids=[extra["id"]])
    _commit_source(db, extra["id"], title="prov-extra-renamed")
    renamed = analyze(client, primary["id"], extra_ids=[extra["id"]])
    assert renamed["analysis_run"]["id"] != first["analysis_run"]["id"]
    _commit_source(db, extra["id"], source_type="MANUAL_OBSERVATION")
    retyped = analyze(client, primary["id"], extra_ids=[extra["id"]])
    assert retyped["analysis_run"]["id"] != renamed["analysis_run"]["id"]


def test_extra_source_order_does_not_change_identity(client: TestClient):
    primary = add_text(client, "Primary motor intelligence latency paper.", title="prov-order-p")
    extra_a = add_text(client, "Extra A about latency evaluation.", title="prov-order-a")
    extra_b = add_observation(client, "Extra B measured 12ms latency.", title="prov-order-b")
    first = analyze(client, primary["id"], extra_ids=[extra_a["id"], extra_b["id"]])
    second = analyze(client, primary["id"], extra_ids=[extra_b["id"], extra_a["id"]])
    assert second["analysis_run"]["id"] == first["analysis_run"]["id"]


def test_kernel_snapshot_change_creates_new_analysis_run(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-kernel")
    first = analyze(client, src["id"])
    created = client.post(
        "/kernel/nodes",
        json={"node_type": "BELIEF", "title": "New provenance belief", "payload": {"proposition": "x"}},
    )
    assert created.status_code == 200, created.text
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]
    assert second["analysis_run"]["kernel_snapshot_hash"] != first["analysis_run"]["kernel_snapshot_hash"]


def test_relevant_source_edge_changes_identity_unrelated_does_not(client: TestClient, db):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-edge")
    other = add_text(client, "Unrelated secondary document about folding cloth.", title="prov-other")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]

    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.CITES)
    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.DISCUSSES)
    db.commit()
    after_unrelated = analyze(client, src["id"])
    assert after_unrelated["analysis_run"]["id"] == run_id

    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.DERIVED_FROM)
    db.commit()
    after_derived = analyze(client, src["id"])
    assert after_derived["analysis_run"]["id"] != run_id


def test_reposts_and_reports_on_invalidate_completed_run(client: TestClient, db):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-repost")
    other = add_text(client, "Reprint of the same event.", title="prov-target")
    first = analyze(client, src["id"])
    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.REPOSTS)
    db.commit()
    second = analyze(client, src["id"])
    assert second["analysis_run"]["id"] != first["analysis_run"]["id"]

    persist_source_edge(db, UUID(src["id"]), UUID(other["id"]), SourceEdgeRelationship.REPORTS_ON)
    db.commit()
    third = analyze(client, src["id"])
    assert third["analysis_run"]["id"] != second["analysis_run"]["id"]


def test_relational_digest_is_order_independent(db, client: TestClient):
    from sqlalchemy import delete

    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-digest")
    a = add_text(client, "Target A.", title="prov-da")
    b = add_text(client, "Target B.", title="prov-db")
    persist_source_edge(db, UUID(src["id"]), UUID(a["id"]), SourceEdgeRelationship.REPOSTS)
    persist_source_edge(db, UUID(src["id"]), UUID(b["id"]), SourceEdgeRelationship.DERIVED_FROM)
    db.commit()
    ids = [UUID(src["id"])]
    forward = analysis_relational_context_digest(db, ids)

    db.execute(delete(SourceEdge).where(SourceEdge.source_id == UUID(src["id"])))
    db.commit()
    persist_source_edge(db, UUID(src["id"]), UUID(b["id"]), SourceEdgeRelationship.DERIVED_FROM)
    persist_source_edge(db, UUID(src["id"]), UUID(a["id"]), SourceEdgeRelationship.REPOSTS)
    db.commit()
    reverse = analysis_relational_context_digest(db, ids)
    assert forward == reverse
    assert forward != analysis_relational_context_digest(db, [])


def test_runtime_only_change_reschedules_same_analysis_run(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-runtime")
    first = analyze(client, src["id"])
    planned = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "camera-ready",
                "interruptibility": "LOW",
                "cognitive_capacity": "LOW",
            },
        },
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["analysis_run"]["id"] == first["analysis_run"]["id"]
    assert body["attention_plan"]["id"] != first["attention_plan"]["id"]


def test_legacy_missing_cognitive_impact_reschedule_is_none_not_open_new(client: TestClient, db):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-legacy-impact")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]
    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    plan = dict(payload.get("attention_plan") or {})
    debug = dict(plan.get("score_debug") or {})
    debug.pop("cognitive_impact", None)
    debug["features"] = {
        **(debug.get("features") or {}),
        "exploration_candidate": True,
        "kernel_delta": 0.95,
        "change_magnitude": 0.2,
        "disagreement": 0.9,
        "sources_conflict": True,
    }
    plan["score_debug"] = debug
    payload["attention_plan"] = plan
    payload.pop("cognitive_impact", None)
    feat = dict(payload.get("features") or {})
    feat.update(
        {
            "exploration_candidate": True,
            "kernel_delta": 0.95,
            "change_magnitude": 0.2,
            "disagreement": 0.9,
            "sources_conflict": True,
        }
    )
    payload["features"] = feat
    planted = deepcopy(payload)
    run.result_payload = payload
    flag_modified(run, "result_payload")
    plan_row = db.get(AttentionPlan, UUID(str(first["attention_plan"]["id"])))
    plan_row.score_debug = debug
    flag_modified(plan_row, "score_debug")
    db.commit()

    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "later"}},
    )
    assert planned.status_code == 200, planned.text
    update = planned.json().get("update") or {}
    latest = planned.json()["attention_plan"]["update"] or {}
    assert update.get("operation") is None
    assert latest.get("operation") is None
    stored = db.get(AnalysisRun, UUID(str(run_id)))
    assert stored.result_payload == planted
    assert stored.result_payload.get("cognitive_impact") is None
    assert "cognitive_impact" not in ((stored.result_payload.get("attention_plan") or {}).get("score_debug") or {})


def test_drop_does_not_rewrite_reinforce_delta(client: TestClient, db):
    index = kernel_index(client)
    m1 = index["M1"]["id"]
    src = add_text(client, "A technical paper about motor intelligence latency.", title="prov-drop-dt")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]
    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    frozen_payload = deepcopy(payload)
    debug = dict((payload.get("attention_plan") or {}).get("score_debug") or {})
    debug["matches"] = [
        {
            "node_id": m1,
            "node_type": "MODEL",
            "title": "Motor Intelligence",
            "score": 0.9,
            "reason": "locate M1",
            "structural": False,
            "relevance_type": "TOPIC",
        }
    ]
    debug["cognitive_impact"] = {
        "effects": [
            {
                "target_kernel_node_id": m1,
                "operation": "REINFORCE",
                "target_node_type": "MODEL",
                "change_magnitude": 0.9,
                "epistemic_strength": 0.6,
                "target_importance": 0.8,
                "reason": "strengthens M1",
                "exploration_candidate": False,
            }
        ]
    }
    plan_blob = dict(payload.get("attention_plan") or {})
    plan_blob["score_debug"] = debug
    payload["attention_plan"] = plan_blob
    payload["cognitive_impact"] = debug["cognitive_impact"]
    payload["update"] = {"operation": "REINFORCE", "target_node_id": m1}
    feat = dict(payload.get("features") or {})
    feat["is_duplicate"] = True
    payload["features"] = feat
    payload["model_delta"] = {
        "summary": "Downstream synthesis skipped because current AttentionPlan is DROP.",
        "admission_allowed": False,
        "rationale": "Attention Policy routed DROP. Canonical Δ_t is unchanged.",
    }
    run.result_payload = payload
    flag_modified(run, "result_payload")
    plan_row = db.get(AttentionPlan, UUID(str(first["attention_plan"]["id"])))
    plan_row.score_debug = debug
    flag_modified(plan_row, "score_debug")
    db.commit()

    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "later"}},
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["attention_plan"]["disposition"] == "DROP"
    assert public_update(body["update"]) == {"operation": "REINFORCE", "target_node_id": m1}
    assert public_update(body["attention_plan"]["update"]) == {"operation": "REINFORCE", "target_node_id": m1}
    assert body["delta_content"] == ""
    assert body["attention_plan"]["delta_content"] == ""
    first_patch_ids = {p["id"] for p in (first.get("kernel_patches") or [])}
    body_patch_ids = {p["id"] for p in (body.get("kernel_patches") or [])}
    assert body_patch_ids == first_patch_ids
    stored = db.get(AnalysisRun, UUID(str(run_id)))
    summary = ((stored.result_payload or {}).get("model_delta") or {}).get("summary") or ""
    low = summary.lower()
    assert "no material cognitive" not in low
    assert "no cognitive value" not in low
    assert "no cognitive change" not in low
    assert stored.result_payload["update"] == payload["update"]
    assert stored.result_payload.get("cognitive_impact") == payload.get("cognitive_impact")
    assert frozen_payload.get("attention_plan", {}).get("id") == stored.result_payload.get("attention_plan", {}).get("id")


def test_fresh_drop_model_delta_does_not_deny_cognition(client: TestClient, db):
    original = add_text(client, "A technical paper about motor intelligence latency.", title="prov-drop-orig")
    copy = add_text(client, "A technical paper about motor intelligence latency.", title="prov-drop-copy")
    persist_source_edge(db, UUID(copy["id"]), UUID(original["id"]), SourceEdgeRelationship.REPOSTS)
    db.commit()
    result = analyze(client, copy["id"], extra_ids=[original["id"]])
    assert result["disposition"] == "DROP"
    summary = ((result.get("model_delta") or {}).get("summary") or "").lower()
    assert "no material cognitive" not in summary
    assert "no cognitive value" not in summary
    assert "downstream synthesis skipped" in summary
    assert result.get("kernel_patches") == []
