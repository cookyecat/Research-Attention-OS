"""Cognitive Dynamics v2.0.2a: semantic scope in impact assessment, not lexical override."""

from __future__ import annotations

from uuid import uuid4

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_USER
from app.enums import CognitiveEffectKind
from app.services.matching import KernelMatch
from tests.fakes import SemanticFakeChat, _load_json_blob, _split_marker

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
UNRELATED_SEPARATE_PLUS_UNIFIED = (
    "We use a separate dataset for training. "
    + TRULY_UNIFIED_EXPLICIT
)
SCOPE_AMBIGUOUS = "A unified AI brain controls the entire robot."

BENCHMARK_SOURCE = "Method X beats baseline on Benchmark A."
BENCHMARK_KERNEL = "Method X is generally superior across real-world tasks."

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


def _assess(text: str, match: KernelMatch):
    provider = ModelBackedCognitiveProvider(chat_fn=ScopeContractFake())
    extraction = provider.extract_information(text, "TEXT")
    return provider.assess_cognitive_impact(text, extraction, [match]), provider, extraction


class ScopeContractFake(SemanticFakeChat):
    """Test double that distinguishes contrasting scope cases.

    Not a canned single effect. Hierarchical, truly unified, and ambiguous
    sources must produce different BELIEF directions against the same Kernel title.
    """

    def _impact(self, user: str) -> dict:
        parsed = super()._impact(user)
        source, rest = _split_marker(user, "Eligible cognitive targets:")
        if not rest:
            source, rest = _split_marker(user, "Matches:")
        epistemic, after_locations = _split_marker(source, "Kernel locations:")
        if after_locations:
            source = epistemic
        matches = _load_json_blob(rest)
        if not isinstance(matches, list):
            matches = []
        by_id = {str(item.get("id")): item for item in matches if isinstance(item, dict)}
        effects = []
        for effect in parsed.get("effects") or []:
            item = by_id.get(str(effect.get("target_kernel_node_id") or ""))
            ntype = str((item or {}).get("type") or "")
            title = str((item or {}).get("title") or "")
            scoped = _scoped_belief_effect(source, title) if ntype == "BELIEF" else None
            if scoped is None and ntype == "BELIEF":
                continue
            if scoped is not None:
                kind, change, epi = scoped
                effect = {
                    **effect,
                    "operation": kind,
                    "change_magnitude": change,
                    "epistemic_strength": epi,
                    "reason": f"{kind} after aligning source-claim scope with Kernel proposition.",
                }
            effects.append(effect)
        parsed["effects"] = effects
        return parsed


def _scoped_belief_effect(source: str, title: str) -> tuple[str, float, float] | None:
    """Map contrasting source/Kernel pairs. None leaves the base fake unchanged."""
    src = source.lower()
    ker = title.lower()
    control_loop_belief = any(p in ker for p in ("fastest", "high-frequency", "control loop"))
    if control_loop_belief:
        hierarchical = all(p in src for p in ("high-level", "planning", "low-level", "controller"))
        unified_direct = (
            "same large model" in src
            and "directly" in src
            and "no separate" in src
            and ("500 hz" in src or "high-frequency joint" in src)
        )
        ambiguous_system = (
            "unified" in src
            and "brain" in src
            and "entire robot" in src
            and "controller" not in src
            and "500" not in src
            and "directly" not in src
        )
        if unified_direct:
            return "CHALLENGE", 0.75, 0.4
        if hierarchical:
            return "REINFORCE", 0.35, 0.22
        if ambiguous_system:
            return None
        return None
    if "generally" in ker and "real-world" in ker and "benchmark" in src:
        return None
    if "causal" in ker and "across" in ker and "correlat" in src and "one deployment" in src:
        return None
    return None


def test_impact_prompt_requires_scope_alignment():
    low = IMPACT_SYSTEM.lower()
    assert "scope alignment" in low
    assert "broad claim" in low
    assert "narrower" in low
    assert "reinforce" in low
    assert "open_new" in low or "open new" in low
    assert "location" in low
    assert "epistemic" in low
    assert "refine" not in low or "do not emit refine" in low
    assert "kernel propositions" in IMPACT_USER.lower()


