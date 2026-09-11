from __future__ import annotations

from uuid import uuid4

from app.enums import CognitiveEffectKind, Disposition
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.effect_admission import ANCHORED_OPEN_NEW_ADMISSION, has_jurisdiction_anchor
from app.services.effect_calibration import MAGNITUDE_FREE_CALIBRATION
from app.services.matching import KernelMatch
from app.services.pareto_decision_strategy import (
    ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    PARETO_MULTI_DELTA_DECISION_STRATEGY,
    decision_vector,
    dominates,
    pareto_frontier,
)
from app.services.scheduler import SchedulerFeatures, get_decision_strategy, route


def _match(node_type="BELIEF"):
    return KernelMatch(
        node_id=uuid4(), node_type=node_type, title=node_type, score=0.8,
        reason="test", structural=False, relevance_type="TOPIC"
    )


def _effect(match, operation, *, change=.6, epi=.7, importance=.75):
    return CognitiveEffect(
        target_kernel_node_id=match.node_id if match else None,
        operation=operation,
        change_magnitude=change,
        epistemic_strength=epi,
        target_importance=importance,
        reason="test",
        exploration_candidate=operation == CognitiveEffectKind.OPEN_NEW,
        target_node_type=match.node_type if match else None,
    )
def _features():
    return SchedulerFeatures(
        topic_relevance=.5, structural_relevance=.2, decision_relevance=.2,
        novelty=.5, credibility=.6, kernel_delta=.2, bottleneck_alignment=.1,
        disagreement=0, actionability=.3, temporal_value=.3, cognitive_cost=2,
        evidence_maturity=.6, threatens_active_work=False,
    )


def test_rs15_like_equal_reinforce_channels_both_survive_frontier():
    q2, b2 = _match("QUESTION"), _match("BELIEF")
    effects = [
        _effect(q2, CognitiveEffectKind.REINFORCE, change=.3, epi=.8, importance=.8),
        _effect(b2, CognitiveEffectKind.REINFORCE, change=.3, epi=.8, importance=.8),
    ]
    assert decision_vector(effects[0]) == decision_vector(effects[1])
    assert pareto_frontier(effects) == effects


def test_challenge_and_open_new_are_incomparable_axes():
    challenge = _effect(_match("BELIEF"), CognitiveEffectKind.CHALLENGE)
    open_new = _effect(None, CognitiveEffectKind.OPEN_NEW)
    assert not dominates(challenge, open_new)
    assert not dominates(open_new, challenge)
    assert len(pareto_frontier([challenge, open_new])) == 2


def test_stronger_reinforce_can_dominate_weaker_reinforce_for_attention_frontier():
    strong = _effect(_match("BELIEF"), CognitiveEffectKind.REINFORCE, change=.7, epi=.8, importance=.8)
    weak = _effect(_match("MODEL"), CognitiveEffectKind.REINFORCE, change=.2, epi=.3, importance=.4)
    assert dominates(strong, weak)
    assert pareto_frontier([weak, strong]) == [strong]
def test_pareto_strategy_is_registered_and_versioned():
    strategy = get_decision_strategy("pareto-multidelta")
    assert strategy is PARETO_MULTI_DELTA_DECISION_STRATEGY
    assert strategy.execution_snapshot()["version"] == "pareto-multidelta-v0.1"


def test_article_attention_is_join_over_frontier_channels():
    challenge_match = _match("BELIEF")
    reinforce_match = _match("MODEL")
    assessment = CognitiveImpactAssessment(
        effects=[
            _effect(
                challenge_match,
                CognitiveEffectKind.CHALLENGE,
                change=.7,
                epi=.7,
                importance=.75,
            ),
            _effect(
                reinforce_match,
                CognitiveEffectKind.REINFORCE,
                change=.2,
                epi=.3,
                importance=.4,
            ),
        ]
    )
    plan = route(
        _features(),
        assessment=assessment,
        matches=[challenge_match, reinforce_match],
        decision_strategy=PARETO_MULTI_DELTA_DECISION_STRATEGY,
    )
    assert plan.disposition == Disposition.ENGAGE
    assert "Pareto frontier" in plan.reason


def test_magnitude_free_strategy_is_registered_and_fingerprinted():
    strategy = get_decision_strategy("pareto-multidelta-magnitude-free")
    assert strategy is MAGNITUDE_FREE_PARETO_DECISION_STRATEGY
    snapshot = strategy.execution_snapshot()
    assert snapshot["version"] == "pareto-multidelta-magnitude-free-v0.1"
    assert snapshot["effect_calibration"]["version"] == "magnitude-free-v0.1"
    assert snapshot["effect_calibration"]["uses_raw_change_magnitude"] is False


