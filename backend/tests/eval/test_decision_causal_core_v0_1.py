from uuid import uuid4

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import SchedulerFeatures, get_decision_strategy
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core


def match(node_type="BELIEF"):
    return KernelMatch(uuid4(), node_type, node_type, .8, "test", False, "TOPIC")


def effect(m, op, *, magnitude=.5, epi=.8, importance=.8):
    return CognitiveEffect(m.node_id if m else None, op, magnitude, epi, importance, "test", op == CognitiveEffectKind.OPEN_NEW, m.node_type if m else None)


def features():
    return SchedulerFeatures(topic_relevance=.5, structural_relevance=.2, decision_relevance=.2, novelty=.5, credibility=.6, kernel_delta=.2, bottleneck_alignment=.1, disagreement=0, actionability=.3, temporal_value=.3, cognitive_cost=2, evidence_maturity=.6, threatens_active_work=False)


def analyze(effects, matches):
    return analyze_decision_causal_core(
        assessment=CognitiveImpactAssessment(effects=effects), matches=matches, features=features(),
        decision_strategy=get_decision_strategy("pareto-multidelta-magnitude-free-anchored-open-new"),
    )


def test_unique_challenge_is_necessary_and_sufficient_against_watch_reinforce():
    b, q = match("BELIEF"), match("QUESTION")
    c = effect(b, CognitiveEffectKind.CHALLENGE)
    r = effect(q, CognitiveEffectKind.REINFORCE)
    report = analyze([c, r], [b, q])
    by = {row.relation: row for row in report.relations}
    ck = ("CHALLENGE", str(b.node_id)); rk = ("REINFORCE", str(q.node_id))
    assert report.baseline_decision == "ENGAGE"
    assert by[ck].necessary and by[ck].sufficient
    assert not by[rk].necessary and not by[rk].sufficient


def test_redundant_challenges_are_sufficient_but_not_individually_necessary():
    a, b = match("BELIEF"), match("MODEL")
    report = analyze([effect(a, CognitiveEffectKind.CHALLENGE), effect(b, CognitiveEffectKind.CHALLENGE)], [a, b])
    assert report.baseline_decision == "ENGAGE"
    assert report.necessary_core == ()
    assert len(report.sufficient_supports) == 2
    assert {r.classification for r in report.relations} == {"REDUNDANT_LOAD_BEARING"}


def test_weak_ordinary_reinforce_is_peripheral_to_important_challenge():
    b, m = match("BELIEF"), match("MODEL")
    report = analyze([effect(b, CognitiveEffectKind.CHALLENGE), effect(m, CognitiveEffectKind.REINFORCE, epi=.3, importance=.2)], [b, m])
    rows = {r.relation[0]: r for r in report.relations}
    assert rows["REINFORCE"].classification == "PERIPHERAL"


def test_empty_effect_set_has_empty_core():
    report = analyze([], [])
    assert report.baseline_decision == "DROP"
    assert report.necessary_core == () and report.sufficient_supports == ()


def test_magnitude_free_causal_profile_is_invariant_to_raw_magnitude():
    b = match("BELIEF")
    low = analyze([effect(b, CognitiveEffectKind.CHALLENGE, magnitude=.01)], [b])
    high = analyze([effect(b, CognitiveEffectKind.CHALLENGE, magnitude=.99)], [b])
    assert low.as_dict() == high.as_dict()


def test_rejected_relation_cannot_be_sufficient_for_null_drop_baseline():
    open_new = effect(None, CognitiveEffectKind.OPEN_NEW, magnitude=.99, epi=.9, importance=.9)
    report = analyze([open_new], [])
    assert report.baseline_decision == "DROP"
    assert report.necessary_core == ()
    assert report.sufficient_supports == ()
    assert report.relations[0].classification == "PERIPHERAL"


def test_causal_core_respects_cardinal_free_strategy_legality():
    from app.enums import CognitiveEffectKind
    from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
    from app.services.pareto_decision_strategy import CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY
    from app.services.matching import KernelMatch
    from uuid import uuid4
    node_id=uuid4()
    match=KernelMatch(node_id=node_id,node_type="QUESTION",title="Q",score=.8,reason="test",structural=False,relevance_type="TOPIC")
    effect=CognitiveEffect(target_kernel_node_id=node_id,operation=CognitiveEffectKind.REINFORCE,change_magnitude=0.0,epistemic_strength=1.0,target_importance=1.0,reason="test",target_node_type="QUESTION")
    report=analyze_decision_causal_core(assessment=CognitiveImpactAssessment(effects=[effect]),matches=[match],features=features(),decision_strategy=CARDINAL_FREE_ANCHORED_OPEN_NEW_PARETO_DECISION_STRATEGY)
    assert report.baseline_decision == "WATCH"
    assert len(report.relations) == 1
