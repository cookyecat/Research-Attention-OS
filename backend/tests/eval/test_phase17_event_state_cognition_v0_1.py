from eval.live.run_phase17_event_state_cognition_v0_1 import run


def test_phase17_event_state_cognition_controlled_gates():
    report = run()
    diag = report["diagnostics"]

    assert diag["all_preregistered_structural_gates_pass"] is True
    assert diag["case_a_preserves_two_support_units"] is True
    assert diag["case_a_independence_correct"] is True
    assert diag["case_b_latest_is_correction_only"] is True
    assert diag["case_b_event_retains_prior_and_correction"] is True
    assert diag["case_b_event_effect_set_richer_than_latest"] is True
    assert diag["case_c_repost_independence_guardrail"] is True

    case_b = report["cases"]["B_MATERIAL_CORRECTION"]
    assert case_b["latest_source"]["disposition"] == "AWARE"
    assert case_b["event_aggregated"]["disposition"] == "ENGAGE"
    assert [
        effect["operation"]
        for effect in case_b["latest_source"]["authorized_effects"]
    ] == ["REINFORCE"]
    assert {
        effect["operation"]
        for effect in case_b["event_aggregated"]["authorized_effects"]
    } == {"CHALLENGE", "REINFORCE"}
