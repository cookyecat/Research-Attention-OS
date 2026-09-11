from uuid import NAMESPACE_URL, uuid5

from eval.live.phase10d6g_native_support_binding_v0_1 import (
    NativeSupportBoundEffect,
    SYSTEM_PROMPT,
    normalize_effects,
)
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM


def test_system_prompt_preserves_native_base_contract():
    assert SYSTEM_PROMPT.startswith(NATIVE_IMPACT_SYSTEM)
    assert "support_unit_ids" in SYSTEM_PROMPT
    assert "diagnostic only" in SYSTEM_PROMPT


def test_deterministic_open_new_duplicate_normalization():
    e1 = NativeSupportBoundEffect(
        operation="OPEN_NEW", support_unit_ids=["u2", "u1"], jurisdiction_anchor_ids=[uuid5(NAMESPACE_URL, "a")],
        change_magnitude=.8, epistemic_strength=.7, target_importance=.6, reason="a",
    )
    e2 = NativeSupportBoundEffect(
        operation="OPEN_NEW", support_unit_ids=["u1", "u2"], jurisdiction_anchor_ids=[uuid5(NAMESPACE_URL, "a")],
        change_magnitude=.1, epistemic_strength=.2, target_importance=.3, reason="b",
    )
    assert normalize_effects([e1, e2], nodes=[]) == [e1]
