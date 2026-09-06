"""Fresh Collective Attention (P) holdout template integrity tests.

No model calls. No Human Gold. This only validates that the post-freeze fresh
Evidence Packets conform to the frozen v1 sensor boundary and contain no labels.
"""

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

from eval.live.collective_attention_v1 import (
    ESTIMATOR_VERSION,
    EVIDENCE_INTERFACE_VERSION,
    PROFILE_ID,
    PROMPT_VERSION,
    prompt_sha256,
    validate_evidence_packet,
)

TEMPLATE = ROOT / "eval" / "live" / "manifest.collective_attention_final_fresh_validation.v1.template.yaml"


def _load_template():
    raw = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def test_fresh_p_template_has_exact_frozen_provenance_and_no_gold():
    raw = _load_template()
    assert raw["estimator_version"] == ESTIMATOR_VERSION
    assert raw["prompt_version"] == PROMPT_VERSION
    assert raw["profile_id"] == PROFILE_ID
    assert raw["evidence_interface_version"] == EVIDENCE_INTERFACE_VERSION
    assert raw["prompt_sha256"] == prompt_sha256()
    assert raw["status"] == "TEMPLATE_ONLY_HUMAN_GOLD_UNSET"

    text = TEMPLATE.read_text(encoding="utf-8")
    forbidden = (
        "gold_status:",
        "label_provenance:",
        "collective_attention_salience:",
        "human_label:",
    )
    for marker in forbidden:
        assert marker not in text


def test_fresh_p_template_has_12_unique_post_calibration_cases():
    raw = _load_template()
    cases = raw["cases"]
    assert len(cases) == 12
    ids = [case["id"] for case in cases]
    assert ids == [f"PF{i}" for i in range(1, 13)]
    assert len(set(ids)) == 12
    assert not any(case_id.startswith("PC") for case_id in ids)


def test_all_fresh_p_packets_validate_against_frozen_sensor_boundary():
    raw = _load_template()
    for case in raw["cases"]:
        packet = validate_evidence_packet(case["packet"])
        assert packet.event.event_id
        assert packet.event.as_of
        assert packet.event.semantic_summary
        assert packet.constituency_prior.description


def test_fresh_p_primary_set_is_designed_as_scorable_not_missingness_probe():
    raw = _load_template()
    assert raw["pre_registered_criterion"]["expected_scorable_cases"] == 12
    assert raw["pre_registered_criterion"]["insufficient_evidence_should_be_zero"] is True
    for case in raw["cases"]:
        packet = validate_evidence_packet(case["packet"])
        assert len(packet.current_attention_evidence) >= 2
