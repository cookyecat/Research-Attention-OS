from eval.live.cognitive_map_distance_v0_1 import js_divergence_bits, compare_cognitive_maps
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map


def _map(samples):
    return summarize_static_cognitive_map(samples)


def test_js_identical_is_zero():
    assert js_divergence_bits({"WATCH": 1.0}, {"WATCH": 1.0}) == 0


def test_js_disjoint_point_masses_is_one_bit():
    assert js_divergence_bits({"AWARE": 1.0}, {"WATCH": 1.0}) == 1.0


def test_attention_can_be_stable_while_topology_moves():
    a=[{"topology":[("R","A")],"necessary_core":[],"sufficient_supports":[("R","A")],"attention":"WATCH"} for _ in range(4)]
    b=[{"topology":[("R","A"),("R","B")],"necessary_core":[],"sufficient_supports":[("R","A")],"attention":"WATCH"} for _ in range(4)]
    d=compare_cognitive_maps(_map(a),a,_map(b),b)
    assert d["attention_js_bits"] == 0
    assert d["topology_state_js_bits"] == 1.0
    assert d["load_bearing_state_js_bits"] == 0


def test_core_can_move_without_attention_move():
    a=[{"topology":[("R","A")],"necessary_core":[],"sufficient_supports":[("R","A")],"attention":"WATCH"}]
    b=[{"topology":[("R","B")],"necessary_core":[],"sufficient_supports":[("R","B")],"attention":"WATCH"}]
    d=compare_cognitive_maps(_map(a),a,_map(b),b)
    assert d["attention_js_bits"] == 0
    assert d["load_bearing_state_js_bits"] == 1.0


def test_frequency_drift_identifies_changed_relation():
    a=[{"topology":[("R","A")],"necessary_core":[],"sufficient_supports":[("R","A")],"attention":"WATCH"} for _ in range(4)]
    b=[{"topology":[("R","A"),("C","B")],"necessary_core":[],"sufficient_supports":[("C","B")],"attention":"ENGAGE"} for _ in range(4)]
    d=compare_cognitive_maps(_map(a),a,_map(b),b)
    changes=d["load_bearing_relation_frequency_drift"]["top_changes"]
    assert changes[0]["abs_delta"] == 1.0
