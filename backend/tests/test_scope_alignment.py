"""Cognitive Dynamics v2.0.2: scope-aligned impact, not domain-specific rules."""

from __future__ import annotations

from uuid import uuid4

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.prompts import IMPACT_SYSTEM
from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import (
    CognitiveEffect,
    assess_impact_from_rules,
    ground_effects,
    scope_alignment,
)
from app.services.extraction import ExtractionResult
from app.services.matching import KernelMatch
from tests.fakes import SemanticFakeChat

BELIEF_FASTEST_LOOP = "Large unified models may be unsuitable for the fastest control loop."

HIERARCHICAL_EXPLICIT = (
    "A general model performs high-level planning. "
    "A separate low-level controller executes high-frequency motor control. "
    "The architecture is hierarchical."
)
TRULY_UNIFIED_EXPLICIT = (
    "The same large model directly outputs high-frequency joint commands "
    "at 500 Hz, with no separate low-level controller."
)
SCOPE_AMBIGUOUS = "A unified AI brain controls the entire robot."

BENCHMARK_SOURCE = "Method X beats baseline on Benchmark A."
BENCHMARK_KERNEL = "Method X is generally superior across real-world tasks."
BENCHMARK_MATCHED_KERNEL = "Method X is strong on Benchmark A."

CAUSAL_SOURCE = "Feature Y correlates with higher success in one deployment."
CAUSAL_KERNEL = "Feature Y causally improves success across deployments."


def _match(title: str, node_type: str = "BELIEF") -> KernelMatch:
    return KernelMatch(
        node_id=uuid4(),
        node_type=node_type,
        title=title,
        score=0.8,
        reason="test",
        relevance_type="TOPIC",
    )


def _belief_effects(assessment, match: KernelMatch):
    return [e for e in assessment.effects if e.target_kernel_node_id == match.node_id]


def test_impact_prompt_requires_scope_alignment():
    low = IMPACT_SYSTEM.lower()
    assert "scope alignment" in low
    assert "broad claim" in low
    assert "narrower" in low
    assert "refine" in low


def test_scope_alignment_hierarchical_is_split():
    assert scope_alignment(HIERARCHICAL_EXPLICIT, BELIEF_FASTEST_LOOP) == "split"


def test_scope_alignment_truly_unified_is_aligned():
    assert scope_alignment(TRULY_UNIFIED_EXPLICIT, BELIEF_FASTEST_LOOP) == "aligned"


def test_scope_alignment_ambiguous_is_mismatch():
    assert scope_alignment(SCOPE_AMBIGUOUS, BELIEF_FASTEST_LOOP) == "mismatch"


def test_scope_alignment_benchmark_does_not_generalize():
    assert scope_alignment(BENCHMARK_SOURCE, BENCHMARK_KERNEL) == "mismatch"
    assert scope_alignment(BENCHMARK_SOURCE, BENCHMARK_MATCHED_KERNEL) == "aligned"


def test_scope_alignment_correlation_is_not_causal_generalization():
    assert scope_alignment(CAUSAL_SOURCE, CAUSAL_KERNEL) == "mismatch"


def test_hierarchical_explicit_does_not_challenge():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment = assess_impact_from_rules(
        HIERARCHICAL_EXPLICIT,
        ExtractionResult(technical_claims=["separate low-level controller"], evidence_maturity=0.4),
        [match],
    )
    kinds = {e.effect for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE not in kinds
    assert kinds <= {CognitiveEffectKind.REINFORCE, CognitiveEffectKind.REFINE}


def test_truly_unified_explicit_challenge_is_preserved():
    match = _match(BELIEF_FASTEST_LOOP)
    raw = [
        CognitiveEffect(
            target_kernel_node_id=match.node_id,
            effect=CognitiveEffectKind.CHALLENGE,
            change_magnitude=0.8,
            epistemic_strength=0.4,
            target_importance=0.75,
            reason="same model at the Kernel's control-loop scope",
        )
    ]
    grounded = ground_effects(
        raw,
        [match],
        ExtractionResult(evidence_maturity=0.5),
        independent_source_count=2,
        source_text=TRULY_UNIFIED_EXPLICIT,
    )
    assert grounded[0].effect == CognitiveEffectKind.CHALLENGE

    chat = SemanticFakeChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    extraction = provider.extract_information(TRULY_UNIFIED_EXPLICIT, "TEXT")
    assessment = provider.assess_cognitive_impact(TRULY_UNIFIED_EXPLICIT, extraction, [match])
    kinds = {e.effect for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE in kinds


def test_ambiguous_scope_has_no_strong_direction():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment = assess_impact_from_rules(
        SCOPE_AMBIGUOUS,
        ExtractionResult(technical_claims=["unified AI brain"], evidence_maturity=0.4),
        [match],
    )
    for effect in _belief_effects(assessment, match):
        assert effect.effect in {CognitiveEffectKind.REFINE, CognitiveEffectKind.NO_MATERIAL_CHANGE}
        assert effect.epistemic_strength <= 0.35


def test_benchmark_scope_does_not_auto_reinforce_general_belief():
    match = _match(BENCHMARK_KERNEL)
    assessment = assess_impact_from_rules(
        BENCHMARK_SOURCE,
        ExtractionResult(technical_claims=["Method X beats baseline on Benchmark A."], evidence_maturity=0.5),
        [match],
    )
    for effect in _belief_effects(assessment, match):
        assert effect.effect != CognitiveEffectKind.REINFORCE or effect.epistemic_strength <= 0.25
        assert effect.effect in {
            CognitiveEffectKind.REFINE,
            CognitiveEffectKind.NO_MATERIAL_CHANGE,
            CognitiveEffectKind.REINFORCE,
        }
        if effect.effect == CognitiveEffectKind.REINFORCE:
            raise AssertionError("benchmark result must not automatically REINFORCE a broader belief")


def test_causal_deployment_scope_does_not_auto_reinforce():
    match = _match(CAUSAL_KERNEL)
    assessment = assess_impact_from_rules(
        CAUSAL_SOURCE,
        ExtractionResult(technical_claims=["Feature Y correlates with success in one deployment."], evidence_maturity=0.5),
        [match],
    )
    kinds = {e.effect for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.REINFORCE not in kinds
    assert kinds <= {CognitiveEffectKind.REFINE, CognitiveEffectKind.NO_MATERIAL_CHANGE}


def test_hierarchical_impact_and_delta_are_not_semantically_inverted():
    match = _match(BELIEF_FASTEST_LOOP)
    chat = SemanticFakeChat()
    provider = ModelBackedCognitiveProvider(chat_fn=chat)
    extraction = provider.extract_information(HIERARCHICAL_EXPLICIT, "TEXT")
    assessment = provider.assess_cognitive_impact(HIERARCHICAL_EXPLICIT, extraction, [match])
    kinds = {e.effect for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE not in kinds
    delta = provider.propose_model_delta(
        HIERARCHICAL_EXPLICIT,
        extraction,
        [match],
        assessment.features,
        [],
    )
    joined = " ".join(
        [delta.summary, *(delta.distinctions or []), *(delta.questions or []), *(delta.what_could_change or [])]
    ).lower()
    assert "hierarch" in joined or "layer" in joined
