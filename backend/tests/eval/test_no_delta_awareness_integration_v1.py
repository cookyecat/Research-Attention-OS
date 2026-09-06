"""Integrated no-Delta AWARE composition tests."""

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

from app.enums import Disposition
from eval.live.no_delta_awareness_integration_v1 import (
    INTEGRATION_VERSION,
    POLICY_GATE_VERSION,
    awareness_signals_from_dsp,
    estimate_integrated_no_delta_awareness_v1,
    expected_gate_disposition,
    route_no_delta_from_dsp,
)


def sample_p_packet() -> dict:
    return {
        "event": {
            "event_id": "integration-test",
            "as_of": "2026-09-07T00:00:00Z",
            "semantic_summary": "A test event.",
        },
        "constituency_prior": {
            "description": "relevant professional community",
            "scope": "domain",
            "reference_scale": "10^4",
            "reference_size_hint": "unknown",
            "basis": "explicit_event_scope",
            "provenance": "integration test",
        },
        "collection_context": {
            "channels_checked": ["manual_structural_evidence"],
            "channels_unavailable": [],
            "notes": "integration test",
        },
        "current_attention_evidence": [
            {
                "kind": "human_discussion",
                "window": "last 24h",
                "observation": "Many independent members are discussing the event.",
                "source": "integration test",
                "observed_at": "2026-09-07T00:00:00Z",
                "independence_group": "humans",
                "quality": "direct",
                "contamination": [],
            }
        ],
        "recent_attention_history": [],
    }


@pytest.mark.parametrize(
    "d,s,p",
    [
        ("OUT", "NOT_MATERIAL", "NOT_SALIENT"),
        ("OUT", "NOT_MATERIAL", "SALIENT"),
        ("IN", "NOT_MATERIAL", "NOT_SALIENT"),
        ("IN", "NOT_MATERIAL", "SALIENT"),
        ("OUT", "MATERIAL", "NOT_SALIENT"),
        ("OUT", "MATERIAL", "SALIENT"),
        ("IN", "MATERIAL", "NOT_SALIENT"),
        ("IN", "MATERIAL", "SALIENT"),
    ],
)
def test_all_eight_truth_table_rows_match_frozen_gate_and_real_scheduler(d, s, p):
    expected = expected_gate_disposition(d, s, p)
    draft = route_no_delta_from_dsp(d, s, p)
    assert draft.disposition == expected
    assert draft.disposition in {Disposition.DROP, Disposition.AWARE}


def test_awareness_signal_mapping_is_exactly_d_s_p():
    sig = awareness_signals_from_dsp("IN", "MATERIAL", "SALIENT")
    assert sig.domain_fit is True
    assert sig.event_significance is True
    assert sig.attention_momentum is True

    sig = awareness_signals_from_dsp("OUT", "NOT_MATERIAL", "NOT_SALIENT")
    assert sig.domain_fit is False
    assert sig.event_significance is False
    assert sig.attention_momentum is False


def test_gate_requires_s_even_when_d_or_p_is_true():
    assert expected_gate_disposition("IN", "NOT_MATERIAL", "NOT_SALIENT") == Disposition.DROP
    assert expected_gate_disposition("OUT", "NOT_MATERIAL", "SALIENT") == Disposition.DROP
    assert expected_gate_disposition("IN", "NOT_MATERIAL", "SALIENT") == Disposition.DROP


def test_gate_accepts_either_d_or_p_when_s_is_material():
    assert expected_gate_disposition("IN", "MATERIAL", "NOT_SALIENT") == Disposition.AWARE
    assert expected_gate_disposition("OUT", "MATERIAL", "SALIENT") == Disposition.AWARE
    assert expected_gate_disposition("IN", "MATERIAL", "SALIENT") == Disposition.AWARE
    assert expected_gate_disposition("OUT", "MATERIAL", "NOT_SALIENT") == Disposition.DROP


def test_integrated_estimator_composes_components_without_rejudging_semantics():
    def d_chat(messages, **kwargs):
        return {
            "standing_radar_fit": "OUT",
            "substantive_anchors": ["unmonitored field"],
            "matched_clauses": [],
            "reason": "outside standing radar",
        }, {"model": "fake-d", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    def s_chat(messages, **kwargs):
        return {
            "material_consequence": "MATERIAL",
            "affected_shared_systems": ["industry"],
            "material_changes": ["industry state changed"],
            "reason": "material shared-system change",
        }, {"model": "fake-s", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    def p_chat(messages, **kwargs):
        return {
            "measurement_status": "scorable",
            "collective_attention_salience": "SALIENT",
            "objective_constituency": "relevant professional community",
            "attention_state_summary": "broad genuine uptake",
            "inertia_summary": "current salience established",
            "reason": "high constituency-relative attention",
        }, {"model": "fake-p", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_integrated_no_delta_awareness_v1(
        "A test event.",
        sample_p_packet(),
        d_chat_fn=d_chat,
        s_chat_fn=s_chat,
        p_chat_fn=p_chat,
    )
    assert out["scorable"] is True
    assert out["labels"] == {"D": "OUT", "S": "MATERIAL", "P": "SALIENT"}
    assert out["disposition"] == Disposition.AWARE.value
    assert out["gate_wiring_matches"] is True
    assert out["integration_version"] == INTEGRATION_VERSION
    assert out["policy_gate_version"] == POLICY_GATE_VERSION


def test_component_failure_prevents_final_disposition():
    def d_chat(messages, **kwargs):
        return {
            "standing_radar_fit": "IN",
            "substantive_anchors": ["AI"],
            "matched_clauses": ["AI systems"],
            "reason": "in radar",
        }, {"model": "fake-d", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    def s_chat(messages, **kwargs):
        return {
            "material_consequence": "MATERIAL",
            "affected_shared_systems": ["industry"],
            "material_changes": ["change"],
            "reason": "material",
        }, {"model": "fake-s", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    def p_chat(messages, **kwargs):
        return {
            "measurement_status": "insufficient_evidence",
            "collective_attention_salience": None,
            "objective_constituency": "community",
            "attention_state_summary": "missing current evidence",
            "inertia_summary": "unknown",
            "reason": "insufficient evidence",
        }, {"model": "fake-p", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_integrated_no_delta_awareness_v1(
        "A test event.",
        sample_p_packet(),
        d_chat_fn=d_chat,
        s_chat_fn=s_chat,
        p_chat_fn=p_chat,
    )
    assert out["scorable"] is False
    assert out["disposition"] is None
    assert out["component_scorable"] == {"D": True, "S": True, "P": False}


def test_invalid_labels_are_rejected():
    with pytest.raises(ValueError):
        awareness_signals_from_dsp("MAYBE", "MATERIAL", "SALIENT")