def test_hierarchical_explicit_does_not_challenge():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment, _, _ = _assess(HIERARCHICAL_EXPLICIT, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE not in kinds
    assert kinds <= {CognitiveEffectKind.REINFORCE}
    assert all(e.epistemic_strength <= 0.35 for e in _belief_effects(assessment, match))


def test_truly_unified_explicit_challenge_is_allowed():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment, _, _ = _assess(TRULY_UNIFIED_EXPLICIT, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE in kinds


def test_contrasting_control_scope_cases_are_not_the_same_effect():
    match_a = _match(BELIEF_FASTEST_LOOP)
    match_b = _match(BELIEF_FASTEST_LOOP)
    match_c = _match(BELIEF_FASTEST_LOOP)
    a, _, _ = _assess(HIERARCHICAL_EXPLICIT, match_a)
    b, _, _ = _assess(TRULY_UNIFIED_EXPLICIT, match_b)
    c, _, _ = _assess(SCOPE_AMBIGUOUS, match_c)
    kind_a = {e.operation for e in _belief_effects(a, match_a)}
    kind_b = {e.operation for e in _belief_effects(b, match_b)}
    kind_c = {e.operation for e in _belief_effects(c, match_c)}
    assert kind_a != kind_b
    assert kind_b != kind_c
    assert CognitiveEffectKind.CHALLENGE in kind_b
    assert CognitiveEffectKind.CHALLENGE not in kind_a
    assert CognitiveEffectKind.CHALLENGE not in kind_c


def test_unrelated_separate_mention_does_not_block_unified_challenge():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment, _, _ = _assess(UNRELATED_SEPARATE_PLUS_UNIFIED, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.CHALLENGE in kinds


def test_ambiguous_scope_has_no_strong_direction():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment, _, _ = _assess(SCOPE_AMBIGUOUS, match)
    for effect in _belief_effects(assessment, match):
        assert effect.operation != CognitiveEffectKind.CHALLENGE
        assert effect.epistemic_strength <= 0.35


def test_benchmark_scope_does_not_auto_reinforce_general_belief():
    match = _match(BENCHMARK_KERNEL)
    assessment, _, _ = _assess(BENCHMARK_SOURCE, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.REINFORCE not in kinds
    assert CognitiveEffectKind.CHALLENGE not in kinds


def test_causal_deployment_scope_does_not_auto_reinforce():
    match = _match(CAUSAL_KERNEL)
    assessment, _, _ = _assess(CAUSAL_SOURCE, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
    assert CognitiveEffectKind.REINFORCE not in kinds
    assert CognitiveEffectKind.CHALLENGE not in kinds


def test_hierarchical_impact_and_delta_are_not_semantically_inverted():
    match = _match(BELIEF_FASTEST_LOOP)
    assessment, provider, extraction = _assess(HIERARCHICAL_EXPLICIT, match)
    kinds = {e.operation for e in _belief_effects(assessment, match)}
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


def test_production_grounding_does_not_rewrite_challenge_from_source_markers():
    from app.services.cognitive_impact import CognitiveEffect, ground_effects
    from app.services.extraction import ExtractionResult

    match = _match(BELIEF_FASTEST_LOOP)
    raw = [
        CognitiveEffect(
            target_kernel_node_id=match.node_id,
            operation=CognitiveEffectKind.CHALLENGE,
            change_magnitude=0.8,
            epistemic_strength=0.4,
            target_importance=0.75,
            reason="llm judged challenge at aligned scope",
        )
    ]
    grounded = ground_effects(raw, [match], ExtractionResult(evidence_maturity=0.5), independent_source_count=2)
    assert grounded[0].operation == CognitiveEffectKind.CHALLENGE
    assert grounded[0].change_magnitude == 0.8
