from eval.live.run_phase10d6l1_support_binding_diagnostic_v0_1 import (
    CASES,
    PROVENANCE_ADDENDUM,
    REPEATS,
    RUN_VERSION,
    assert_prompt_delta,
)


def test_phase10d6l1_support_diagnostic_keeps_primary_prompt_delta():
    assert_prompt_delta()
    assert "support_unit_ids" in PROVENANCE_ADDENDUM
    assert "jurisdiction_anchor_ids" in PROVENANCE_ADDENDUM


def test_phase10d6l1_support_diagnostic_scope_is_frozen():
    assert CASES == ("A", "D", "X", "N4")
    assert REPEATS == 6
    assert RUN_VERSION == "phase10d6l1-support-binding-diagnostic-v0.1"
