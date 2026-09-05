"""Attention Policy contract: Δ is cognitive authority; ExpectedOutput authorizes execution."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.enums import CognitiveEffectKind, Disposition, ExpectedOutput, Urgency
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import PlanDraft, RuntimeView, SchedulerFeatures, route, validate_plan
from tests.conftest import add_text, analyze


def _features(**overrides) -> SchedulerFeatures:
    base = dict(
        topic_relevance=0.9,
        structural_relevance=0.1,
        decision_relevance=0.2,
        novelty=0.65,
        credibility=0.8,
        kernel_delta=0.1,
        bottleneck_alignment=0.1,
        disagreement=0.0,
        actionability=0.4,
        temporal_value=0.4,
        cognitive_cost=8.0,
        evidence_maturity=0.6,
        high_quality_technical=True,
        foundational_paper=True,
        threatens_active_work=True,
        exploration_candidate=True,
        change_magnitude=0.0,
        epistemic_strength=0.0,
        target_importance=0.0,
    )
    base.update(overrides)
    return SchedulerFeatures(**base)


def _match(node_type: str = "MODEL") -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=node_type,
        score=0.8,
        reason="test",
        structural=node_type == "DECISION",
        relevance_type="STRUCTURAL" if node_type == "DECISION" else "TOPIC",
    )


def _effect(match: KernelMatch | None, kind: CognitiveEffectKind, **overrides) -> CognitiveEffect:
    base = dict(
        target_kernel_node_id=match.node_id if match else None,
        operation=kind,
        change_magnitude=0.75,
        epistemic_strength=0.4,
        target_importance=0.75,
        reason="test effect",
        exploration_candidate=kind == CognitiveEffectKind.OPEN_NEW,
        target_node_type=match.node_type if match is not None else None,
    )
    base.update(overrides)
    return CognitiveEffect(**base)


def _assessment(*effects: CognitiveEffect, **kwargs) -> CognitiveImpactAssessment:
    explore = kwargs.pop("exploration_candidate", any(e.exploration_candidate for e in effects))
    return CognitiveImpactAssessment(
        effects=list(effects),
        attention_cost=8.0,
        exploration_candidate=explore,
    )


def test_none_delta_is_drop_despite_topic_quality_and_threat():
    plan = route(
        _features(),
        assessment=_assessment(exploration_candidate=True),
    )
    assert plan.disposition == Disposition.DROP
    assert plan.expected_output == ExpectedOutput.NONE
    assert plan.urgency != Urgency.PREEMPT


def test_material_delta_plus_threat_keeps_disposition_and_raises_preempt():
    match = _match("MODEL")
    assessment = _assessment(_effect(match, CognitiveEffectKind.REINFORCE))
    plan = route(
        _features(threatens_active_work=True, high_quality_technical=False, foundational_paper=False),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE
    assert plan.expected_output == ExpectedOutput.KERNEL_PATCH
    assert plan.urgency == Urgency.PREEMPT
    assert "preempt" in plan.reason.lower() or "interrupt" in plan.reason.lower()


def test_material_delta_tight_deadline_defers_engage_to_watch():
    match = _match("MODEL")
    assessment = _assessment(_effect(match, CognitiveEffectKind.REINFORCE))
    plan = route(
        _features(threatens_active_work=False, high_quality_technical=False, foundational_paper=False),
        RuntimeView(deadline_minutes=60, interruptibility="LOW"),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.WATCH
    assert plan.expected_output == ExpectedOutput.WATCH
    assert plan.urgency == Urgency.BACKGROUND


def test_deadline_cannot_invent_watch_from_none_delta():
    plan = route(
        _features(threatens_active_work=False),
        RuntimeView(deadline_minutes=60, interruptibility="LOW"),
        assessment=_assessment(),
    )
    assert plan.disposition == Disposition.DROP
    assert plan.expected_output == ExpectedOutput.NONE


def test_exploration_candidate_without_open_new_is_not_attention_authority():
    match = _match("PROJECT")
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.05, epistemic_strength=0.1),
        exploration_candidate=True,
    )
    # Untargeted/illegal weak REINFORCE is normalized away; leftover flag is not OPEN_NEW.
    empty = _assessment(exploration_candidate=True)
    plan = route(_features(exploration_candidate=True), assessment=empty, matches=[match])
    assert plan.disposition == Disposition.DROP
    assert plan.expected_output == ExpectedOutput.NONE


def _force_route(disposition: Disposition, expected: ExpectedOutput):
    def _forced(*_a, **_k):
        return validate_plan(
            PlanDraft(
                disposition=disposition,
                expected_output=expected,
                reason="forced authorization test",
                watch_triggers=["NEW_EVIDENCE"] if expected == ExpectedOutput.WATCH else [],
                cognitive_budget_minutes=1,
            )
        )

    return _forced


def test_summary_does_not_create_kernel_patch(client: TestClient, monkeypatch):
    monkeypatch.setattr("app.services.pipeline.route", _force_route(Disposition.AWARE, ExpectedOutput.SUMMARY))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="auth-summary")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "SUMMARY"
    assert result["kernel_patches"] == []


def test_watch_does_not_create_kernel_patch(client: TestClient, monkeypatch):
    monkeypatch.setattr("app.services.pipeline.route", _force_route(Disposition.WATCH, ExpectedOutput.WATCH))
    src = add_text(client, "A technical paper about motor intelligence latency.", title="auth-watch")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "WATCH"
    assert result["kernel_patches"] == []


def test_kernel_patch_expected_output_may_propose_patches(client: TestClient, monkeypatch):
    monkeypatch.setattr("app.services.pipeline.route", _force_route(Disposition.ENGAGE, ExpectedOutput.KERNEL_PATCH))
    src = add_text(
        client,
        """A high-quality technical paper on arXiv argues the opposite of the belief that large
        unified models may be unsuitable for the fastest embodied-control loop.""",
        title="auth-patch",
    )
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "KERNEL_PATCH"
    assert result["kernel_patches"]
    assert all(p["status"] == "PROPOSED" for p in result["kernel_patches"])


def test_decision_review_fail_closed_is_not_generic_patch(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.route", _force_route(Disposition.ENGAGE, ExpectedOutput.DECISION_REVIEW)
    )
    src = add_text(client, "A technical paper about motor intelligence latency.", title="auth-decision")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "DECISION_REVIEW"
    assert result["kernel_patches"] == []
    rationale = (result["model_delta"].get("rationale") or "").lower()
    assert "fail closed" in rationale
    assert "decision_review" in rationale


def test_experiment_proposal_fail_closed_is_not_generic_patch(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.pipeline.route", _force_route(Disposition.ENGAGE, ExpectedOutput.EXPERIMENT_PROPOSAL)
    )
    src = add_text(client, "A technical paper about motor intelligence latency.", title="auth-experiment")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["expected_output"] == "EXPERIMENT_PROPOSAL"
    assert result["kernel_patches"] == []
    rationale = (result["model_delta"].get("rationale") or "").lower()
    assert "fail closed" in rationale
    assert "experiment_proposal" in rationale


def test_duplicate_none_delta_still_drops():
    plan = route(_features(is_duplicate=True), assessment=_assessment())
    assert plan.disposition == Disposition.DROP
    assert plan.expected_output == ExpectedOutput.NONE


def test_duplicate_cannot_drop_material_reinforce():
    match = _match("MODEL")
    assessment = _assessment(_effect(match, CognitiveEffectKind.REINFORCE))
    plan = route(
        _features(is_duplicate=True, threatens_active_work=False),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition != Disposition.DROP
    assert plan.expected_output != ExpectedOutput.NONE


def test_duplicate_cannot_drop_material_challenge():
    match = _match("BELIEF")
    assessment = _assessment(_effect(match, CognitiveEffectKind.CHALLENGE))
    plan = route(
        _features(is_duplicate=True, threatens_active_work=False),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition != Disposition.DROP
    assert plan.expected_output != ExpectedOutput.NONE


def test_duplicate_open_new_follows_normal_open_new_policy():
    effect = _effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.6, target_importance=0.6)
    assessment = _assessment(effect)
    baseline = route(_features(is_duplicate=False), assessment=assessment)
    duplicate = route(_features(is_duplicate=True), assessment=assessment)
    assert baseline.disposition != Disposition.DROP
    assert duplicate.disposition == baseline.disposition
    assert duplicate.expected_output == baseline.expected_output


def test_duplicate_relation_stays_in_impact_provenance(client: TestClient, db):
    from uuid import UUID

    from app.enums import SourceEdgeRelationship
    from app.services.source_graph import persist_source_edge

    original = add_text(client, "A technical paper about motor intelligence latency.", title="dup-prov-orig")
    copy = add_text(client, "A technical paper about motor intelligence latency.", title="dup-prov-copy")
    persist_source_edge(db, UUID(copy["id"]), UUID(original["id"]), SourceEdgeRelationship.REPOSTS)
    db.commit()
    result = analyze(client, copy["id"], extra_ids=[original["id"]])
    independence = ((result.get("relational_context") or {}).get("independence") or {})
    impact_ind = ((result.get("impact_input") or {}).get("independence") or {})
    debug_ind = ((result.get("attention_plan") or {}).get("score_debug") or {}).get("independence") or {}
    assert result["features"]["is_duplicate"] is True
    assert independence.get("is_duplicate") is True
    assert impact_ind.get("is_duplicate") is True
    assert result["features"]["independent_source_count"] == 1
    assert int(result["features"]["secondary_report_count"] or 0) >= 1
    assert int(independence.get("independent_sources") or debug_ind.get("independent_sources") or 0) == 1
    assert int(independence.get("secondary_reports") or debug_ind.get("secondary_reports") or 0) >= 1


def test_reschedule_frozen_reinforce_is_not_duplicate_hard_drop(client: TestClient, db):
    from sqlalchemy.orm.attributes import flag_modified

    from app.models.analysis import AnalysisRun
    from app.models.scheduler import AttentionPlan
    from tests.conftest import kernel_index

    index = kernel_index(client)
    m1 = index["M1"]["id"]
    src = add_text(client, "A technical paper about motor intelligence latency.", title="dup-reschedule")
    first = analyze(client, src["id"])
    run = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    payload = dict(run.result_payload or {})
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
    feat = dict(payload.get("features") or {})
    feat["is_duplicate"] = True
    payload["features"] = feat
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
    assert body["attention_plan"]["disposition"] != "DROP"
    db.expire_all()
    stored = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    assert stored.result_payload == payload
    assert stored.result_payload.get("cognitive_impact") == debug["cognitive_impact"]
