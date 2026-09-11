from eval.live.run_phase10d6g_native_support_binding_parity_v0_1 import CASES, HISTORICAL_SENTINELS, REPEATS


def test_frozen_sampling_contract():
    assert CASES == ("A", "D", "X", "N4")
    assert REPEATS == 6
    assert HISTORICAL_SENTINELS["N4"] == [
        ("OPEN_NEW", "OPEN_NEW"),
        ("REINFORCE", "B1"),
        ("REINFORCE", "BT1"),
        ("REINFORCE", "M1"),
        ("REINFORCE", "Q1"),
        ("CHALLENGE", "BT1"),
        ("CHALLENGE", "B1"),
    ]
