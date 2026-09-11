from eval.live.run_phase10d6f_effect_support_binding_v0_1 import CASES, REPEATS
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases


def test_support_binding_measurement_scope_is_frozen():
    assert CASES==('A','D','X','N4')
    assert REPEATS==6
    assert tuple(selected_cases())==CASES
