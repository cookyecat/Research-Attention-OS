from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, wilson_interval


def test_wilson_interval_is_bounded_and_contains_empirical_rate():
    lo, hi = wilson_interval(5, 10)
    assert 0 <= lo < .5 < hi <= 1


def test_stable_attention_and_topology_have_zero_entropy():
    samples = [
        {"topology": [("R", "Q1")], "necessary_core": [("R", "Q1")], "sufficient_supports": [("R", "Q1")], "attention": "WATCH"}
        for _ in range(6)
    ]
    m = summarize_static_cognitive_map(samples)
    assert m["topology_distribution"]["entropy_bits"] == 0
    assert m["load_bearing_distribution"]["entropy_bits"] == 0
    assert m["attention_distribution"]["entropy_bits"] == 0
    assert m["attention_distribution"]["concentration"] == 1


def test_frequency_does_not_imply_load_bearing_probability():
    samples = [
        {"topology": [("R", "COMMON"), ("C", "WALL")], "necessary_core": [("C", "WALL")], "sufficient_supports": [("C", "WALL")], "attention": "ENGAGE"}
        for _ in range(4)
    ]
    m = summarize_static_cognitive_map(samples)
    assert m["relation_map"][repr(("R", "COMMON"))]["topology"]["p"] == 1
    assert m["relation_map"][repr(("R", "COMMON"))]["load_bearing"]["p"] == 0
    assert m["relation_map"][repr(("C", "WALL"))]["load_bearing"]["p"] == 1


def test_redundant_sufficient_support_counts_as_load_bearing():
    samples = [{
        "topology": [("C", "B1"), ("C", "Q1")],
        "necessary_core": [],
        "sufficient_supports": [("C", "B1"), ("C", "Q1")],
        "attention": "ENGAGE",
    }]
    m = summarize_static_cognitive_map(samples)
    assert m["relation_map"][repr(("C", "B1"))]["necessary"]["p"] == 0
    assert m["relation_map"][repr(("C", "B1"))]["load_bearing"]["p"] == 1


def test_attention_distribution_reports_mixed_basin():
    samples = [
        {"topology": [], "necessary_core": [], "sufficient_supports": [], "attention": a}
        for a in ["WATCH", "WATCH", "ENGAGE", "ENGAGE"]
    ]
    m = summarize_static_cognitive_map(samples)
    assert m["attention_distribution"]["counts"] == {"ENGAGE": 2, "WATCH": 2}
    assert m["attention_distribution"]["entropy_bits"] == 1.0
    assert m["attention_distribution"]["concentration"] == .5


def test_branch_relations_remain_distinct():
    samples = [{
        "topology": [("OPEN_NEW", ("N11",)), ("OPEN_NEW", ("N10",))],
        "necessary_core": [("OPEN_NEW", ("N11",))],
        "sufficient_supports": [("OPEN_NEW", ("N11",))],
        "attention": "WATCH",
    }]
    m = summarize_static_cognitive_map(samples)
    assert len(m["relation_map"]) == 2
