from __future__ import annotations

from eval.live.run_phase17_jev_recursive_filter_primitives_v0_1 import run


def test_jev_recursive_filter_primitive_sensitivity_is_not_gold_tuned():
    report = run()

    assert report["daily_innovation"] == [3.0, 8.0, 15.0, 8.0, 10.0]
    assert report["full_history_cumulative_baseline"] == [
        3.0,
        11.0,
        26.0,
        34.0,
        44.0,
    ]
    assert report["diagnostics"]["cumulative_is_monotone"] is True
    assert report["diagnostics"]["all_leaky_states_bounded_below_cumulative"] is True

    assert report["leaky_momentum_by_retention_per_day"]["0.25"] == [
        3.0,
        8.75,
        17.1875,
        12.296875,
        13.074219,
    ]
    assert report["leaky_momentum_by_retention_per_day"]["0.50"] == [
        3.0,
        9.5,
        19.75,
        17.875,
        18.9375,
    ]

    boundary = "\n".join(report["interpretation_boundary"]).lower()
    assert "not decision evidence" in boundary
    assert "no retention parameter is selected" in boundary
    assert "no attention labels" in boundary
