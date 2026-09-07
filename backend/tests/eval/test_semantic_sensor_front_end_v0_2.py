from pathlib import Path

import pytest
from pydantic import ValidationError

from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
from eval.live.semantic_evidence_extractor_v0_2 import (
    build_messages,
    estimate_semantic_evidence_v0_2,
)
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source


def _source(source_id: str):
    manifest = load_dev_manifest()
    entry = next(item for item in manifest["sources"] if item["id"] == source_id)
    return load_manifest_source(entry)


def _valid_batch(source_id="RS02"):
    return {
        "interface_version": "semantic-evidence-batch-v0.2",
        "batch_id": f"{source_id}-semantic-batch-v0.2",
        "source_ids": [source_id],
        "event_frames": [],
        "non_event_units": [
            {
                "unit_id": "U1",
                "statement": "Several passages support one aggregated methodological point.",
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
                "supports": [
                    {"source_id": source_id, "support_pointer": "PARA 0001", "support_excerpt": "first support"},
                    {"source_id": source_id, "support_pointer": "PARA 0002", "support_excerpt": "second support"},
                ],
                "note": "",
            }
        ],
        "notes": [],
    }


def test_v0_2_non_event_unit_supports_multiple_passages():
    batch = SemanticExtractionBatchV0_2.model_validate(_valid_batch())
    assert len(batch.non_event_units[0].supports) == 2


def test_v0_2_executable_limit_matches_prompt_limit():
    raw = _valid_batch()
    raw["non_event_units"] = [
        {
            "unit_id": f"U{i}",
            "statement": "x",
            "epistemic_status": "SOURCE_CLAIM",
            "confidence": "HIGH",
            "supports": [{"source_id": "RS02", "support_pointer": "PARA 0001", "support_excerpt": "x"}],
        }
        for i in range(21)
    ]
    with pytest.raises(ValidationError):
        SemanticExtractionBatchV0_2.model_validate(raw)


def test_v0_2_prompt_exposes_exact_non_event_contract():
    messages = build_messages(_source("RS02"), as_of="2026-09-07")
    text = "\n".join(message["content"] for message in messages)
    assert '"interface_version": "semantic-evidence-batch-v0.2"' in text
    assert '"supports"' in text
    assert "event_frames <= 8" in text
    assert "non_event_units <= 20" in text


def test_v0_2_first_pass_valid_records_no_repair():
    source = _source("RS02")

    def fake_chat(messages, **kwargs):
        return _valid_batch(), {"model": "fake", "prompt_tokens": 1, "completion_tokens": 1, "latency_ms": 1}

    result = estimate_semantic_evidence_v0_2(source, as_of="2026-09-07", chat_fn=fake_chat)
    assert result["scorable"] is True
    assert result["repair_used"] is False
    assert result["model_meta"]["schema_repaired"] is False


def test_v0_2_final_schema_failure_preserves_diagnostics_and_model_meta():
    source = _source("RS02")
    calls = 0

    def fake_chat(messages, **kwargs):
        nonlocal calls
        calls += 1
        return {"source_ids": ["RS02"]}, {"model": "fake", "prompt_tokens": 2, "completion_tokens": 1, "latency_ms": 1}

    result = estimate_semantic_evidence_v0_2(source, as_of="2026-09-07", chat_fn=fake_chat)
    assert calls == 2
    assert result["scorable"] is False
    assert result["failure_kind"] == "schema_validation"
    assert result["repair_used"] is True
    assert len(result["schema_events"]) == 2
    assert result["invalid_raw"] == {"source_ids": ["RS02"]}
    assert result["model_meta"]["model"] == "fake"
    assert result["model_meta"]["prompt_tokens"] == 4
