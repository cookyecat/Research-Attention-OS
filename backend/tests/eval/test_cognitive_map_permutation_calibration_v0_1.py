from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate
from eval.live.cognitive_map_distance_v0_1 import attention_distribution, js_divergence_bits


def _att_js(a,b):
    return js_divergence_bits(attention_distribution(a), attention_distribution(b))


def test_identical_labels_do_not_support_drift():
    a=[{"attention":"WATCH"} for _ in range(4)]
    b=[{"attention":"WATCH"} for _ in range(8)]
    r=permutation_calibrate(a,b,statistic=_att_js,permutations=200,seed=1)
    assert r["observed"] == 0
    assert r["drift_supported_v0_1"] is False


def test_disjoint_labels_support_drift_against_permutation_null():
    a=[{"attention":"AWARE"} for _ in range(6)]
    b=[{"attention":"WATCH"} for _ in range(12)]
    r=permutation_calibrate(a,b,statistic=_att_js,permutations=1000,seed=2)
    assert r["observed"] == 1.0
    assert r["exceeds_null_p95"] is True
    assert r["drift_supported_v0_1"] is True


def test_fixed_seed_is_reproducible():
    a=[{"attention":"WATCH"} for _ in range(3)]
    b=[{"attention":"WATCH"} for _ in range(3)]+[{"attention":"ENGAGE"} for _ in range(3)]
    x=permutation_calibrate(a,b,statistic=_att_js,permutations=100,seed=7)
    y=permutation_calibrate(a,b,statistic=_att_js,permutations=100,seed=7)
    assert x == y
