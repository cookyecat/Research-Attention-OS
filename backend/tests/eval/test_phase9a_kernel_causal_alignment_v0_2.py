import pytest
from pydantic import ValidationError

from app.enums import CognitiveEffectKind
from eval.live.phase9a_kernel_causal_alignment_v0_2 import (
    ASSIMILATED_PROPOSITION, RelationEffect, RelationResponse, SYSTEM_PROMPT, TARGET_CODE,
    authorize_relations, frozen_rs05_match, materialize_rs05_arm, relation_user_prompt,
    target_node, target_polarity_state, validate_relation,
)
from eval.live.run_phase9a_kernel_causal_alignment_v0_2 import downstream_sample, load_rs05_units, paired_importance_gate
from app.services.scheduler import get_decision_strategy


def test_relation_only_schema_rejects_downstream_authority_fields():
    with pytest.raises(ValidationError):
        RelationResponse.model_validate({"effects": [{
            "operation": "CHALLENGE", "target_kernel_node_id": None, "reason": "x", "target_importance": 1.0,
        }]})
    for forbidden in ("change_magnitude", "epistemic_strength", "target_importance", "support_unit_ids", "jurisdiction_anchor_ids"):
        assert forbidden not in RelationEffect.model_fields


def test_phase9a_materialization_and_relation_payload_isolation():
    units = load_rs05_units()
    k0, ks, ki = (materialize_rs05_arm(x) for x in ("K0", "K1-S", "K1-I"))
    t0, ts, ti = target_node(k0.nodes), target_node(ks.nodes), target_node(ki.nodes)
    assert t0.id == ts.id == ti.id
    assert ts.title == ASSIMILATED_PROPOSITION
    assert ts.payload["importance"] == 0.9
    assert ti.title == t0.title
    assert ti.payload["proposition"] == t0.payload["proposition"]
    assert ti.payload["importance"] == 0.2
    p0 = relation_user_prompt(units, frozen_rs05_match(k0.nodes), k0.nodes)
    ps = relation_user_prompt(units, frozen_rs05_match(ks.nodes), ks.nodes)
    pi = relation_user_prompt(units, frozen_rs05_match(ki.nodes), ki.nodes)
    assert p0 == pi
    assert p0 != ps
    assert '"importance"' not in p0


def _effect(arm, operation):
    return RelationEffect(operation=operation, target_kernel_node_id=target_node(arm.nodes).id, reason="test")


def test_phase9a_preregistered_grounding_authority_direction():
    k0, ks, ki = (materialize_rs05_arm(x) for x in ("K0", "K1-S", "K1-I"))
    a0, tr0 = authorize_relations([_effect(k0, "CHALLENGE")], arm="K0", nodes=k0.nodes)
    a1, tr1 = authorize_relations([_effect(ks, "REINFORCE")], arm="K1-S", nodes=ks.nodes)
    ai, tri = authorize_relations([_effect(ki, "CHALLENGE")], arm="K1-I", nodes=ki.nodes)
    assert a0.effects[0].operation == CognitiveEffectKind.CHALLENGE and a0.effects[0].target_importance == 0.9
    assert a1.effects[0].operation == CognitiveEffectKind.REINFORCE and a1.effects[0].target_importance == 0.9
    assert ai.effects[0].operation == CognitiveEffectKind.CHALLENGE and ai.effects[0].target_importance == 0.2
    assert tr0[0]["epistemic_band"] == tr1[0]["epistemic_band"] == tri[0]["epistemic_band"] == "SUFFICIENT"
    rejected, traces = authorize_relations([_effect(ks, "CHALLENGE")], arm="K1-S", nodes=ks.nodes)
    assert not rejected.effects and traces[0]["keep"] is False


def test_phase9a_downstream_mechanistic_channels_match_preregistration():
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-anchored-open-new")
    cases = [("K0", "CHALLENGE", "ENGAGE"), ("K1-S", "REINFORCE", "AWARE"), ("K1-I", "CHALLENGE", "AWARE")]
    for arm_name, operation, expected in cases:
        arm = materialize_rs05_arm(arm_name)
        raw = {
            "ordinal": 1, "relation_source_arm": arm_name, "status": "OK", "raw_target_polarity": f"{operation}_ONLY",
            "raw_topology": [(operation, TARGET_CODE)], "normalized_objects": [_effect(arm, operation)],
            "raw_effects": [], "normalized_effects": [], "invalid_effects": [], "meta": {}, "schema_events": [],
        }
        row = downstream_sample(raw, arm_name=arm_name, arm=arm, strategy=strategy)
        assert row["attention"] == expected


def test_target_polarity_and_unknown_target_validation():
    arm = materialize_rs05_arm("K0")
    challenge = _effect(arm, "CHALLENGE")
    reinforce = _effect(arm, "REINFORCE")
    assert target_polarity_state([challenge], arm.nodes) == "CHALLENGE_ONLY"
    assert target_polarity_state([reinforce], arm.nodes) == "REINFORCE_ONLY"
    assert target_polarity_state([challenge, reinforce], arm.nodes) == "BOTH"
    assert target_polarity_state([], arm.nodes) == "NONE"
    wrong = RelationEffect(operation="CHALLENGE", target_kernel_node_id="00000000-0000-0000-0000-000000000001", reason="x")
    ok, reason = validate_relation(wrong, arm.nodes)
    assert not ok and reason == "TARGET_NOT_FROZEN_CF_B_PERF"


def test_k0_k1i_paired_gate_requires_identical_topology_and_engage_to_aware():
    k0 = [{"ordinal": 1, "raw_topology": [("CHALLENGE", TARGET_CODE)], "raw_target_polarity": "CHALLENGE_ONLY", "topology": [("CHALLENGE", TARGET_CODE)], "attention": "ENGAGE"}]
    ki = [{"ordinal": 1, "raw_topology": [("CHALLENGE", TARGET_CODE)], "raw_target_polarity": "CHALLENGE_ONLY", "topology": [("CHALLENGE", TARGET_CODE)], "attention": "AWARE"}]
    result = paired_importance_gate(k0, ki)
    assert result["gate_pass"] is True
    ki[0]["topology"] = []
    assert paired_importance_gate(k0, ki)["gate_pass"] is False


def test_system_prompt_does_not_assign_downstream_policy():
    assert "DROP/AWARE/WATCH/ENGAGE" not in SYSTEM_PROMPT
    assert "public update" in SYSTEM_PROMPT
    assert "Do not vote, rank" in SYSTEM_PROMPT