def test_magnitude_free_question_reinforce_is_invariant_to_raw_magnitude():
    question = _match("QUESTION")
    low = _effect(question, CognitiveEffectKind.REINFORCE, change=.01, epi=.8, importance=.8)
    high = _effect(question, CognitiveEffectKind.REINFORCE, change=.99, epi=.8, importance=.8)
    assert decision_vector(low, [question], calibration_strategy=MAGNITUDE_FREE_CALIBRATION) == decision_vector(
        high, [question], calibration_strategy=MAGNITUDE_FREE_CALIBRATION
    )
    assert MAGNITUDE_FREE_CALIBRATION.representative_key(low, [question]) == MAGNITUDE_FREE_CALIBRATION.representative_key(high, [question])
    for effect in (low, high):
        plan = route(
            _features(), assessment=CognitiveImpactAssessment(effects=[effect]), matches=[question],
            decision_strategy=MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
        )
        assert plan.disposition == Disposition.WATCH


def test_magnitude_free_important_challenge_engages_regardless_of_raw_magnitude():
    belief = _match("BELIEF")
    for magnitude in (.01, .99):
        effect = _effect(belief, CognitiveEffectKind.CHALLENGE, change=magnitude, epi=.8, importance=.8)
        plan = route(
            _features(), assessment=CognitiveImpactAssessment(effects=[effect]), matches=[belief],
            decision_strategy=MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
        )
        assert plan.disposition == Disposition.ENGAGE


def test_magnitude_free_low_importance_challenge_stays_aware_regardless_of_raw_magnitude():
    question = _match("QUESTION")
    for magnitude in (.01, .99):
        effect = _effect(question, CognitiveEffectKind.CHALLENGE, change=magnitude, epi=.8, importance=.1)
        plan = route(
            _features(), assessment=CognitiveImpactAssessment(effects=[effect]), matches=[question],
            decision_strategy=MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
        )
        assert plan.disposition == Disposition.AWARE


def test_anchored_open_new_strategy_is_registered_and_fingerprinted():
    strategy = get_decision_strategy("pareto-multidelta-magnitude-free-anchored-open-new")
    assert strategy is ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY
    snapshot = strategy.execution_snapshot()
    assert snapshot["effect_admission"]["version"] == "anchored-open-new-v0.1"
    assert snapshot["effect_admission"]["uses_raw_change_magnitude"] is False


