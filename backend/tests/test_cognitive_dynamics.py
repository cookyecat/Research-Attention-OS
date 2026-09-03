"""Cognitive Dynamics v2.0: impact assessment, routing from effects, Kernel safety."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.enums import Disposition, ClaimType, CognitiveEffectKind, ExpectedOutput, Urgency
from app.services.cognitive_impact import (
    MEANINGFUL_CHANGE,
    CognitiveEffect,
    CognitiveImpactAssessment,
    assess_impact_from_rules,
    epistemic_cap,
    ground_effects,
    primary_update,
    resolve_target_importance,
    select_primary_effect,
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
        operation=kind,
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
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.12, epistemic_strength=0.2)
    )
    plan = route(
        _features(topic_relevance=0.88, kernel_delta=0.12, change_magnitude=0.12, epistemic_strength=0.2),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition != Disposition.ENGAGE


def test_low_topic_structural_effect_may_engage():
    match = _match("MODEL", "STRUCTURAL", 0.8)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, epistemic_strength=0.35, target_importance=0.75)
    )
    plan = route(
        _features(topic_relevance=0.15, structural_relevance=0.8, kernel_delta=0.7, decision_relevance=0.1),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE


def test_high_change_low_epistemic_favors_verify():
    match = _match("MODEL", "TOPIC", 0.7)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, epistemic_strength=0.2, target_importance=0.75)
    )
    plan = route(
        _features(topic_relevance=0.7, kernel_delta=0.7, change_magnitude=0.7, epistemic_strength=0.2, evidence_maturity=0.35),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE


def test_strong_target_refinement_synthesizes():
    match = _match("MODEL", "TOPIC", 0.7)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, epistemic_strength=0.35, target_importance=0.8)
    )
    plan = route(
        _features(topic_relevance=0.7, kernel_delta=0.7, bottleneck_alignment=0.2),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE


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
    assert plan.disposition == Disposition.ENGAGE


def test_decision_target_effect_is_decision_review():
    match = _match("DECISION", "STRUCTURAL", 0.85)
    assessment = _assessment(
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.75, epistemic_strength=0.4, target_importance=0.85)
    )
    plan = route(
        _features(topic_relevance=0.2, decision_relevance=0.2, structural_relevance=0.85),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE
    assert plan.expected_output == ExpectedOutput.DECISION_REVIEW


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
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.75, epistemic_strength=0.3, target_importance=0.8)
    )
    plan = route(
        _features(bottleneck_alignment=0.2, topic_relevance=0.4),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.ENGAGE
    assert plan.urgency == Urgency.PRIORITY


def test_runtime_deadline_still_watch_when_not_threatened():
    match = _match("MODEL")
    assessment = _assessment(_effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.8))
    plan = route(
        _features(),
        RuntimeView(deadline_minutes=60, interruptibility="LOW"),
        assessment=assessment,
        matches=[match],
    )
    assert plan.disposition == Disposition.WATCH
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
    belief = KernelMatch(
        node_id=uuid4(),
        node_type="BELIEF",
        title="Household robots already generalize zero-shot.",
        score=0.8,
        reason="test",
        relevance_type="TOPIC",
    )
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="The company says household robots already generalize zero-shot.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["zero-shot"],
        promotional_framing=["revolutionary seamless"],
        marketing_heavy=True,
        evidence_maturity=0.4,
    )
    assessment = assess_impact_from_rules(
        "The company says household robots already generalize zero-shot. Revolutionary seamless leap.",
        extraction,
        [belief],
        independent_source_count=1,
    )
    assert assessment.effects
    assert any(e.operation == CognitiveEffectKind.REINFORCE for e in assessment.effects)
    assert all(e.epistemic_strength <= 0.35 for e in assessment.effects)
    assert assessment.features.epistemic_strength <= 0.35
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition != Disposition.DROP


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
    assert any(e.operation == CognitiveEffectKind.OPEN_NEW for e in assessment.effects)
    assert assessment.exploration_candidate is True
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition != Disposition.DROP
    assert plan.disposition == Disposition.WATCH


def test_media_hype_open_new_is_not_watch():
    extraction = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="One unsourced claim of 'real-time' with no architecture.",
                claim_type=ClaimType.TECHNICAL,
            )
        ],
        technical_claims=["One unsourced claim of 'real-time' with no architecture."],
        evidence_maturity=0.2,
    )
    assessment = assess_impact_from_rules(
        "Magical inspiring robot video. One unsourced claim of 'real-time' with no architecture.",
        extraction,
        [],
        independent_source_count=1,
    )
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition in {Disposition.DROP, Disposition.AWARE}
    primary = select_primary_effect(assessment)
    if primary is not None:
        assert float(primary.change_magnitude) < MEANINGFUL_CHANGE


def test_negated_architecture_is_not_keep_in_view():
    extraction = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="The notes contain no architecture details.",
                claim_type=ClaimType.TECHNICAL,
            )
        ],
        technical_claims=["no architecture details"],
        evidence_maturity=0.3,
    )
    assessment = assess_impact_from_rules(
        "The notes contain no architecture details.",
        extraction,
        [],
        independent_source_count=1,
    )
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition in {Disposition.DROP, Disposition.AWARE}


def test_negated_technical_cue_does_not_block_promotional_framing():
    from app.services.extraction import extract_from_text

    result = extract_from_text(
        "Unlock a revolutionary seamless lifestyle robot. No architecture, no measurements.",
        "TEXT",
    )
    assert result.marketing_heavy is True


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
    assert not assessment.effects
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition in {Disposition.DROP, Disposition.AWARE}


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
            operation=CognitiveEffectKind.REINFORCE,
            change_magnitude=0.6,
            epistemic_strength=0.9,
            target_importance=0.75,
            reason="company self-report",
        )
    ]
    grounded = ground_effects(raw, [match], extraction, independent_source_count=1)
    assert grounded[0].operation == CognitiveEffectKind.REINFORCE
    assert grounded[0].change_magnitude == 0.6
    assert grounded[0].epistemic_strength <= 0.25
    assert epistemic_cap(extraction, independent_source_count=1) <= 0.25


def test_impact_assessment_is_run_scoped_dataclass():
    assessment = CognitiveImpactAssessment(effects=[], attention_cost=2.0)
    assert assessment.as_dict()["effects"] == []
    assert "target_kernel_node_id" in CognitiveEffect(
        None, CognitiveEffectKind.OPEN_NEW, 0.5, 0.2, 0.5, "new", True
    ).as_dict()


def test_project_location_is_not_automatic_reinforce():
    project = _match("PROJECT", "TOPIC", 0.9)
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="A new tactile feedback controller for uncertain contact.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["tactile feedback"],
        evidence_maturity=0.5,
    )
    assessment = assess_impact_from_rules(
        "A paper on tactile feedback for uncertain contact in manipulation.",
        extraction,
        [project],
        independent_source_count=1,
    )
    assert all(e.target_kernel_node_id != project.node_id for e in assessment.effects)
    assert any(e.operation == CognitiveEffectKind.OPEN_NEW for e in assessment.effects)


def test_ground_effects_discards_unaligned_project_reinforce():
    project = _match("PROJECT", "TOPIC", 0.9)
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="A new tactile feedback controller for uncertain contact.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["tactile feedback"],
        evidence_maturity=0.5,
    )
    raw = [
        CognitiveEffect(
            target_kernel_node_id=project.node_id,
            operation=CognitiveEffectKind.REINFORCE,
            change_magnitude=0.8,
            epistemic_strength=0.4,
            target_importance=0.65,
            reason="same robotics topic as Motor Intelligence",
        )
    ]
    grounded = ground_effects(raw, [project], extraction, independent_source_count=1)
    assert grounded == []


def test_bottleneck_update_requires_claim_scope_alignment():
    bottleneck = KernelMatch(
        node_id=uuid4(),
        node_type="BOTTLENECK",
        title="Lack of latency × energy × task-success evaluation for high-frequency embodied control.",
        score=0.8,
        reason="test",
        relevance_type="BOTTLENECK",
    )
    aligned = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="Latency evaluation must decompose energy and task-success rather than one end-to-end number.",
                claim_type=ClaimType.TECHNICAL,
            )
        ],
        technical_claims=["latency evaluation"],
        evidence_maturity=0.5,
    )
    assessment = assess_impact_from_rules("profiler latency energy task-success", aligned, [bottleneck])
    assert any(
        e.operation == CognitiveEffectKind.REINFORCE and e.target_kernel_node_id == bottleneck.node_id
        for e in assessment.effects
    )
    topical_only = ExtractionResult(
        claims=[ExtractedClaim(text="A humanoid robot played soccer in a demo.", claim_type=ClaimType.FACTUAL)],
        technical_claims=["humanoid"],
        evidence_maturity=0.4,
    )
    missed = assess_impact_from_rules("humanoid soccer robot demo", topical_only, [bottleneck])
    assert all(e.target_kernel_node_id != bottleneck.node_id for e in missed.effects)


def test_invalid_targeted_effect_is_discarded_not_open_new():
    belief = KernelMatch(
        node_id=uuid4(),
        node_type="BELIEF",
        title="Approach Beta is unsuitable for task Tau.",
        score=0.8,
        reason="test",
        relevance_type="TOPIC",
    )
    extraction = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="Approach Alpha succeeds on task Tau with a compact method.",
                claim_type=ClaimType.TECHNICAL,
            )
        ],
        technical_claims=["compact method"],
        evidence_maturity=0.6,
    )
    challenged = ground_effects(
        [_effect(belief, CognitiveEffectKind.CHALLENGE, change_magnitude=0.8)],
        [belief],
        extraction,
    )
    reinforced = ground_effects(
        [_effect(belief, CognitiveEffectKind.REINFORCE, change_magnitude=0.8)],
        [belief],
        extraction,
    )
    assert challenged == []
    assert reinforced == []


def test_direct_counterevidence_can_challenge_a_belief():
    belief = KernelMatch(
        node_id=uuid4(),
        node_type="BELIEF",
        title="Approach Beta is unsuitable for task Tau.",
        score=0.8,
        reason="test",
        relevance_type="TOPIC",
    )
    extraction = ExtractionResult(
        claims=[
            ExtractedClaim(
                text="Approach Beta is unsuitable is false; compared to Alpha it handles task Tau within the latency bound.",
                claim_type=ClaimType.TECHNICAL,
            )
        ],
        technical_claims=["latency"],
        evidence_maturity=0.6,
    )
    grounded = ground_effects(
        [_effect(belief, CognitiveEffectKind.CHALLENGE, change_magnitude=0.8)],
        [belief],
        extraction,
    )
    assert any(
        e.operation == CognitiveEffectKind.CHALLENGE and e.target_kernel_node_id == belief.node_id
        for e in grounded
    )


def test_marketing_heavy_caps_epistemic_strength_but_keeps_material_effect():
    match = _match("MODEL")
    extraction = ExtractionResult(
        claims=[ExtractedClaim(text="A new temporal abstraction for tactile control.", claim_type=ClaimType.TECHNICAL)],
        technical_claims=["temporal abstraction"],
        promotional_framing=["revolutionary"],
        marketing_heavy=True,
        evidence_maturity=0.3,
    )
    assessment = assess_impact_from_rules(
        "Revolutionary new temporal abstraction for tactile control. We propose a new method.",
        extraction,
        [],
        independent_source_count=1,
    )
    assert any(e.operation == CognitiveEffectKind.OPEN_NEW for e in assessment.effects)
    assert all(e.epistemic_strength <= 0.35 for e in assessment.effects)
    plan = route(assessment.features, assessment=assessment)
    assert plan.disposition != Disposition.DROP


def test_primary_null_and_marketing_is_not_automatic_drop():
    """marketing_heavy is framing, not a DROP rule, when a technical signal remains."""
    assessment = _assessment()
    plan = route(
        _features(
            marketing_heavy=True,
            high_quality_technical=True,
            topic_relevance=0.6,
            change_magnitude=0.0,
        ),
        assessment=assessment,
    )
    assert plan.disposition == Disposition.AWARE


def test_primary_null_promotional_without_cognitive_content_may_drop():
    assessment = _assessment()
    plan = route(_features(marketing_heavy=True, topic_relevance=0.6, change_magnitude=0.0), assessment=assessment)
    assert plan.disposition == Disposition.DROP


def test_primary_update_rejects_untargeted_reinforce_and_challenge():
    from app.services.cognitive_impact import primary_update

    illegal = _assessment(
        _effect(None, CognitiveEffectKind.CHALLENGE, change_magnitude=0.8),
        _effect(None, CognitiveEffectKind.REINFORCE, change_magnitude=0.7),
    )
    assert primary_update(illegal) == {"operation": None, "target_node_id": None}

    match = _match("BELIEF")
    mixed = _assessment(
        _effect(None, CognitiveEffectKind.CHALLENGE, change_magnitude=0.8),
        _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.6),
    )
    update = primary_update(mixed)
    assert update["operation"] == CognitiveEffectKind.REINFORCE
    assert update["target_node_id"] == str(match.node_id)

    open_new = _assessment(_effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.6))
    assert primary_update(open_new) == {"operation": CognitiveEffectKind.OPEN_NEW, "target_node_id": None}


def test_projection_never_emits_untargeted_reinforce_or_challenge():
    from app.services.cognitive_impact import primary_update
    from app.services.scheduler import _projection_assessment

    conflicted = _projection_assessment(_features(disagreement=0.8, sources_conflict=True))
    assert all(e.operation == CognitiveEffectKind.OPEN_NEW for e in conflicted.effects)
    assert all(e.target_kernel_node_id is None for e in conflicted.effects)
    assert primary_update(conflicted)["operation"] == CognitiveEffectKind.OPEN_NEW
    assert primary_update(conflicted)["target_node_id"] is None

    material = _projection_assessment(_features(change_magnitude=0.7, disagreement=0.1))
    assert material.effects == []
    assert primary_update(material) == {"operation": None, "target_node_id": None}


def test_primary_effect_is_order_independent_and_not_list_head():
    match = _match("MODEL")
    reinforce = _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.7, target_importance=0.75)
    opened = _effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.9, target_importance=0.9)
    forward = _assessment(opened, reinforce)
    backward = _assessment(reinforce, opened)
    assert select_primary_effect(forward).operation == CognitiveEffectKind.OPEN_NEW
    assert select_primary_effect(backward).operation == CognitiveEffectKind.OPEN_NEW
    assert primary_update(forward)["operation"] == CognitiveEffectKind.OPEN_NEW
    assert primary_update(backward)["target_node_id"] is None


def test_stronger_open_new_outranks_weaker_targeted_reinforce():
    weak_target = _match("BELIEF")
    opened = _effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.8, target_importance=0.8)
    weak = _effect(weak_target, CognitiveEffectKind.REINFORCE, change_magnitude=0.4, target_importance=0.2)
    assessment = _assessment(weak, opened)
    chosen = select_primary_effect(assessment)
    assert chosen.operation == CognitiveEffectKind.OPEN_NEW
    assert chosen.target_kernel_node_id is None
    plan = route(_features(), assessment=assessment, matches=[weak_target])
    assert plan.disposition == Disposition.WATCH


def test_stronger_targeted_still_outranks_weaker_open_new():
    match = _match("MODEL")
    reinforce = _effect(match, CognitiveEffectKind.REINFORCE, change_magnitude=0.8, target_importance=0.8)
    opened = _effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.4, target_importance=0.4)
    assessment = _assessment(opened, reinforce)
    chosen = select_primary_effect(assessment)
    assert chosen.operation == CognitiveEffectKind.REINFORCE
    assert chosen.target_kernel_node_id == match.node_id


def test_route_uses_primary_effect_not_cross_effect_max():
    weak_target = _match("BELIEF")
    weak_reinforce = _effect(
        weak_target,
        CognitiveEffectKind.REINFORCE,
        change_magnitude=0.4,
        target_importance=0.2,
        epistemic_strength=0.2,
    )
    assessment = _assessment(weak_reinforce)
    plan = route(_features(change_magnitude=0.9, target_importance=0.9), assessment=assessment, matches=[weak_target])
    assert primary_update(assessment)["operation"] == CognitiveEffectKind.REINFORCE
    assert plan.disposition == Disposition.WATCH
    assert plan.disposition != Disposition.ENGAGE


def test_conflicting_open_new_can_engage_despite_low_epistemic_strength():
    assessment = _assessment(
        _effect(
            None,
            CognitiveEffectKind.OPEN_NEW,
            change_magnitude=0.7,
            target_importance=0.75,
            epistemic_strength=0.3,
        )
    )
    plan = route(
        _features(sources_conflict=True, disagreement=0.8, marketing_heavy=False),
        assessment=assessment,
    )
    assert plan.disposition == Disposition.ENGAGE


def test_material_open_new_routes_to_watch_not_aware():
    assessment = _assessment(
        _effect(None, CognitiveEffectKind.OPEN_NEW, change_magnitude=0.55, target_importance=0.55)
    )
    plan = route(_features(marketing_heavy=False), assessment=assessment)
    assert plan.disposition == Disposition.WATCH


def test_untargeted_challenge_does_not_count_as_challenge_route():
    from app.services.cognitive_impact import has_effect

    assessment = _assessment(_effect(None, CognitiveEffectKind.CHALLENGE, change_magnitude=0.8))
    assert has_effect(assessment, CognitiveEffectKind.CHALLENGE) is False
    plan = route(_features(disagreement=0.8), assessment=assessment)
    assert plan.disposition != Disposition.ENGAGE
