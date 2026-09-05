"""Reschedule executes ExpectedOutput; WATCH creates a real obligation."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import attributes as sa_attributes

from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.enums import Disposition, ExpectedOutput
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelPatch
from app.models.watch import Watch
from app.services.scheduler import PlanDraft, validate_plan
from tests.conftest import add_text, analyze

PATCH_SOURCE = """A high-quality technical paper on arXiv argues the opposite of the belief that large
unified models may be unsuitable for the fastest embodied-control loop.
It argues that large unified models are necessary for high-frequency embodied motor control."""


def _force_route(
    disposition: Disposition,
    expected: ExpectedOutput,
    *,
    watch_after_processing: bool = False,
):
    def _forced(*_a, **_k):
        return validate_plan(
            PlanDraft(
                disposition=disposition,
                expected_output=expected,
                reason="forced attention plan execution test",
                watch_after_processing=watch_after_processing,
                watch_triggers=["NEW_EVIDENCE", "PAPER_RELEASE"]
                if watch_after_processing or expected == ExpectedOutput.WATCH
                else [],
                cognitive_budget_minutes=1,
            )
        )

    return _forced


def test_reschedule_watch_to_kernel_patch_uses_frozen_run(client: TestClient, db, monkeypatch):
    counts = {"extract": 0, "match": 0, "assess": 0}
    import app.services.pipeline as pipeline_mod

    original_extract = pipeline_mod.extract_source
    original_match = RuleBasedCognitiveProvider.match_kernel
    original_assess = RuleBasedCognitiveProvider.assess_cognitive_impact

    def counting_extract(*args, **kwargs):
        counts["extract"] += 1
        return original_extract(*args, **kwargs)

    def counting_match(self, *args, **kwargs):
        counts["match"] += 1
        return original_match(self, *args, **kwargs)

    def counting_assess(self, *args, **kwargs):
        counts["assess"] += 1
        return original_assess(self, *args, **kwargs)

    monkeypatch.setattr(pipeline_mod, "extract_source", counting_extract)
    monkeypatch.setattr(RuleBasedCognitiveProvider, "match_kernel", counting_match)
    monkeypatch.setattr(RuleBasedCognitiveProvider, "assess_cognitive_impact", counting_assess)
    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    src = add_text(client, PATCH_SOURCE, title="rs-w2p")
    first = analyze(client, src["id"])
    assert first["attention_plan"]["expected_output"] == "WATCH"
    assert first["kernel_patches"] == []
    after_first = dict(counts)
    run = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    planted = deepcopy(run.result_payload)

    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.ENGAGE, ExpectedOutput.KERNEL_PATCH))
    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "later"}},
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["attention_plan"]["id"] != first["attention_plan"]["id"]
    assert body["attention_plan"]["expected_output"] == "KERNEL_PATCH"
    assert body["authorized_kernel_patches"]
    assert all(p["status"] == "PROPOSED" for p in body["authorized_kernel_patches"])
    assert all(
        p["attention_plan_id"] == body["attention_plan"]["id"] for p in body["authorized_kernel_patches"]
    )
    assert counts == after_first
    db.expire_all()
    run = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    assert run.result_payload == planted
    assert not sa_attributes.get_history(run, "result_payload").has_changes()
    new_plan_id = UUID(body["attention_plan"]["id"])
    owned = db.execute(select(KernelPatch).where(KernelPatch.attention_plan_id == new_plan_id)).scalars().all()
    assert owned


def test_reschedule_kernel_patch_to_watch_keeps_old_patches(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.ENGAGE, ExpectedOutput.KERNEL_PATCH))
    src = add_text(client, PATCH_SOURCE, title="rs-p2w")
    first = analyze(client, src["id"])
    old_ids = {p["id"] for p in first["kernel_patches"]}
    assert old_ids
    planted = deepcopy(db.get(AnalysisRun, UUID(first["analysis_run"]["id"])).result_payload)

    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "later"}},
    )
    assert planned.status_code == 200, planned.text
    body = planned.json()
    assert body["attention_plan"]["expected_output"] == "WATCH"
    assert body["authorized_kernel_patches"] == []
    assert body["authorized_watches"]
    db.expire_all()
    run = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    assert run.result_payload == planted
    assert {p["id"] for p in (run.result_payload.get("kernel_patches") or [])} == old_ids
    for pid in old_ids:
        row = db.get(KernelPatch, UUID(pid))
        assert row is not None
        assert row.status == "PROPOSED"
    new_plan_id = UUID(body["attention_plan"]["id"])
    assert db.execute(select(Watch).where(Watch.attention_plan_id == new_plan_id)).scalars().all()
    new_patches = db.execute(select(KernelPatch).where(KernelPatch.attention_plan_id == new_plan_id)).scalars().all()
    assert new_patches == []
    assert not sa_attributes.get_history(run, "result_payload").has_changes()


def test_watch_creates_obligation_even_when_heuristic_is_empty(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "suggest_watches", lambda *_a, **_k: [])
    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="watch-empty")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "WATCH"
    plan_id = UUID(result["attention_plan"]["id"])
    watches = db.execute(select(Watch).where(Watch.attention_plan_id == plan_id)).scalars().all()
    assert len(watches) >= 1
    assert watches[0].triggers
    artifacts = (result["attention_plan"].get("score_debug") or {}).get("authorized_artifacts") or {}
    assert artifacts.get("policy_authorized_watch") is True
    assert artifacts.get("explicit_watch_override") is False
    assert all(w.target_ref != "heuristic-should-not-win" for w in watches)


def test_watch_plus_persist_flag_still_uses_plan_obligation_not_heuristic(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(
        pipeline_mod,
        "suggest_watches",
        lambda *_a, **_k: [
            {
                "target_type": "METHOD",
                "target_ref": "heuristic-should-not-win",
                "created_reason": "heuristic",
                "triggers": ["CODE_RELEASE"],
            }
        ],
    )
    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="watch-not-override")
    result = analyze(client, src["id"], persist_watches=True)
    plan_id = UUID(result["attention_plan"]["id"])
    watches = db.execute(select(Watch).where(Watch.attention_plan_id == plan_id)).scalars().all()
    assert len(watches) >= 1
    assert all(w.target_ref != "heuristic-should-not-win" for w in watches)
    artifacts = (result["attention_plan"].get("score_debug") or {}).get("authorized_artifacts") or {}
    assert artifacts.get("policy_authorized_watch") is True
    assert artifacts.get("explicit_watch_override") is False


def test_none_and_summary_do_not_auto_create_watches(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    heuristic = [
        {
            "target_type": "METHOD",
            "target_ref": "should-not-persist",
            "created_reason": "heuristic",
            "triggers": ["PAPER_RELEASE"],
        }
    ]
    monkeypatch.setattr(pipeline_mod, "suggest_watches", lambda *_a, **_k: heuristic)
    for disposition, expected in (
        (Disposition.DROP, ExpectedOutput.NONE),
        (Disposition.AWARE, ExpectedOutput.SUMMARY),
    ):
        monkeypatch.setattr(pipeline_mod, "route", _force_route(disposition, expected))
        src = add_text(
            client,
            "A technical paper about motor intelligence latency.",
            title=f"no-watch-{expected.value}",
        )
        result = analyze(client, src["id"])
        plan_id = UUID(result["attention_plan"]["id"])
        watches = db.execute(select(Watch).where(Watch.attention_plan_id == plan_id)).scalars().all()
        assert watches == []


def test_persist_suggested_watches_is_explicit_override(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    heuristic = [
        {
            "target_type": "METHOD",
            "target_ref": "override-watch",
            "created_reason": "explicit caller override",
            "triggers": ["CODE_RELEASE"],
        }
    ]
    monkeypatch.setattr(pipeline_mod, "suggest_watches", lambda *_a, **_k: heuristic)
    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.AWARE, ExpectedOutput.SUMMARY))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="watch-override")
    result = analyze(client, src["id"], persist_watches=True)
    assert result["attention_plan"]["expected_output"] == "SUMMARY"
    plan_id = UUID(result["attention_plan"]["id"])
    watches = db.execute(select(Watch).where(Watch.attention_plan_id == plan_id)).scalars().all()
    assert len(watches) == 1
    assert watches[0].target_ref == "override-watch"
    artifacts = (result["attention_plan"].get("score_debug") or {}).get("authorized_artifacts") or {}
    assert artifacts.get("explicit_watch_override") is True
    assert artifacts.get("policy_authorized_watch") is False


def _watches_for_plan(db, plan_id: UUID) -> list[Watch]:
    return db.execute(select(Watch).where(Watch.attention_plan_id == plan_id)).scalars().all()


def test_kernel_patch_with_watch_after_processing_creates_patch_and_watch(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(
        pipeline_mod,
        "route",
        _force_route(Disposition.ENGAGE, ExpectedOutput.KERNEL_PATCH, watch_after_processing=True),
    )
    src = add_text(client, PATCH_SOURCE, title="patch-then-watch")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "KERNEL_PATCH"
    assert result["attention_plan"]["watch_after_processing"] is True
    assert result["kernel_patches"]
    assert all(p["status"] == "PROPOSED" for p in result["kernel_patches"])
    watches = _watches_for_plan(db, UUID(result["attention_plan"]["id"]))
    assert len(watches) >= 1
    artifacts = (result["attention_plan"].get("score_debug") or {}).get("authorized_artifacts") or {}
    assert artifacts.get("policy_authorized_watch") is True
    assert artifacts.get("explicit_watch_override") is False
    planted = deepcopy(db.get(AnalysisRun, UUID(result["analysis_run"]["id"])).result_payload)
    db.expire_all()
    run = db.get(AnalysisRun, UUID(result["analysis_run"]["id"]))
    assert run.result_payload == planted


def test_kernel_patch_without_watch_after_processing_creates_no_watch(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(
        pipeline_mod,
        "suggest_watches",
        lambda *_a, **_k: [
            {
                "target_type": "METHOD",
                "target_ref": "should-not-persist",
                "created_reason": "heuristic",
                "triggers": ["PAPER_RELEASE"],
            }
        ],
    )
    monkeypatch.setattr(
        pipeline_mod,
        "route",
        _force_route(Disposition.ENGAGE, ExpectedOutput.KERNEL_PATCH, watch_after_processing=False),
    )
    src = add_text(client, PATCH_SOURCE, title="patch-no-watch")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "KERNEL_PATCH"
    assert result["attention_plan"]["watch_after_processing"] is False
    assert result["kernel_patches"]
    assert _watches_for_plan(db, UUID(result["attention_plan"]["id"])) == []


def test_summary_with_watch_after_processing_creates_watch(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "suggest_watches", lambda *_a, **_k: [])
    monkeypatch.setattr(
        pipeline_mod,
        "route",
        _force_route(Disposition.AWARE, ExpectedOutput.SUMMARY, watch_after_processing=True),
    )
    src = add_text(client, "A technical paper about motor intelligence latency.", title="summary-then-watch")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "SUMMARY"
    assert result["attention_plan"]["watch_after_processing"] is True
    assert result["kernel_patches"] == []
    assert result.get("model_delta")
    watches = _watches_for_plan(db, UUID(result["attention_plan"]["id"]))
    assert len(watches) >= 1


def test_watch_expected_output_implies_watch_after_processing(client: TestClient, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "suggest_watches", lambda *_a, **_k: [])
    monkeypatch.setattr(pipeline_mod, "route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="watch-primary")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "WATCH"
    assert result["attention_plan"]["watch_after_processing"] is True
    assert result["kernel_patches"] == []
    watches = _watches_for_plan(db, UUID(result["attention_plan"]["id"]))
    assert len(watches) >= 1
