"""Development tests for no-Delta integration v2 (D v4 uplift only)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.enums import Disposition
from eval.live.no_delta_awareness_integration_v2 import (
    INTEGRATION_VERSION,
    estimate_integrated_no_delta_awareness_v2,
    expected_gate_disposition,
    route_no_delta_from_dsp,
)
from eval.live.standing_radar_fit_v4 import PROFILE_ID


def _p_packet() -> dict:
    return {
        "event": {"event_id": "v2-test", "as_of": "2026-09-08", "semantic_summary": "test"},
        "constituency_prior": {
            "description": "test community", "scope": "domain", "reference_scale": "10^3",
            "reference_size_hint": "unknown", "basis": "explicit_event_scope", "provenance": "test",
        },
        "collection_context": {"channels_checked": ["test"], "channels_unavailable": [], "notes": ""},
        "current_attention_evidence": [{
            "kind": "discussion", "window": "24h", "observation": "many independent humans discussing",
            "source": "test", "observed_at": "2026-09-08", "independence_group": "humans",
            "quality": "direct", "contamination": [],
        }],
        "recent_attention_history": [],
    }


def _d_chat(messages, **kwargs):
    return {
        "standing_radar_fit": "IN", "substantive_anchors": ["AI"],
        "matched_clauses": ["AI systems"], "reason": "in radar",
    }, {"model": "fake-d-v4", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}


def _s_chat(messages, **kwargs):
    return {
        "material_consequence": "MATERIAL", "affected_shared_systems": ["field"],
        "material_changes": ["state change"], "reason": "material",
    }, {"model": "fake-s", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}


def _p_chat(messages, **kwargs):
    return {
        "measurement_status": "scorable", "collective_attention_salience": "NOT_SALIENT",
        "objective_constituency": "test community", "attention_state_summary": "low",
        "inertia_summary": "none", "reason": "not salient",
    }, {"model": "fake-p", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}


def test_v2_identifies_d_v4_binding_and_preserves_gate():
    assert INTEGRATION_VERSION == "no-delta-awareness-integration-v2-d-v4"
    assert PROFILE_ID == "standing-radar-profile-v4"
    assert expected_gate_disposition("IN", "MATERIAL", "NOT_SALIENT") == Disposition.AWARE
    assert route_no_delta_from_dsp("OUT", "MATERIAL", "NOT_SALIENT").disposition == Disposition.DROP


def test_v2_composes_d_v4_s_v1_p_v1_without_rejudging():
    out = estimate_integrated_no_delta_awareness_v2(
        "AI event",
        _p_packet(),
        d_chat_fn=_d_chat,
        s_chat_fn=_s_chat,
        p_chat_fn=_p_chat,
    )
    assert out["scorable"] is True
    assert out["labels"] == {"D": "IN", "S": "MATERIAL", "P": "NOT_SALIENT"}
    assert out["disposition"] == "AWARE"
    assert out["gate_wiring_matches"] is True
