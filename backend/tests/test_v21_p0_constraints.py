"""v2.1 frozen invariants: Location ≠ Update, Δ_t as unique transition truth."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm.attributes import flag_modified

from app.enums import ClaimType, CognitiveEffectKind, PatchChangeType
from app.models.analysis import AnalysisRun
from app.models.kernel import KernelNode
from app.services.cognitive_impact import (
    LOCATION_NODE_TYPES,
    UPDATE_ELIGIBLE_NODE_TYPES,
    CognitiveEffect,
    CognitiveImpactAssessment,
    assessment_from_dict,
    bind_legacy_target_types,
    canonical_delta_content,
    ground_effects,
    is_location_node,
    is_update_eligible_node,
    normalize_frozen_transition,
    primary_update,
    select_primary_effect,
    visible_delta_content,
)
from app.services.deltas import (
    ModelDelta,
    PatchDraft,
    LEGAL_NODE_STATUSES,
    model_delta_from_transition,
    patch_consistent_with_update,
    proposed_state_is_legal,
    propose_patches,
)
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.matching import KernelMatch, match_kernel
from app.services.scheduler import SchedulerFeatures


def _match(node_type: str, title: str | None = None, score: float = 0.9) -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=title or node_type,
        score=score,
        reason="test locate",
        relevance_type="TOPIC",
    )


def _effect(match: KernelMatch | None, kind: CognitiveEffectKind, **overrides) -> CognitiveEffect:
    base = dict(
        target_kernel_node_id=match.node_id if match else None,
        operation=kind,
        change_magnitude=0.8,
        epistemic_strength=0.4,
        target_importance=0.75,
        reason="test effect",
        exploration_candidate=kind == CognitiveEffectKind.OPEN_NEW,
        target_node_type=match.node_type if match is not None else None,
    )
    base.update(overrides)
    return CognitiveEffect(**base)


def _extraction(*texts: str) -> ExtractionResult:
    claims = [ExtractedClaim(text=t, claim_type=ClaimType.TECHNICAL) for t in texts]
    return ExtractionResult(claims=claims, technical_claims=list(texts), evidence_maturity=0.5)


def _features() -> SchedulerFeatures:
    return SchedulerFeatures(
        topic_relevance=0.7,
        structural_relevance=0.1,
        decision_relevance=0.2,
        novelty=0.6,
        credibility=0.7,
        kernel_delta=0.7,
        bottleneck_alignment=0.2,
        disagreement=0.1,
        actionability=0.4,
        temporal_value=0.4,
        cognitive_cost=8.0,
        evidence_maturity=0.5,
        change_magnitude=0.7,
        epistemic_strength=0.4,
        target_importance=0.7,
        attention_cost=8.0,
    )


def _node(match: KernelMatch, payload: dict | None = None) -> KernelNode:
    node = KernelNode(
        node_type=match.node_type,
        title=match.title,
        status="ACTIVE",
        payload=payload or {"proposition": match.title, "confidence": 0.5},
        current_version=1,
    )
    node.id = match.node_id
    return node


def test_location_and_update_eligible_types_are_disjoint():
    assert LOCATION_NODE_TYPES.isdisjoint(UPDATE_ELIGIBLE_NODE_TYPES)
    for kind in ("GOAL", "PROJECT"):
        assert is_location_node(kind)
        assert not is_update_eligible_node(kind)
    for kind in ("BELIEF", "MODEL", "QUESTION", "HYPOTHESIS", "DECISION", "BOTTLENECK"):
        assert is_update_eligible_node(kind)
        assert not is_location_node(kind)


def test_locate_may_hit_goal_and_project():
    goal = KernelNode(node_type="GOAL", title="Build better motor control", status="ACTIVE", payload={})
    project = KernelNode(node_type="PROJECT", title="Motor Intelligence", status="ACTIVE", payload={})
    goal.id = uuid4()
    project.id = uuid4()
    extraction = _extraction("A motor control paper on temporal intelligence.")
    matches = match_kernel(extraction, [goal, project], extra_text="motor control temporal intelligence")
    located = {m.node_type for m in matches}
    assert "GOAL" in located or "PROJECT" in located


def test_grounding_discards_location_reinforce_even_when_scope_overlaps():
    project = _match("PROJECT", "Motor Intelligence temporal control")
    extraction = _extraction("A paper on motor intelligence and temporal control.")
    raw = [_effect(project, CognitiveEffectKind.REINFORCE, reason="same project topic")]
    grounded = ground_effects(raw, [project], extraction, independent_source_count=1)
    assert grounded == []
    assert primary_update(CognitiveImpactAssessment(effects=grounded))["operation"] is None


def test_grounding_discards_goal_challenge():
    goal = _match("GOAL", "Build better embodied intelligence")
    extraction = _extraction("Embodied intelligence claims are overstated.")
    raw = [_effect(goal, CognitiveEffectKind.CHALLENGE)]
    grounded = ground_effects(raw, [goal], extraction, independent_source_count=2)
    assert grounded == []


def test_update_eligible_types_remain_legal_targets():
    extraction = _extraction("Latency evaluation must split energy and task-success.")
    for kind in ("BELIEF", "MODEL", "QUESTION", "HYPOTHESIS", "DECISION", "BOTTLENECK"):
        match = _match(kind, "Latency evaluation of energy and task-success")
        raw = [_effect(match, CognitiveEffectKind.REINFORCE)]
        grounded = ground_effects(raw, [match], extraction, independent_source_count=2)
        assert grounded, kind
        update = primary_update(CognitiveImpactAssessment(effects=grounded))
        assert update["operation"] == CognitiveEffectKind.REINFORCE
        assert update["target_node_id"] == str(match.node_id)


def test_public_update_cannot_select_location_node():
    project = _match("PROJECT")
    model = _match("MODEL", "Separable temporal motor intelligence")
    extraction = _extraction("Evidence supports a temporal motor intelligence split.")
    raw = [
        _effect(project, CognitiveEffectKind.REINFORCE, change_magnitude=0.99, target_importance=0.99),
        _effect(model, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, target_importance=0.75),
    ]
    grounded = ground_effects(raw, [project, model], extraction, independent_source_count=2)
    update = primary_update(CognitiveImpactAssessment(effects=grounded))
    assert update["target_node_id"] == str(model.node_id)
    assert update["operation"] == CognitiveEffectKind.REINFORCE


def test_challenge_patch_revises_delta_target_only():
    model = _match("MODEL", "Existing model M1")
    other = _match("QUESTION", "Unrelated question")
    node = _node(model)
    unused = _node(other)
    assessment = CognitiveImpactAssessment(
        effects=[
            _effect(
                model,
                CognitiveEffectKind.CHALLENGE,
                reason="Source contests M1 at matching scope.",
                target_node_type="MODEL",
            )
        ]
    )
    stray = ModelDelta(
        summary="ignore",
        questions=["Should we open a new question about something else?"],
        distinctions=["cognitive vs motor"],
    )
    drafts = propose_patches(
        "scale differently cognitive motor",
        stray,
        [model, other],
        _features(),
        [node, unused],
        [],
        assessment=assessment,
        extraction=_extraction("Direct evidence that M1 is too strong as stated."),
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.change_type == PatchChangeType.REVISE
    assert draft.target_object_id == model.node_id
    assert draft.target_object_type.value == "MODEL"
    assert patch_consistent_with_update(draft, primary_update(assessment))


def test_open_new_patch_is_create_without_existing_target():
    project = _match("PROJECT", "Motor Intelligence")
    assessment = CognitiveImpactAssessment(
        effects=[
            _effect(
                None,
                CognitiveEffectKind.OPEN_NEW,
                reason="No existing Kernel node captures this branch.",
            )
        ]
    )
    stray = ModelDelta(
        summary="old heuristic",
        questions=["A precise new research question?"],
        distinctions=["scale differently"],
    )
    drafts = propose_patches(
        "scale differently",
        stray,
        [project],
        _features(),
        [_node(project)],
        [],
        assessment=assessment,
        extraction=_extraction("A new architecture paper introduces an abstraction."),
    )
    assert len(drafts) == 1
    assert drafts[0].change_type == PatchChangeType.CREATE
    assert drafts[0].target_object_id is None
    assert patch_consistent_with_update(drafts[0], primary_update(assessment))


def test_none_delta_does_not_emit_heuristic_patches():
    model = _match("MODEL")
    stray = ModelDelta(
        summary="would have created a model",
        questions=["At which layers?"],
        distinctions=["cognitive vs motor", "scale differently"],
    )
    drafts = propose_patches(
        "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.",
        stray,
        [model],
        _features(),
        [_node(model)],
        [],
        assessment=CognitiveImpactAssessment(effects=[]),
        extraction=_extraction("scale differently"),
    )
    assert drafts == []


def test_lexical_locate_has_no_domain_bonus_tables():
    import inspect

    import app.services.matching as matching

    for name in ("EQUITY_STRUCTURE", "EMBODIED_MOTOR", "COLLECTIVE"):
        assert not hasattr(matching, name)
    source = inspect.getsource(matching.match_kernel)
    assert "folding" not in source
    assert "humanoid" not in source
    assert "swarm" not in source
    assert "orbit" not in source


def test_propose_patches_without_delta_assessment_is_empty():
    model = _match("MODEL")
    stray = ModelDelta(summary="unbound prose", questions=["Open a new question?"], distinctions=["scale differently"])
    drafts = propose_patches(
        "scale differently",
        stray,
        [model],
        _features(),
        [_node(model)],
        [],
    )
    assert drafts == []


def test_select_primary_rejects_typed_location_effect_without_grounding():
    project = _match("PROJECT")
    leaked = _effect(project, CognitiveEffectKind.REINFORCE, target_node_type="PROJECT")
    assessment = CognitiveImpactAssessment(effects=[leaked])
    assert select_primary_effect(assessment) is None
    assert primary_update(assessment)["operation"] is None


def test_legacy_project_match_without_type_is_not_public_primary():
    project = _match("PROJECT")
    leaked = _effect(project, CognitiveEffectKind.REINFORCE, target_node_type=None, change_magnitude=0.95, target_importance=0.95)
    assessment = CognitiveImpactAssessment(effects=[leaked])
    assert leaked.target_node_type is None
    bound = bind_legacy_target_types(assessment, [project])
    assert assessment.effects[0].target_node_type is None
    assert bound is not assessment
    update = primary_update(bound)
    assert update["operation"] is None
    assert update["target_node_id"] is None


def test_legacy_model_match_without_type_restores_legal_target():
    model = _match("MODEL")
    leaked = _effect(model, CognitiveEffectKind.CHALLENGE, target_node_type=None, change_magnitude=0.8)
    assessment = CognitiveImpactAssessment(effects=[leaked])
    bound = bind_legacy_target_types(assessment, [model])
    assert assessment.effects[0].target_node_type is None
    update = primary_update(bound)
    assert update["operation"] == CognitiveEffectKind.CHALLENGE
    assert update["target_node_id"] == str(model.node_id)
    assert bound.effects[0].target_node_type == "MODEL"


def test_unverified_legacy_target_type_fail_closed():
    model = _match("MODEL")
    leaked = _effect(model, CognitiveEffectKind.REINFORCE, target_node_type=None, change_magnitude=0.9)
    assessment = CognitiveImpactAssessment(effects=[leaked])
    bound = bind_legacy_target_types(assessment, [])
    assert assessment.effects[0].target_node_type is None
    assert bound.effects[0].target_node_type is None
    assert select_primary_effect(bound) is None
    reconstructed = assessment_from_dict(
        {
            "effects": [
                {
                    "target_kernel_node_id": str(model.node_id),
                    "operation": "REINFORCE",
                    "change_magnitude": 0.9,
                    "epistemic_strength": 0.4,
                    "target_importance": 0.8,
                    "reason": "legacy untyped",
                }
            ]
        }
    )
    assert select_primary_effect(reconstructed) is None


def test_none_delta_prose_cannot_claim_a_cognitive_change():
    stray = ModelDelta(
        summary="This information challenges M1 and opens a new question.",
        distinctions=["a new cognitive split"],
        questions=["Should we create a model?"],
        what_could_change=["Kernel should change"],
    )
    bound = model_delta_from_transition(CognitiveImpactAssessment(effects=[]), prose=stray)
    assert bound.summary == canonical_delta_content(CognitiveImpactAssessment(effects=[]))
    assert "challenge" not in bound.summary.lower()
    assert bound.distinctions == []
    assert bound.questions == []
    assert bound.what_could_change == []
    assert bound.admission_allowed is False


def test_challenge_question_does_not_emit_contested_status():
    question = _match("QUESTION", "Open research question")
    node = _node(question, payload={"text": question.title})
    node.status = "OPEN"
    assessment = CognitiveImpactAssessment(
        effects=[_effect(question, CognitiveEffectKind.CHALLENGE, target_node_type="QUESTION")]
    )
    drafts = propose_patches(
        "source",
        ModelDelta(summary="ignore"),
        [question],
        _features(),
        [node],
        [],
        assessment=assessment,
        extraction=_extraction("The question should be reframed."),
    )
    assert drafts == []
    assert "CONTESTED" not in LEGAL_NODE_STATUSES["QUESTION"]


def test_challenge_decision_does_not_emit_contested_status():
    decision = _match("DECISION", "Pending decision")
    node = _node(decision, payload={"rationale": "pending"})
    node.status = "PENDING"
    assessment = CognitiveImpactAssessment(
        effects=[_effect(decision, CognitiveEffectKind.CHALLENGE, target_node_type="DECISION")]
    )
    drafts = propose_patches(
        "source",
        ModelDelta(summary="ignore"),
        [decision],
        _features(),
        [node],
        [],
        assessment=assessment,
        extraction=_extraction("The decision may need revisiting."),
    )
    assert drafts == []
    for draft in drafts:
        assert draft.proposed_state.get("status") != "CONTESTED"
        assert proposed_state_is_legal("DECISION", draft.proposed_state)


def test_reinforce_without_legal_proposed_state_emits_zero_patch():
    belief = _match("BELIEF")
    node = _node(belief, payload={"proposition": belief.title, "confidence": 0.68})
    assessment = CognitiveImpactAssessment(
        effects=[_effect(belief, CognitiveEffectKind.REINFORCE, target_node_type="BELIEF")]
    )
    drafts = propose_patches(
        "source",
        ModelDelta(summary="would have bumped confidence"),
        [belief],
        _features(),
        [node],
        [],
        assessment=assessment,
        extraction=_extraction("Supporting evidence at matching scope."),
    )
    assert drafts == []


def test_challenge_belief_revise_is_contested_without_confidence_heuristic():
    belief = _match("BELIEF")
    node = _node(belief, payload={"proposition": belief.title, "confidence": 0.68})
    assessment = CognitiveImpactAssessment(
        effects=[_effect(belief, CognitiveEffectKind.CHALLENGE, target_node_type="BELIEF")]
    )
    drafts = propose_patches(
        "source",
        ModelDelta(summary="ignore"),
        [belief],
        _features(),
        [node],
        [],
        assessment=assessment,
        extraction=_extraction("Direct counterevidence at matching scope."),
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.change_type == PatchChangeType.REVISE
    assert draft.proposed_state["status"] == "CONTESTED"
    assert draft.proposed_state["payload"].get("confidence") == 0.68
    assert draft.suggested_confidence_change is None
    assert proposed_state_is_legal("BELIEF", draft.proposed_state)
    assert patch_consistent_with_update(draft, primary_update(assessment))


def test_match_prompt_has_no_pilot_exemplars():
    from app.cognitive.prompts import DELTA_SYSTEM, EVIDENCE_SYSTEM, MATCH_SYSTEM

    blob = f"{MATCH_SYSTEM}\n{DELTA_SYSTEM}\n{EVIDENCE_SYSTEM}".lower()
    for token in ("equity", "motor intelligence", "humanoid", "folding", "swarm", "orbitbench", "move-pause-move"):
        assert token not in blob
    assert "structural" in MATCH_SYSTEM.lower()


def test_reschedule_legacy_project_target_is_not_public_update(client: TestClient, db):
    from tests.conftest import add_text, analyze, kernel_index

    index = kernel_index(client)
    src = add_text(client, "A technical paper about motor intelligence latency.", title="legacy-loc")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]
    project_id = index["P1"]["id"]
    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    plan = dict(payload.get("attention_plan") or {})
    debug = dict(plan.get("score_debug") or {})
    debug["matches"] = [
        {
            "node_id": project_id,
            "node_type": "PROJECT",
            "title": "Motor Intelligence",
            "score": 0.9,
            "reason": "legacy locate",
            "structural": False,
            "relevance_type": "TOPIC",
        }
    ]
    debug["cognitive_impact"] = {
        "effects": [
            {
                "target_kernel_node_id": project_id,
                "operation": "REINFORCE",
                "change_magnitude": 0.9,
                "epistemic_strength": 0.5,
                "target_importance": 0.8,
                "reason": "legacy location treated as update",
                "exploration_candidate": False,
            }
        ],
        "attention_cost": 8.0,
        "exploration_candidate": False,
    }
    plan["score_debug"] = debug
    payload["attention_plan"] = plan
    payload["cognitive_impact"] = debug["cognitive_impact"]
    run.result_payload = payload
    flag_modified(run, "result_payload")
    db.commit()

    planned = client.post("/scheduler/plan", json={"source_id": src["id"]})
    assert planned.status_code == 200, planned.text
    latest = planned.json()["attention_plan"]
    update = latest.get("update") or {}
    assert update.get("target_node_id") != project_id
    assert not (update.get("operation") == "REINFORCE" and update.get("target_node_id") == project_id)
    stored = client.get(f"/analysis/by-source/{src['id']}").json()
    assert stored["analysis_run"]["id"] == run_id
    assert stored["attention_plan"]["id"] == first["attention_plan"]["id"]
    assert stored["update"] == stored["latest_attention_plan"]["update"]


def test_frozen_project_overrides_persisted_model_type():
    project = _match("PROJECT")
    leaked = _effect(project, CognitiveEffectKind.REINFORCE, target_node_type="MODEL", change_magnitude=0.9)
    assessment = CognitiveImpactAssessment(effects=[leaked])
    norm = normalize_frozen_transition(assessment, [project])
    assert assessment.effects[0].target_node_type == "MODEL"
    assert norm.assessment.effects[0].target_node_type == "PROJECT"
    assert norm.update == {"operation": None, "target_node_id": None}


def test_persisted_model_without_frozen_match_fail_closed():
    target = uuid4()
    leaked = CognitiveEffect(
        target_kernel_node_id=target,
        operation=CognitiveEffectKind.REINFORCE,
        change_magnitude=0.9,
        epistemic_strength=0.5,
        target_importance=0.8,
        reason="payload claimed MODEL",
        target_node_type="MODEL",
    )
    assessment = CognitiveImpactAssessment(effects=[leaked])
    norm = normalize_frozen_transition(assessment, [])
    assert assessment.effects[0].target_node_type == "MODEL"
    assert norm.assessment.effects[0].target_node_type is None
    assert select_primary_effect(norm.assessment) is None
    assert norm.update == {"operation": None, "target_node_id": None}


def test_frozen_model_match_restores_wrong_or_missing_persisted_type():
    model = _match("MODEL")
    missing = _effect(model, CognitiveEffectKind.CHALLENGE, target_node_type=None, change_magnitude=0.8)
    wrong = _effect(model, CognitiveEffectKind.CHALLENGE, target_node_type="PROJECT", change_magnitude=0.8)
    for leaked in (missing, wrong):
        assessment = CognitiveImpactAssessment(effects=[leaked])
        norm = normalize_frozen_transition(assessment, [model])
        assert leaked.target_node_type != "MODEL" or leaked.target_node_type is None
        assert assessment.effects[0].target_node_type == leaked.target_node_type
        assert norm.assessment.effects[0].target_node_type == "MODEL"
        assert norm.update["operation"] == "CHALLENGE"
        assert norm.update["target_node_id"] == str(model.node_id)


def test_visible_delta_content_none_respects_disposition():
    empty = CognitiveImpactAssessment(effects=[])
    canonical = canonical_delta_content(empty)
    assert canonical
    assert visible_delta_content("WATCH", canonical) == canonical
    assert visible_delta_content("ENGAGE", canonical) == canonical
    assert visible_delta_content("DROP", canonical) == ""
    assert visible_delta_content("DROP", "No material cognitive change relative to the current Kernel.") == ""


def test_hydrated_legacy_reinforce_project_is_normalized_none(client: TestClient, db):
    from app.models.scheduler import AttentionPlan
    from tests.conftest import add_text, analyze, kernel_index

    index = kernel_index(client)
    src = add_text(client, "A technical paper about motor intelligence latency.", title="hydrate-legacy")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]
    project_id = index["P1"]["id"]
    plan_id = UUID(str(first["attention_plan"]["id"]))
    illegal = {
        "operation": "REINFORCE",
        "target_node_id": project_id,
    }
    debug = {
        "matches": [
            {
                "node_id": project_id,
                "node_type": "PROJECT",
                "title": "Motor Intelligence",
                "score": 0.9,
                "reason": "legacy locate",
                "structural": False,
                "relevance_type": "TOPIC",
            }
        ],
        "cognitive_impact": {
            "effects": [
                {
                    "target_kernel_node_id": project_id,
                    "operation": "REINFORCE",
                    "target_node_type": "PROJECT",
                    "change_magnitude": 0.9,
                    "epistemic_strength": 0.5,
                    "target_importance": 0.8,
                    "reason": "legacy location treated as update",
                    "exploration_candidate": False,
                }
            ],
            "attention_cost": 8.0,
            "exploration_candidate": False,
        },
    }

    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    stored_plan = dict(payload.get("attention_plan") or {})
    stored_plan["update"] = illegal
    stored_plan["score_debug"] = debug
    payload["attention_plan"] = stored_plan
    payload["update"] = illegal
    payload["delta_content"] = "legacy REINFORCE(PROJECT) prose"
    payload["cognitive_impact"] = debug["cognitive_impact"]
    run.result_payload = payload
    flag_modified(run, "result_payload")

    plan_row = db.get(AttentionPlan, plan_id)
    plan_row.score_debug = debug
    flag_modified(plan_row, "score_debug")
    db.commit()

    stored = client.get(f"/analysis/{run_id}").json()
    latest = stored["latest_attention_plan"]
    assert (stored["original_attention_plan"] or {}).get("update") == illegal
    assert (latest.get("update") or {}).get("operation") is None
    assert (stored.get("update") or {}).get("operation") is None
    assert stored["update"] == latest["update"]
    assert stored["delta_content"] == latest["delta_content"]
    if latest.get("disposition") == "DROP":
        assert stored["delta_content"] == ""
    else:
        assert stored["delta_content"] == canonical_delta_content(
            normalize_frozen_transition(debug["cognitive_impact"], []).assessment
        )

    rerun = db.get(AnalysisRun, UUID(str(run_id)))
    assert rerun.result_payload["update"] == illegal
    assert rerun.result_payload["attention_plan"]["update"] == illegal


def test_human_feedback_records_normalized_visible_prediction(client: TestClient, db):
    from copy import deepcopy

    from app.models.scheduler import AttentionFeedback, AttentionPlan
    from app.services.attention_feedback import public_update
    from tests.conftest import add_text, analyze, kernel_index

    index = kernel_index(client)
    src = add_text(client, "A technical paper about motor intelligence latency.", title="fb-normalized")
    first = analyze(client, src["id"])
    run_id = first["analysis_run"]["id"]
    project_id = index["P1"]["id"]
    plan_id = UUID(str(first["attention_plan"]["id"]))
    debug = {
        "matches": [
            {
                "node_id": project_id,
                "node_type": "PROJECT",
                "title": "Motor Intelligence",
                "score": 0.9,
                "reason": "legacy locate",
                "structural": False,
                "relevance_type": "TOPIC",
            }
        ],
        "cognitive_impact": {
            "effects": [
                {
                    "target_kernel_node_id": project_id,
                    "operation": "REINFORCE",
                    "target_node_type": "MODEL",
                    "change_magnitude": 0.9,
                    "epistemic_strength": 0.5,
                    "target_importance": 0.8,
                    "reason": "legacy location treated as update",
                    "exploration_candidate": False,
                }
            ]
        },
    }
    run = db.get(AnalysisRun, UUID(str(run_id)))
    payload = dict(run.result_payload or {})
    payload["update"] = {"operation": "REINFORCE", "target_node_id": project_id}
    payload["delta_content"] = "raw historical REINFORCE(PROJECT)"
    run.result_payload = payload
    flag_modified(run, "result_payload")
    plan_row = db.get(AttentionPlan, plan_id)
    plan_row.score_debug = debug
    flag_modified(plan_row, "score_debug")
    db.commit()

    visible = client.get(f"/analysis/{run_id}").json()
    latest = visible["latest_attention_plan"]
    resp = client.post(f"/analysis/attention-plans/{plan_id}/feedback", json={"kind": "CONFIRM"})
    assert resp.status_code == 200, resp.text
    pred = resp.json()["system_prediction"]
    assert pred["disposition"] == latest["disposition"]
    assert public_update(pred["update"]) == public_update(latest["update"])
    assert pred["delta_content"] == latest["delta_content"]
    assert public_update(pred["update"]) is None

    historical = deepcopy(pred)
    planned = client.post(
        "/scheduler/plan",
        json={"source_id": src["id"], "runtime_context": {"current_task": "later"}},
    )
    assert planned.status_code == 200, planned.text
    row = db.get(AttentionFeedback, UUID(str(resp.json()["id"])))
    assert row.system_prediction == historical
    rerun = db.get(AnalysisRun, UUID(str(run_id)))
    assert rerun.result_payload["update"] == {"operation": "REINFORCE", "target_node_id": project_id}


def test_feedback_on_plan_a_does_not_use_plan_b_matches():
    from app.services.attention_feedback import system_prediction_from_plan

    project_id = uuid4()
    model_id = uuid4()
    plan_a = type(
        "Plan",
        (),
        {
            "disposition": "ENGAGE",
            "score_debug": {
                "matches": [
                    {
                        "node_id": str(project_id),
                        "node_type": "PROJECT",
                        "title": "P",
                        "score": 0.9,
                        "reason": "locate A",
                        "structural": False,
                        "relevance_type": "TOPIC",
                    }
                ],
                "cognitive_impact": {
                    "effects": [
                        {
                            "target_kernel_node_id": str(project_id),
                            "operation": "REINFORCE",
                            "target_node_type": "MODEL",
                            "change_magnitude": 0.9,
                            "epistemic_strength": 0.5,
                            "target_importance": 0.8,
                            "reason": "plan A judgment",
                        }
                    ]
                },
            },
        },
    )()
    run = type(
        "Run",
        (),
        {
            "result_payload": {
                "update": {"operation": "REINFORCE", "target_node_id": str(model_id)},
                "delta_content": "should not win",
                "attention_plan": {
                    "score_debug": {
                        "matches": [
                            {
                                "node_id": str(model_id),
                                "node_type": "MODEL",
                                "title": "M",
                                "score": 0.9,
                                "reason": "locate B / latest",
                                "structural": False,
                                "relevance_type": "TOPIC",
                            }
                        ],
                        "cognitive_impact": {
                            "effects": [
                                {
                                    "target_kernel_node_id": str(model_id),
                                    "operation": "REINFORCE",
                                    "target_node_type": "MODEL",
                                    "change_magnitude": 0.9,
                                    "epistemic_strength": 0.5,
                                    "target_importance": 0.8,
                                    "reason": "plan B would restore MODEL",
                                }
                            ]
                        },
                    }
                },
            }
        },
    )()
    pred = system_prediction_from_plan(plan_a, run)
    assert pred["disposition"] == "ENGAGE"
    assert pred["update"] is None
    assert pred["delta_content"] == canonical_delta_content(
        normalize_frozen_transition(plan_a.score_debug["cognitive_impact"], []).assessment
    )
