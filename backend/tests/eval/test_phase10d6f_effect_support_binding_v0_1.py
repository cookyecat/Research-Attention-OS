from uuid import NAMESPACE_URL, uuid5

from app.models.kernel import KernelNode
from app.services.matching import KernelMatch
from eval.live.phase10d6f_effect_support_binding_v0_1 import SupportBoundEffect, effect_key, validate_effect


def node(code, kind):
    return KernelNode(id=uuid5(NAMESPACE_URL, code), node_type=kind, title=code, status="ACTIVE", payload={"phase6b_fixture_code": code}, current_version=1)


def test_targeted_binding_must_use_frozen_support_and_eligible_target():
    belief=node("B1","BELIEF"); match=KernelMatch(node_id=belief.id,node_type="BELIEF",title="B1",score=.9,reason="x",relevance_type="EVIDENCE")
    units=[{"unit_id":"u1"}]
    good=SupportBoundEffect(operation="CHALLENGE",target_kernel_node_id=belief.id,support_unit_ids=["u1"],reason="x")
    assert validate_effect(good,units=units,matches=[match],nodes=[belief])==(True,None)
    bad=SupportBoundEffect(operation="CHALLENGE",target_kernel_node_id=belief.id,support_unit_ids=["missing"],reason="x")
    assert validate_effect(bad,units=units,matches=[match],nodes=[belief])==(False,"UNKNOWN_SUPPORT_UNIT")


def test_open_new_requires_null_target_and_legal_jurisdiction():
    goal=node("G1","GOAL"); match=KernelMatch(node_id=goal.id,node_type="GOAL",title="G1",score=.8,reason="x",relevance_type="TOPIC")
    units=[{"unit_id":"u1"}]
    good=SupportBoundEffect(operation="OPEN_NEW",support_unit_ids=["u1"],jurisdiction_anchor_ids=[goal.id],reason="x")
    assert validate_effect(good,units=units,matches=[match],nodes=[goal])==(True,None)
    no_anchor=SupportBoundEffect(operation="OPEN_NEW",support_unit_ids=["u1"],reason="x")
    assert validate_effect(no_anchor,units=units,matches=[match],nodes=[goal])==(False,"OPEN_NEW_WITHOUT_JURISDICTION")
    assert effect_key(good,nodes=[goal])==("OPEN_NEW",("u1",))
