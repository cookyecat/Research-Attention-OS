from types import SimpleNamespace
from uuid import uuid4

from eval.live.run_phase10d6l3_decoupled_support_binding_v0_1 import (
    BindingItem, BindingResponse, SYSTEM_PROMPT, frozen_relations, validate_bindings,
)


def test_binder_contract_cannot_emit_operation_or_target():
    fields = BindingItem.model_fields
    assert set(fields) == {"relation_id", "support_unit_ids", "jurisdiction_anchor_ids", "reason"}
    assert "must not add, remove, merge, retarget" in SYSTEM_PROMPT


def test_frozen_relations_preserve_operation_and_target_from_source():
    sample = {"sample_id": "P1-1", "effects": [{"operation": "REINFORCE", "target_kernel_node_id": "abc", "reason": "r"}]}
    rows = frozen_relations("X", sample)
    assert rows == [{"relation_id": "X:P1-1:1", "operation": "REINFORCE", "target_kernel_node_id": "abc", "reason": "r"}]


def test_validation_accepts_exact_known_binding_and_rejects_unknown_support():
    anchor = uuid4()
    relations = [{"relation_id": "r1", "operation": "REINFORCE", "target_kernel_node_id": str(anchor), "reason": "r"}]
    units = [{"unit_id": "u1"}]
    matches = [SimpleNamespace(node_id=anchor)]
    good = BindingResponse(bindings=[BindingItem(relation_id="r1", support_unit_ids=["u1"], jurisdiction_anchor_ids=[])])
    ok, errors = validate_bindings(parsed=good, relations=relations, units=units, matches=matches)
    assert ok and not errors
    bad = BindingResponse(bindings=[BindingItem(relation_id="r1", support_unit_ids=["missing"], jurisdiction_anchor_ids=[])])
    ok, errors = validate_bindings(parsed=bad, relations=relations, units=units, matches=matches)
    assert not ok and "UNKNOWN_SUPPORT:r1" in errors


def test_validation_rejects_relation_id_set_drift_and_targeted_jurisdiction():
    anchor = uuid4()
    relations = [{"relation_id": "r1", "operation": "CHALLENGE", "target_kernel_node_id": str(anchor), "reason": "r"}]
    units = [{"unit_id": "u1"}]
    matches = [SimpleNamespace(node_id=anchor)]
    parsed = BindingResponse(bindings=[BindingItem(relation_id="other", support_unit_ids=["u1"], jurisdiction_anchor_ids=[anchor])])
    ok, errors = validate_bindings(parsed=parsed, relations=relations, units=units, matches=matches)
    assert not ok
    assert "RELATION_ID_SET_MISMATCH" in errors
