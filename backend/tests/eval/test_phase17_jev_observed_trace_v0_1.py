from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TRACE = ROOT / "eval/live/fixtures/phase17_jev_observed_world_trace_v0_1.json"


def test_jev_observed_world_trace_is_frozen_sample_not_global_ground_truth():
    trace = json.loads(TRACE.read_text())

    assert trace["contract"] == "jev-observed-world-trace-v0.1"
    assert "not a population-level estimate" in trace["scope"]

    summary = trace["summary"]
    assert summary["deduplicated_external_items"] == 44
    assert summary["domain_counts"] == {
        "weibo.com": 28,
        "www.bilibili.com": 15,
        "frederickparsons.substack.com": 1,
    }
    assert summary["type_counts"] == {
        "POST": 28,
        "VIDEO": 15,
        "ARTICLE": 1,
    }

    assert [row["new_items"] for row in trace["daily"]] == [3, 8, 15, 8, 10]
    assert [row["date"] for row in trace["daily"]] == [
        "2026-09-16",
        "2026-09-17",
        "2026-09-18",
        "2026-09-19",
        "2026-09-20",
    ]


def test_jev_world_trace_and_human_gold_remain_separate_contracts():
    fixture = json.loads(
        (ROOT / "eval/live/fixtures/phase17_jev_longitudinal_v0_1.json").read_text()
    )
    trace = json.loads(TRACE.read_text())

    assert fixture["observed_world_trace_ref"].endswith(
        "phase17_jev_observed_world_trace_v0_1.json"
    )
    assert fixture["human_gold"]["subjective"] is True
    assert fixture["human_gold"]["profile_id"] == "user-primary-v0.1"
    assert fixture["human_gold"]["attention_trajectory"] == [
        "AWARE",
        "WATCH",
        "WATCH",
        "ENGAGE",
    ]

    assert "human_gold" not in trace
    assert all("expected_attention" not in row for row in fixture["epochs"])
