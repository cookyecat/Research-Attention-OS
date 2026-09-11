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
