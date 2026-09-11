from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_SYSTEM_VNEXT


def test_vnext_prompt_removes_stale_single_winner_cardinal_instruction():
    assert "largest useful cognitive change (change_magnitude × target_importance)" in IMPACT_SYSTEM
    assert "largest useful cognitive change (change_magnitude × target_importance)" not in IMPACT_SYSTEM_VNEXT
    assert "Set OPEN_NEW change_magnitude >= 0.55" in IMPACT_SYSTEM
    assert "Set OPEN_NEW change_magnitude >= 0.55" not in IMPACT_SYSTEM_VNEXT
    assert "zero decision authority" in IMPACT_SYSTEM_VNEXT
    assert "do not vote, rank, argmax, or suppress" in IMPACT_SYSTEM_VNEXT


def test_model_provider_defaults_to_legacy_prompt_until_shadow_gate_closes():
    p = ModelBackedCognitiveProvider()
    assert p._impact_system_prompt == IMPACT_SYSTEM
    assert p.impact_contract_version == "production-impact-v2.1-legacy"


def test_model_provider_can_select_reconciled_vnext_prompt_explicitly():
    p = ModelBackedCognitiveProvider(
        impact_system_prompt=IMPACT_SYSTEM_VNEXT,
        impact_contract_version="canonical-impact-vnext-v0.1",
    )
    assert p._impact_system_prompt == IMPACT_SYSTEM_VNEXT
    assert p.impact_contract_version == "canonical-impact-vnext-v0.1"


def test_minimal_pareto_compat_prompt_removes_only_downstream_policy_authority():
    from app.cognitive.prompts import (
        IMPACT_SYSTEM,
        IMPACT_SYSTEM_PARETO_COMPAT,
        _IMPACT_DOWNSTREAM_POLICY_LINES,
    )

    expected = IMPACT_SYSTEM
    for line in _IMPACT_DOWNSTREAM_POLICY_LINES:
        assert line.strip() in IMPACT_SYSTEM
        expected = expected.replace(line, "")
    assert IMPACT_SYSTEM_PARETO_COMPAT == expected
    assert "largest useful cognitive change (change_magnitude × target_importance)" not in IMPACT_SYSTEM_PARETO_COMPAT
    assert "Set OPEN_NEW change_magnitude >= 0.55" not in IMPACT_SYSTEM_PARETO_COMPAT
    # Semantic safeguards remain unchanged; this is not the broader vNext rewrite.
    assert "Scope alignment is required before assigning operation." in IMPACT_SYSTEM_PARETO_COMPAT
    assert "Do not CHALLENGE an existing Belief or Model merely because an alternative route succeeded." in IMPACT_SYSTEM_PARETO_COMPAT
