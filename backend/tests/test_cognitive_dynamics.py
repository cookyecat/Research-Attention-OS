"""Cognitive Dynamics v2.0: impact assessment, routing from effects, Kernel safety."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.enums import AttentionState, ClaimType, CognitiveEffectKind, ExpectedOutput, ProcessingMode, Urgency
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    assess_impact_from_rules,
    epistemic_cap,
    ground_effects,
    resolve_target_importance,
)
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.matching import KernelMatch
from app.services.scheduler import RuntimeView, SchedulerFeatures, route
from tests.conftest import add_text, analyze, kernel_index
from tests.test_scheduler_grounding import GALAXY_STYLE


def _features(**overrides) -> SchedulerFeatures:
    base = dict(
        topic_relevance=0.8,
        structural_relevance=0.1,
        decision_relevance=0.2,
        novelty=0.65,
        credibility=0.7,
        kernel_delta=0.7,
        bottleneck_alignment=0.2,
        disagreement=0.1,
        actionability=0.4,
        temporal_value=0.4,
        cognitive_cost=8.0,
        evidence_maturity=0.4,
        change_magnitude=0.7,
        epistemic_strength=0.35,
        target_importance=0.7,
        attention_cost=8.0,
    )
    base.update(overrides)
    return SchedulerFeatures(**base)


def _match(node_type: str = "PROJECT", relevance_type: str = "TOPIC", score: float = 0.8) -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=node_type,
        score=score,
        reason="test",
        structural=relevance_type == "STRUCTURAL",
        relevance_type=relevance_type,
    )


def _effect(match: KernelMatch | None, kind: CognitiveEffectKind, **overrides) -> CognitiveEffect:
    base = dict(
        target_kernel_node_id=match.node_id if match else None,
        effect=kind,
        change_magnitude=0.7,
        epistemic_strength=0.25,
        target_importance=0.75,
        reason="test effect",
        exploration_candidate=kind == CognitiveEffectKind.OPEN_NEW,
    )
    base.update(overrides)
    return CognitiveEffect(**base)


def _assessment(*effects: CognitiveEffect, **kwargs) -> CognitiveImpactAssessment:
    explore = kwargs.pop("exploration_candidate", any(e.exploration_candidate for e in effects))
    return CognitiveImpactAssessment(
        effects=list(effects),
        attention_cost=kwargs.get("attention_cost", 8.0),
        exploration_candidate=explore,
    )


def test_high_topic_without_material_change_does_not_engage():
    match = _match("PROJECT", "TOPIC", 0.88)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.NO_MATERIAL_CHANGE, change_magnitude=0.12, epistemic_strength=0.2)
    )
    plan = route(
        _features(topic_relevance=0.88, kernel_delta=0.12, change_magnitude=0.12, epistemic_strength=0.2),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state != AttentionState.ENGAGE


def test_low_topic_structural_effect_may_engage():
    match = _match("MODEL", "STRUCTURAL", 0.8)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.7, epistemic_strength=0.35, target_importance=0.75)
    )
    plan = route(
        _features(topic_relevance=0.15, structural_relevance=0.8, kernel_delta=0.7, decision_relevance=0.1),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert ProcessingMode.SYNTHESIZE in plan.processing_modes


def test_high_change_low_epistemic_favors_verify():
    match = _match("MODEL", "TOPIC", 0.7)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.7, epistemic_strength=0.2, target_importance=0.75)
    )
    plan = route(
        _features(topic_relevance=0.7, kernel_delta=0.7, change_magnitude=0.7, epistemic_strength=0.2, evidence_maturity=0.35),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert ProcessingMode.VERIFY in plan.processing_modes
    assert ProcessingMode.SYNTHESIZE in plan.processing_modes


def test_strong_target_refinement_synthesizes():
    match = _match("MODEL", "TOPIC", 0.7)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.7, epistemic_strength=0.35, target_importance=0.8)
    )
    plan = route(
        _features(topic_relevance=0.7, kernel_delta=0.7, bottleneck_alignment=0.2),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert ProcessingMode.SYNTHESIZE in plan.processing_modes


def test_challenge_on_belief_favors_verify():
    match = _match("BELIEF", "TOPIC", 0.8)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.CHALLENGE, change_magnitude=0.75, epistemic_strength=0.4, target_importance=0.75)
    )
    plan = route(
        _features(disagreement=0.8, kernel_delta=0.75),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert ProcessingMode.VERIFY in plan.processing_modes
    assert ProcessingMode.SYNTHESIZE in plan.processing_modes


def test_decision_target_effect_is_decision_review():
    match = _match("DECISION", "STRUCTURAL", 0.85)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.75, epistemic_strength=0.4, target_importance=0.85)
    )
    plan = route(
        _features(topic_relevance=0.2, decision_relevance=0.2, structural_relevance=0.85),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert plan.expected_output == ExpectedOutput.DECISION_REVIEW
    assert ProcessingMode.SYNTHESIZE in plan.processing_modes


def test_high_decision_relevance_without_decision_effect_is_not_decision_review():
    match = _match("PROJECT", "TOPIC", 0.8)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, epistemic_strength=0.3, target_importance=0.65)
    )
    plan = route(
        _features(decision_relevance=0.9, topic_relevance=0.8, kernel_delta=0.7),
        assessment=assessment,
        matches=[match],
    )
    assert plan.expected_output != ExpectedOutput.DECISION_REVIEW


def test_bottleneck_effect_can_be_priority():
    match = _match("BOTTLENECK", "BOTTLENECK", 0.8)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.75, epistemic_strength=0.3, target_importance=0.8)
    )
    plan = route(
        _features(bottleneck_alignment=0.2, topic_relevance=0.4),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.ENGAGE
    assert plan.urgency == Urgency.PRIORITY


def test_runtime_deadline_still_watch_when_not_threatened():
    match = _match("MODEL")
    assessment = _assessment(_effect(match, CognitiveEffectKind.REFINE, change_magnitude=0.8))
    plan = route(
        _features(),
        RuntimeView(deadline_minutes=60, interruptibility="LOW"),
        assessment=assessment,
        matches=[match],
    )
    assert plan.attention_state == AttentionState.WATCH
    assert plan.urgency == Urgency.BACKGROUND
    assert plan.urgency != Urgency.PREEMPT


def test_explicit_payload_importance_outranks_type_prior_and_llm():
    class Node:
        node_type = "BELIEF"
        payload = {"importance": 0.2}

    assert resolve_target_importance(node=Node(), node_type="BELIEF", llm_estimate=0.99) == 0.2
    class Bare:
        node_type = "BELIEF"
        payload = {"proposition": "x"}

    assert resolve_target_importance(node=Bare(), node_type="BELIEF", llm_estimate=0.99) == 0.75
    assert resolve_target_importance(node_type=None, llm_estimate=0.41) == 0.41
    class Ranked:
        node_type = "GOAL"
        payload = {"priority": 1}

    assert resolve_target_importance(node=Ranked()) == 1.0


def test_promotional_reinforce_keeps_epistemic_strength_low():
    belief = _match("BELIEF", "TOPIC", 0.8)
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="The company says the robot generalizes zero-shot.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["zero-shot"],
        promotional_framing=["revolutionary seamless"],
        marketing_heavy=True,
        evidence_maturity=0.4,
    )
    assessment = assess_impact_from_rules(
        "The company says its embodied motor intelligence generalizes zero-shot. Revolutionary seamless leap.",
        extraction,
        [belief],
        independent_source_count=1,
    )
    assert assessment.effects
    assert any(e.effect == CognitiveEffectKind.REINFORCE or e.effect == CognitiveEffectKind.REFINE for e in assessment.effects)
    assert all(e.epistemic_strength <= 0.35 for e in assessment.effects)
    assert assessment.features.epistemic_strength <= 0.35
    plan = route(assessment.features, assessment=assessment)
    assert plan.attention_state != AttentionState.DROP
    assert ProcessingMode.LEARN not in plan.processing_modes or ProcessingMode.VERIFY in plan.processing_modes


def test_exploration_open_new_is_not_automatic_drop():
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="A new temporal abstraction for tactile control.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["temporal abstraction"],
        evidence_maturity=0.4,
    )
    assessment = assess_impact_from_rules(
        "A paper introduces a new temporal abstraction for tactile control without overlapping the active kernel.",
        extraction,
        [],
        independent_source_count=1,
    )
    assert any(e.effect == CognitiveEffectKind.OPEN_NEW for e in assessment.effects)
    assert assessment.exploration_candidate is True
    plan = route(assessment.features, assessment=assessment)
    assert plan.attention_state != AttentionState.DROP


def test_irrelevant_hype_is_no_material_change_and_dropped():
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="Unlock a revolutionary seamless lifestyle robot.", claim_type=ClaimType.PROMOTIONAL)],
        promotional_framing=["revolutionary seamless"],
        marketing_heavy=True,
        evidence_maturity=0.1,
    )
    assessment = assess_impact_from_rules(
        "Unlock a revolutionary seamless game-changing lifestyle robot. Reimagine delight.",
        extraction,
        [],
    )
    assert all(e.effect == CognitiveEffectKind.NO_MATERIAL_CHANGE for e in assessment.effects)
    plan = route(assessment.features, assessment=assessment)
    assert plan.attention_state in {AttentionState.DROP, AttentionState.AWARE}


def test_cognitive_effect_does_not_mutate_kernel(client: TestClient):
    index = kernel_index(client)
    before = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    src = add_text(client, GALAXY_STYLE, title="dynamics-no-mutate")
    result = analyze(client, src["id"])
    after = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert after["current_version"] == before["current_version"]
    assert after["payload"] == before["payload"]
    assert result.get("cognitive_impact")


def test_kernel_patch_remains_proposed_until_accept(client: TestClient):
    index = kernel_index(client)
    src = add_text(
        client,
        """A high-quality technical paper on arXiv argues the opposite of the belief that large
        unified models may be unsuitable for the fastest embodied-control loop.
        It argues that large unified models are necessary for high-frequency embodied motor control.""",
        title="dynamics-proposed",
    )
    result = analyze(client, src["id"])
    assert result["kernel_patches"]
    assert all(p["status"] == "PROPOSED" for p in result["kernel_patches"])
    b1 = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert b1["current_version"] == 1


def test_ground_effects_caps_single_source_epistemic_strength():
    match = _match("MODEL")
    extraction = ExtractionResult(marketing_heavy=True, evidence_maturity=0.4)
    raw = [
        CognitiveEffect(
            target_kernel_node_id=match.node_id,
            effect=CognitiveEffectKind.REINFORCE,
            change_magnitude=0.6,
            epistemic_strength=0.9,
            target_importance=0.75,
            reason="company self-report",
        )
    ]
    grounded = ground_effects(raw, [match], extraction, independent_source_count=1)
    assert grounded[0].effect == CognitiveEffectKind.REINFORCE
    assert grounded[0].change_magnitude == 0.6
    assert grounded[0].epistemic_strength <= 0.25
    assert epistemic_cap(extraction, independent_source_count=1) <= 0.25


def test_impact_assessment_is_run_scoped_dataclass():
    assessment = CognitiveImpactAssessment(effects=[], attention_cost=2.0)
    assert assessment.as_dict()["effects"] == []
    assert "target_kernel_node_id" in CognitiveEffect(
        None, CognitiveEffectKind.OPEN_NEW, 0.5, 0.2, 0.5, "new", True
    ).as_dict()
