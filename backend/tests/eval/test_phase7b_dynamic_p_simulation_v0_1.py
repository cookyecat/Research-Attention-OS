from __future__ import annotations

from eval.live.collective_attention_v1 import validate_evidence_packet
from eval.live.phase7b_dynamic_p_simulation_v0_1 import all_dynamic_p_steps


def test_phase7b_dynamic_p_simulation_shape_and_gold_path():
    steps = all_dynamic_p_steps()
    assert len(steps) == 10
    for step in steps:
        validate_evidence_packet(step.packet)
        assert step.expected_p in {"SALIENT", "NOT_SALIENT"}
        assert step.expected_action in {"AWARE", "DROP"}
        assert "SIMULATED DEVELOPMENT EVIDENCE ONLY" in step.packet["collection_context"]["notes"]

    specialist = [s for s in steps if s.scenario_id == "specialist_cycle"]
    assert [s.expected_p for s in specialist] == [
        "NOT_SALIENT", "SALIENT", "SALIENT", "SALIENT", "NOT_SALIENT", "SALIENT"
    ]
    assert [s.expected_action for s in specialist] == ["DROP", "AWARE", "AWARE", "AWARE", "DROP", "AWARE"]


def test_phase7b_manipulated_exposure_does_not_define_p():
    steps = [s for s in all_dynamic_p_steps() if s.scenario_id == "manipulated_to_organic"]
    assert [s.expected_p for s in steps] == ["NOT_SALIENT", "NOT_SALIENT", "SALIENT", "SALIENT"]
    first = steps[0].packet["current_attention_evidence"][0]
    assert set(first["contamination"]) == {"paid", "forced_exposure"}
