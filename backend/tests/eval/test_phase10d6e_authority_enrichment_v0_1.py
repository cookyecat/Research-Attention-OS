from uuid import NAMESPACE_URL, uuid5

from app.enums import CognitiveEffectKind
from app.models.kernel import KernelNode
from app.services.cognitive_impact import CognitiveEffect
from app.services.matching import KernelMatch
from eval.live.phase10d6e_authority_enrichment_v0_1 import enrich_effect, evidence_summary, explicit_importance_band


def node(code, kind, importance=None):
    payload={"phase6b_fixture_code":code}
    if importance is not None: payload["importance"]=importance
    return KernelNode(id=uuid5(NAMESPACE_URL,code),node_type=kind,title=code,status="ACTIVE",payload=payload,current_version=1)


def effect(op, target=None):
    return CognitiveEffect(target_kernel_node_id=target,operation=CognitiveEffectKind(op),change_magnitude=.8,epistemic_strength=.91,target_importance=.93,reason="x")


def test_explicit_importance_and_active_responsibility_policy():
    belief=node("B","BELIEF"); question=node("Q","QUESTION"); explicit=node("E","BELIEF",.9)
    assert explicit_importance_band(explicit)==1
    units=[{"epistemic_status":"SOURCE_CLAIM","supports":[{"source_id":"s1"}]}]
    for n, expected in ((belief,0),(question,1),(explicit,1)):
        e,_=enrich_effect(effect("CHALLENGE",n.id),nodes=[belief,question,explicit],matches=[],units=units,policy="C1_CONSERVATIVE")
        assert e.target_importance==expected
        assert e.epistemic_strength==0.0


def test_open_new_is_source_grounded_but_not_automatically_important():
    goal=node("G","GOAL")
    match=KernelMatch(node_id=goal.id,node_type="GOAL",title="G",score=.9,reason="x",relevance_type="TOPIC")
    units=[{"epistemic_status":"SOURCE_CLAIM","supports":[{"source_id":"s1"}]}]
    e,trace=enrich_effect(effect("OPEN_NEW"),nodes=[goal],matches=[match],units=units,policy="C1_CONSERVATIVE")
    assert e.target_importance==0.0
    assert e.epistemic_strength==1.0
    assert trace["importance_band"]=="LOW"


def test_targeted_relation_needs_direct_or_independent_support_under_c1():
    belief=node("B","BELIEF")
    one=[{"epistemic_status":"SOURCE_CLAIM","supports":[{"source_id":"s1"}]}]
    two=[{"epistemic_status":"SOURCE_CLAIM","supports":[{"source_id":"s1"},{"source_id":"s2"}]}]
    direct=[{"epistemic_status":"DIRECT_OBSERVATION","supports":[{"source_id":"s1"}]}]
    for units,expected in ((one,0.0),(two,1.0),(direct,1.0)):
        e,_=enrich_effect(effect("REINFORCE",belief.id),nodes=[belief],matches=[],units=units,policy="C1_CONSERVATIVE")
        assert e.epistemic_strength==expected


def test_c2_is_explicit_upper_bound_for_auditor_admitted_world():
    belief=node("B","BELIEF")
    units=[{"epistemic_status":"SOURCE_CLAIM","supports":[{"source_id":"s1"}]}]
    e,_=enrich_effect(effect("CHALLENGE",belief.id),nodes=[belief],matches=[],units=units,policy="C2_AUDITOR_TRUST_UPPER_BOUND")
    assert e.epistemic_strength==1.0
    assert evidence_summary(units)["independent_support_sources"]==1
