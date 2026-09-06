"""Pre-Gold integrity checks for integrated no-Delta AWARE fresh template."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.collective_attention_v1 import CollectiveAttentionEvidencePacketV1
from eval.live.no_delta_awareness_integration_v1 import INTEGRATION_VERSION, POLICY_GATE_VERSION

TEMPLATE = ROOT / "eval" / "live" / "manifest.no_delta_awareness_integrated_fresh.v1.template.yaml"
FREEZE_COMMIT = "c39292be9b4d782391c845368efa7346502be7ec"


def load_template():
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def test_integrated_fresh_template_exact_provenance_and_case_count():
    data = load_template()
    assert data["integration_version"] == INTEGRATION_VERSION
    assert data["policy_gate_version"] == POLICY_GATE_VERSION
    assert data["integration_freeze_commit"] == FREEZE_COMMIT
    cases = data["cases"]
    assert len(cases) == 12
    assert [case["id"] for case in cases] == [f"IA{i}" for i in range(1, 13)]


def test_integrated_fresh_template_has_no_human_or_prediction_labels():
    data = load_template()
    forbidden = {
        "gold",
        "gold_d",
        "gold_s",
        "gold_p",
        "human_disposition",
        "standing_radar_fit",
        "material_consequence",
        "collective_attention_salience",
        "prediction",
        "predicted_disposition",
    }
    for case in data["cases"]:
        assert forbidden.isdisjoint(case.keys())
        assert case["delta"] == "NONE"


def test_all_integrated_p_packets_validate_against_frozen_interface():
    data = load_template()
    for case in data["cases"]:
        packet = CollectiveAttentionEvidencePacketV1.model_validate(case["p_packet"])
        assert packet.event.event_id
        assert packet.event.semantic_summary
        assert packet.current_attention_evidence


def test_event_and_p_packet_are_same_underlying_event_not_label_leakage():
    data = load_template()
    for case in data["cases"]:
        event = case["event"].lower()
        summary = case["p_packet"]["event"]["semantic_summary"].lower()
        assert event.strip()
        assert summary.strip()
        for leak in ("p=", "s=", "d=", "should be aware", "should drop", "salient state"):
            assert leak not in event
            assert leak not in summary
