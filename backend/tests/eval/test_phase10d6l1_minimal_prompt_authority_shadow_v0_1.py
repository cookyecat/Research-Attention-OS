from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_SYSTEM_PARETO_COMPAT, _IMPACT_DOWNSTREAM_POLICY_LINES
from eval.live.run_phase10d6l1_minimal_prompt_authority_shadow_v0_1 import (
    CASES,
    REPEATS,
    RUN_VERSION,
    STRATEGY_ID,
    assert_prompt_delta,
)


def test_phase10d6l1_contract_is_deletion_only():
    assert_prompt_delta()
    expected = IMPACT_SYSTEM
    for line in _IMPACT_DOWNSTREAM_POLICY_LINES:
        expected = expected.replace(line, "")
    assert IMPACT_SYSTEM_PARETO_COMPAT == expected


def test_phase10d6l1_measurement_scope_is_frozen():
    assert CASES == ("A", "D", "X", "N4")
    assert REPEATS == 6
    assert STRATEGY_ID == "pareto-multidelta-magnitude-free-anchored-open-new"
    assert RUN_VERSION == "phase10d6l1-minimal-prompt-authority-shadow-v0.1"
