from eval.live.topology_stability_metrics_v0_1 import (
    canonical_topology,
    categorical_stability,
    summarize_topology_stability,
)


def test_identical_topologies_are_fully_stable():
    report = summarize_topology_stability([[('R','Q2'), ('R','B2')]] * 6)
    assert report.exact_mode_rate == 1.0
    assert report.mean_pairwise_jaccard == 1.0
    assert report.entropy_bits == 0.0
    assert report.descriptive_instability == 0.0


def test_duplicate_relation_does_not_change_topology():
    assert canonical_topology([('R','Q2'), ('R','Q2')]) == (('R','Q2'),)


def test_critical_recall_is_relation_specific():
    tops = [
        [('R','Q2'), ('R','B2')],
        [('R','Q2')],
        [('R','Q2'), ('R','B2')],
    ]
    report = summarize_topology_stability(tops, critical_relations=[('R','Q2'), ('R','B2')])
    assert report.critical_relation_recall[('R','Q2')] == 1.0
    assert report.critical_relation_recall[('R','B2')] == 2/3
    assert report.mean_pairwise_jaccard < 1.0


def test_empty_topology_is_a_valid_stable_state():
    report = summarize_topology_stability([[], [], []])
    assert report.exact_mode_rate == 1.0
    assert report.mean_pairwise_jaccard == 1.0
    assert report.n_unique == 1


def test_categorical_stability_uses_modal_rate():
    assert categorical_stability(['WATCH','WATCH','AWARE']) == 2/3
