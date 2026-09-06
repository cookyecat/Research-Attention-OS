"""Collective Attention Salience (P) estimator v1 tests."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

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
    SYSTEM_PROMPT,
    CollectiveAttentionEvidencePacketV1,
    CollectiveAttentionV1Response,
    build_messages,
    compute_collective_attention_metrics,
    estimate_collective_attention_v1,
    load_collective_attention_profile,
    prompt_sha256,
    render_packet_for_prompt,
    render_profile_for_prompt,
)


def sample_packet() -> dict:
    return {
        "event": {
            "event_id": "p-test-1",
            "as_of": "2026-09-07T00:00:00Z",
            "semantic_summary": "A specialist AI-safety technique was released.",
        },
        "constituency_prior": {
            "description": "active AI-safety research and industry community",
            "scope": "domain",
            "reference_scale": "10^4",
            "reference_size_hint": "unknown",
            "basis": "llm_prior",
            "provenance": "frozen test prior",
        },
        "collection_context": {
            "channels_checked": ["manual_structural_evidence"],
            "channels_unavailable": ["x_internal_telemetry"],
            "notes": "controlled test packet",
        },
        "current_attention_evidence": [
            {
                "kind": "institutional_followup",
                "window": "last 24h",
                "observation": "most major labs in the field issued public responses",
                "source": "frozen synthetic test evidence",
                "observed_at": "2026-09-07T00:00:00Z",
                "independence_group": "field_labs",
                "quality": "structural",
                "contamination": [],
            }
        ],
        "recent_attention_history": [],
    }


def test_p_v1_versions_and_prompt_hash():
    assert ESTIMATOR_VERSION == "collective-attention-estimator-v1"
    assert PROMPT_VERSION == "collective-attention-v1"
    assert PROFILE_ID == "collective-attention-profile-v1"
    assert EVIDENCE_INTERFACE_VERSION == "collective-attention-evidence-packet-v1"
    assert len(prompt_sha256()) == 64


def test_p_v1_prompt_encodes_frozen_semantics_and_orthogonality():
    blob = SYSTEM_PROMPT
    assert "Objective Attention Constituency" in blob
    assert "relative to that constituency's scale" in blob
    assert "Raw absolute" in blob
    assert "temporal inertia" in blob
    assert "unavailable channels as unknown, not zero" in blob
    assert "user personally cares (D)" in blob
    assert "intrinsically important/material (S)" in blob
    assert "Do not browse" in blob


def test_p_v1_profile_contains_only_p_semantic_fields():
    profile = load_collective_attention_profile()
    assert set(profile) == {
        "semantic_contract",
        "constituency_principles",
        "attention_evidence_principles",
        "temporal_principles",
        "orthogonality_and_missingness",
    }
    dumped = render_profile_for_prompt(profile)
    assert "Objective Attention Constituency" in dumped
    assert "Raw absolute volume is not P" in dumped
    assert "Unavailable evidence is unknown, not zero" in dumped


def test_p_v1_evidence_packet_schema_forbids_semantic_leakage_fields():
    packet = sample_packet()
    obj = CollectiveAttentionEvidencePacketV1.model_validate(packet)
    assert obj.event.event_id == "p-test-1"

    bad = dict(packet)
    bad["predicted_P"] = "SALIENT"
    with pytest.raises(ValidationError):
        CollectiveAttentionEvidencePacketV1.model_validate(bad)

    bad_event = sample_packet()
    bad_event["event"] = dict(bad_event["event"])
    bad_event["event"]["material_consequence"] = "MATERIAL"
    with pytest.raises(ValidationError):
        CollectiveAttentionEvidencePacketV1.model_validate(bad_event)


def test_p_v1_packet_preserves_unknown_vs_zero_collection_context():
    dumped = render_packet_for_prompt(sample_packet())
    assert "x_internal_telemetry" in dumped
    assert "channels_unavailable" in dumped
    assert "manual_structural_evidence" in dumped


def test_p_v1_prompt_does_not_leak_development_case_ids():
    messages = build_messages(sample_packet(), load_collective_attention_profile())
    blob = "\n".join(m["content"] for m in messages)
    for marker in ("PC1", "PC8", "PC12", "PC15", "PC21", "PC24"):
        assert marker not in blob


def test_p_v1_response_requires_label_iff_scorable():
    obj = CollectiveAttentionV1Response.model_validate(
        {
            "measurement_status": "scorable",
            "collective_attention_salience": "SALIENT",
            "objective_constituency": "AI-safety community",
            "attention_state_summary": "broad field uptake",
            "inertia_summary": "no decay evidence",
            "reason": "high penetration",
        }
    )
    assert obj.collective_attention_salience == "SALIENT"

    insufficient = CollectiveAttentionV1Response.model_validate(
        {
            "measurement_status": "insufficient_evidence",
            "collective_attention_salience": None,
            "objective_constituency": "AI-safety community",
            "attention_state_summary": "current evidence missing",
            "inertia_summary": "history unavailable",
            "reason": "cannot observe current attention",
        }
    )
    assert insufficient.collective_attention_salience is None

    with pytest.raises(ValidationError):
        CollectiveAttentionV1Response.model_validate(
            {
                "measurement_status": "insufficient_evidence",
                "collective_attention_salience": "NOT_SALIENT",
                "objective_constituency": "x",
                "attention_state_summary": "x",
                "inertia_summary": "x",
                "reason": "x",
            }
        )


def test_p_v1_estimator_scorable_and_insufficient_evidence_paths():
    def salient_chat(messages, **kwargs):
        return {
            "measurement_status": "scorable",
            "collective_attention_salience": "SALIENT",
            "objective_constituency": "AI-safety community",
            "attention_state_summary": "major field actors are attending",
            "inertia_summary": "no evidence of sustained decay",
            "reason": "high constituency-relative attention",
        }, {"model": "fake-p-v1", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_collective_attention_v1(sample_packet(), chat_fn=salient_chat)
    assert out["scorable"] is True
    assert out["measurement_status"] == "scorable"
    assert out["collective_attention_salience"] == "SALIENT"

    def insufficient_chat(messages, **kwargs):
        return {
            "measurement_status": "insufficient_evidence",
            "collective_attention_salience": None,
            "objective_constituency": "AI-safety community",
            "attention_state_summary": "no current observations",
            "inertia_summary": "no history",
            "reason": "current attention cannot be inferred",
        }, {"model": "fake-p-v1", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    insufficient = estimate_collective_attention_v1(sample_packet(), chat_fn=insufficient_chat)
    assert insufficient["scorable"] is False
    assert insufficient["measurement_status"] == "insufficient_evidence"
    assert insufficient["collective_attention_salience"] is None
    assert insufficient["failure_kind"] == "insufficient_evidence"


def test_p_v1_invalid_packet_fails_before_model_call():
    called = False

    def should_not_call(messages, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("model should not be called")

    bad = sample_packet()
    bad["event"] = dict(bad["event"])
    bad["event"]["D"] = True
    out = estimate_collective_attention_v1(bad, chat_fn=should_not_call)
    assert called is False
    assert out["scorable"] is False
    assert out["failure_kind"] == "invalid_packet"
    assert out["collective_attention_salience"] is None


def test_p_v1_estimator_provider_failure_fails_closed():
    from app.cognitive.client import LLMError

    def boom(messages, **kwargs):
        raise LLMError("provider 503 unavailable")

    failed = estimate_collective_attention_v1(sample_packet(), chat_fn=boom)
    assert failed["scorable"] is False
    assert failed["measurement_status"] == "technical_failure"
    assert failed["collective_attention_salience"] is None


def test_p_v1_metrics_have_no_embedded_success_gate():
    rows = [
        {"scorable": True, "gold": "SALIENT", "prediction": "SALIENT"},
        {"scorable": True, "gold": "NOT_SALIENT", "prediction": "NOT_SALIENT"},
        {"scorable": True, "gold": "SALIENT", "prediction": "NOT_SALIENT"},
    ]
    metrics = compute_collective_attention_metrics(rows)
    assert metrics["n_scored"] == 3
    assert metrics["exact_accuracy"] == pytest.approx(2 / 3)
    assert metrics["salient_recall"] == pytest.approx(0.5)
    assert metrics["not_salient_recall"] == pytest.approx(1.0)
    assert "success_criterion" not in metrics
    assert "metrics_pass" not in metrics


def test_p_v1_is_eval_only_and_direct_not_mandatory_numeric_pipeline():
    source = inspect.getsource(estimate_collective_attention_v1)
    assert "scheduler" not in source
    assert "theta_on" not in source
    assert "theta_off" not in source
    assert "weighted_score" not in source
