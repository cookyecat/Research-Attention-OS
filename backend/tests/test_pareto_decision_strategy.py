from __future__ import annotations

from uuid import uuid4

from app.enums import CognitiveEffectKind, Disposition
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.pareto_decision_strategy import (
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
