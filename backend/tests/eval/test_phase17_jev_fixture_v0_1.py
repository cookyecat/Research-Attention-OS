from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "eval/live/fixtures/phase17_jev_longitudinal_v0_1.json"


def test_jev_longitudinal_fixture_contract_is_frozen():
    fixture = json.loads(FIXTURE.read_text())

    assert fixture["contract"] == "jev-longitudinal-benchmark-v0.1"
    assert fixture["human_gold"]["subjective"] is True
    assert fixture["human_gold"]["profile_id"] == "user-primary-v0.1"
    assert fixture["human_gold"]["attention_trajectory"] == [
        "AWARE",
        "WATCH",
        "WATCH",
        "ENGAGE",
    ]
    assert fixture["observed_world_trace_ref"] == (
        "eval/live/fixtures/phase17_jev_observed_world_trace_v0_1.json"
    )

    epochs = fixture["epochs"]
    assert [row["epoch"] for row in epochs] == ["t0", "t1", "t2", "t3"]
    assert all(row["expected_relation_to_event"] == "SAME_EVENT" for row in epochs)

    for row in epochs:
        assert isinstance(row["world_state_delta"], dict)
        assert isinstance(row["evidence_state_delta"], dict)
        assert row["source_description"].strip()


def test_jev_fixture_uses_only_minimal_state_axes():
    fixture = json.loads(FIXTURE.read_text())

    allowed_epoch_keys = {
        "epoch",
        "source_label",
        "source_description",
        "world_state_delta",
        "evidence_state_delta",
        "expected_relation_to_event",
    }
    for row in fixture["epochs"]:
        assert set(row) == allowed_epoch_keys

    # Update-algorithm-specific labels must not leak into the Event benchmark
    # state contract. They may be inferred internally by a candidate U.
    serialized = json.dumps(fixture["epochs"], ensure_ascii=False).lower()
    for forbidden in (
        '"correction"',
        '"supersession"',
        '"enrichment"',
        '"contradiction"',
    ):
        assert forbidden not in serialized
