from eval.live.phase10d6h_cardinal_free_relation_v0_1 import CardinalFreeEffect, SYSTEM_PROMPT
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM


def test_cardinal_free_schema_has_no_effect_level_scores():
    fields = set(CardinalFreeEffect.model_fields)
    assert {"change_magnitude", "epistemic_strength", "target_importance"}.isdisjoint(fields)
    assert {"operation", "target_kernel_node_id", "support_unit_ids", "jurisdiction_anchor_ids", "reason"} <= fields


def test_prompt_preserves_native_semantic_base_without_cardinal_instruction():
    assert SYSTEM_PROMPT.startswith(NATIVE_IMPACT_SYSTEM)
    assert "support_unit_ids" in SYSTEM_PROMPT
    assert "change_magnitude" not in SYSTEM_PROMPT
    assert "target_importance" not in SYSTEM_PROMPT
    assert "epistemic_strength" not in SYSTEM_PROMPT
