from eval.live.run_phase10d6h_cardinal_field_removal_parity_v0_1 import CASES, G_STABLE_SENTINELS, REPEATS, SOURCE_G_SHA


def test_frozen_phase10d6h_contract():
    assert CASES == ("A", "D", "X", "N4")
    assert REPEATS == 6
    assert len(SOURCE_G_SHA) == 64
    assert ("REINFORCE", "BT1") in G_STABLE_SENTINELS["N4"]
