"""Tests for the integrated no-Delta AWARE attribution runner."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_no_delta_awareness_integration_v1_eval import (
    DEFAULT_GOLD,
    DEFAULT_TEMPLATE,
    FRESH_TEMPLATE_COMMIT,
    HUMAN_GOLD_COMMIT,
    INTEGRATION_FREEZE_COMMIT,
    compute_integrated_metrics,
    load_joined_cases,
    run_integrated_v1,
    validate_provenance,
)


def test_integrated_runner_frozen_provenance_and_case_join():
    template, gold, joined = load_joined_cases(DEFAULT_TEMPLATE, DEFAULT_GOLD)
    validate_provenance(template, gold)
    assert len(joined) == 12
    assert [x["template"]["id"] for x in joined] == [f"IA{i}" for i in range(1, 13)]
    assert gold["fresh_template_commit"] == FRESH_TEMPLATE_COMMIT
    assert gold["integration_freeze_commit"] == INTEGRATION_FREEZE_COMMIT
    assert len(HUMAN_GOLD_COMMIT) == 40


def test_integrated_human_gate_consistency_is_preserved_not_repaired():
    template, gold, joined = load_joined_cases(DEFAULT_TEMPLATE, DEFAULT_GOLD)
    rows = []
    from eval.live.no_delta_awareness_integration_v1 import expected_gate_disposition

    for item in joined:
        g = item["gold"]
        rows.append({
            "case_id": item["template"]["id"],
            "gold_D": g["D"],
            "gold_S": g["S"],
            "gold_P": g["P"],
            "gold_final": g["final"],
            "human_gate_final": expected_gate_disposition(g["D"], g["S"], g["P"]).value,
            "pred_D": g["D"],
            "pred_S": g["S"],
            "pred_P": g["P"],
            "pred_final": expected_gate_disposition(g["D"], g["S"], g["P"]).value,
            "D_correct": True,
            "S_correct": True,
            "P_correct": True,
            "final_correct": expected_gate_disposition(g["D"], g["S"], g["P"]).value == g["final"],
            "any_component_error": False,
            "gate_wiring_matches": True,
        })

    metrics = compute_integrated_metrics(rows)
    assert metrics["human_gate_consistency"]["exact"] == 10
    assert metrics["human_gate_consistency"]["accuracy"] == pytest.approx(10 / 12)
    assert metrics["human_gate_consistency"]["mismatch_cases"] == ["IA4", "IA12"]
    assert metrics["final"]["exact_accuracy"] == pytest.approx(10 / 12)


def test_integrated_runner_dry_run_makes_no_model_calls():
    called = {"D": 0, "S": 0, "P": 0}

    def d_chat(*args, **kwargs):
        called["D"] += 1
        raise AssertionError("D model should not be called during dry run")

    def s_chat(*args, **kwargs):
        called["S"] += 1
        raise AssertionError("S model should not be called during dry run")

    def p_chat(*args, **kwargs):
        called["P"] += 1
        raise AssertionError("P model should not be called during dry run")

    out = run_integrated_v1(
        DEFAULT_TEMPLATE,
        DEFAULT_GOLD,
        dry_run=True,
        d_chat_fn=d_chat,
        s_chat_fn=s_chat,
        p_chat_fn=p_chat,
    )
    assert out["n_cases"] == 12
    assert out["metrics"] is None
    assert called == {"D": 0, "S": 0, "P": 0}
    assert all(row.get("dry_run") is True for row in out["cases"])


def test_integrated_metrics_record_masked_and_causal_errors_separately():
    rows = [
        {
            "case_id": "A",
            "gold_D": "IN", "pred_D": "OUT",
            "gold_S": "NOT_MATERIAL", "pred_S": "NOT_MATERIAL",
            "gold_P": "NOT_SALIENT", "pred_P": "NOT_SALIENT",
            "gold_final": "DROP", "pred_final": "DROP",
            "human_gate_final": "DROP",
            "D_correct": False, "S_correct": True, "P_correct": True,
            "final_correct": True, "any_component_error": True,
            "gate_wiring_matches": True,
        },
        {
            "case_id": "B",
            "gold_D": "IN", "pred_D": "OUT",
            "gold_S": "MATERIAL", "pred_S": "MATERIAL",
            "gold_P": "NOT_SALIENT", "pred_P": "NOT_SALIENT",
            "gold_final": "AWARE", "pred_final": "DROP",
            "human_gate_final": "AWARE",
            "D_correct": False, "S_correct": True, "P_correct": True,
            "final_correct": False, "any_component_error": True,
            "gate_wiring_matches": True,
        },
    ]
    metrics = compute_integrated_metrics(rows)
    assert metrics["masked_component_error_cases"] == ["A"]
    assert metrics["causal_final_error_cases"] == ["B"]
    assert metrics["wiring_mismatch_cases"] == []
    assert metrics["final"]["false_drop_count"] == 1


def test_integrated_runner_provenance_mismatch_fails_closed():
    template, gold, _ = load_joined_cases(DEFAULT_TEMPLATE, DEFAULT_GOLD)
    bad = dict(template)
    bad["integration_version"] = "wrong-version"
    with pytest.raises(ValueError, match="provenance mismatch"):
        validate_provenance(bad, gold)