def test_free_floating_open_new_is_rejected_without_jurisdiction_anchor():
    effect = _effect(None, CognitiveEffectKind.OPEN_NEW, change=.99, epi=.9, importance=.9)
    assessment = CognitiveImpactAssessment(effects=[effect])
    baseline = route(
        _features(), assessment=assessment, matches=[],
        decision_strategy=MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    anchored = route(
        _features(), assessment=assessment, matches=[],
        decision_strategy=ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    assert baseline.disposition == Disposition.ENGAGE
    assert anchored.disposition == Disposition.DROP


def test_project_or_structural_match_is_a_jurisdiction_anchor_for_open_new():
    project = _match("PROJECT")
    effect = _effect(None, CognitiveEffectKind.OPEN_NEW, change=.01, epi=.9, importance=.9)
    assert has_jurisdiction_anchor([project])
    admitted = ANCHORED_OPEN_NEW_ADMISSION.admit([effect], [project])
    assert admitted == [effect]
    plan = route(
        _features(), assessment=CognitiveImpactAssessment(effects=[effect]), matches=[project],
        decision_strategy=ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    assert plan.disposition == Disposition.ENGAGE


def test_bare_topic_belief_is_not_sufficient_jurisdiction_anchor():
    belief = _match("BELIEF")
    effect = _effect(None, CognitiveEffectKind.OPEN_NEW, epi=.9, importance=.9)
    assert not has_jurisdiction_anchor([belief])
    assert ANCHORED_OPEN_NEW_ADMISSION.admit([effect], [belief]) == []


def test_anchor_admission_never_removes_targeted_effects():
    belief = _match("BELIEF")
    challenge = _effect(belief, CognitiveEffectKind.CHALLENGE, epi=.8, importance=.8)
    reinforce = _effect(belief, CognitiveEffectKind.REINFORCE, epi=.8, importance=.8)
    assert ANCHORED_OPEN_NEW_ADMISSION.admit([challenge, reinforce], []) == [challenge, reinforce]


def test_cardinal_free_strategy_admits_zero_magnitude_semantic_effect_without_changing_legacy():
    from app.services.pareto_decision_strategy import CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY
    question = _match("QUESTION")
    effect = _effect(question, CognitiveEffectKind.REINFORCE, change=0.0, epi=.8, importance=.8)
    assessment = CognitiveImpactAssessment(effects=[effect])
    legacy = route(
        _features(), assessment=assessment, matches=[question],
        decision_strategy=MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    cardinal_free = route(
        _features(), assessment=assessment, matches=[question],
        decision_strategy=CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY,
    )
    assert legacy.disposition == Disposition.DROP
    assert cardinal_free.disposition == Disposition.WATCH
    snap = CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY.execution_snapshot()
    assert snap["effect_existence"] == "legal-semantic-relation-v0.1"
    assert snap["effect_calibration"]["uses_raw_change_magnitude"] is False


def test_cardinal_free_strategy_is_registered_without_replacing_production_strategy():
    from app.services.pareto_decision_strategy import CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY
    candidate = get_decision_strategy("pareto-multidelta-cardinal-free-anchored-open-new")
    existing = get_decision_strategy("pareto-multidelta-magnitude-free-anchored-open-new")
    assert candidate is CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY
    assert existing is ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY


def test_pareto_public_projection_uses_attention_decision_cause_not_legacy_primary():
    from app.services.cognitive_impact import select_primary_effect

    belief = _match("BELIEF")
    model = _match("MODEL")
    challenge = _effect(
        belief,
        CognitiveEffectKind.CHALLENGE,
        change=.10,
        epi=.8,
        importance=.8,
    )
    high_raw_reinforce = _effect(
        model,
        CognitiveEffectKind.REINFORCE,
        change=.95,
        epi=.8,
        importance=.8,
    )
    assessment = CognitiveImpactAssessment(effects=[challenge, high_raw_reinforce])

    # Legacy single-primary projection would choose the high raw-magnitude reinforce.
    assert select_primary_effect(assessment) is high_raw_reinforce

    strategy = ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY
    plan = route(
        _features(), assessment=assessment, matches=[belief, model], decision_strategy=strategy,
    )
    assert plan.disposition == Disposition.ENGAGE
    assert plan.decision_effect.operation == challenge.operation
    assert plan.decision_effect.target_kernel_node_id == challenge.target_kernel_node_id
    assert plan.decision_effect_bound is True

    visible = strategy.visible_prediction(
        frozen_impact=assessment,
        frozen_matches=[belief, model],
        disposition=plan.disposition,
        decision_cause=plan.decision_effect.as_dict(),
        decision_cause_bound=True,
    )
    assert visible["update"] == {
        "operation": "CHALLENGE",
        "target_node_id": str(belief.node_id),
    }


def test_decision_scope_marks_targeted_effect_as_exact_target():
    question = _match("QUESTION")
    effect = _effect(question, CognitiveEffectKind.REINFORCE, change=.2, epi=.8, importance=.8)
    plan = route(
        _features(),
        assessment=CognitiveImpactAssessment(effects=[effect]),
        matches=[question],
        decision_strategy=ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    assert plan.decision_effect_bound is True
    assert plan.decision_scope_node_ids == [str(question.node_id)]
    assert plan.decision_scope_kind == "TARGET"
    assert plan.decision_scope_provenance == "exact-target"


def test_decision_scope_marks_open_new_global_anchor_as_approximation():
    project = _match("PROJECT")
    belief = _match("BELIEF")
    effect = _effect(None, CognitiveEffectKind.OPEN_NEW, change=.2, epi=.8, importance=.8)
    plan = route(
        _features(),
        assessment=CognitiveImpactAssessment(effects=[effect]),
        matches=[project, belief],
        decision_strategy=ANCHORED_OPEN_NEW_MAGNITUDE_FREE_PARETO_DECISION_STRATEGY,
    )
    assert plan.decision_effect_bound is True
    assert plan.decision_scope_kind == "JURISDICTION"
    assert plan.decision_scope_provenance == "global-locate-jurisdiction-approximation"
    assert plan.decision_scope_node_ids == [str(project.node_id)]
    assert str(belief.node_id) not in plan.decision_scope_node_ids
