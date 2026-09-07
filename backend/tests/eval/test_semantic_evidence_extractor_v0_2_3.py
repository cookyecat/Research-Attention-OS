from __future__ import annotations

import pytest

from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
from eval.live.semantic_evidence_extractor_v0_2_3 import (
    MAX_NON_EVENT_UNITS,
    MAX_SUPPORTS_PER_NON_EVENT_UNIT,
    _validate_compression_policy,
    build_messages,
    estimate_semantic_evidence_v0_2_3,
    invocation_record,
)
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource


def _source() -> LoadedSemanticSource:
    text = "[PARA 0001]\nA source says one thing.\n\n[PARA 0002]\nIt gives an example."
    return LoadedSemanticSource(
        source_id="RSX",
        path="eval_samples/x.txt",
        media_type="text/plain",
        git_blob_sha="abc",
        file_sha256="file",
        text_sha256="text",
        char_count=len(text),
        page_count=None,
        rendered_text=text,
        published_at="unknown",
        updated_at="unknown",
        captured_at="unknown",
    )


def _unit(idx: int, *, n_supports: int = 1) -> dict:
    return {
        "unit_id": f"u{idx}",
        "statement": f"Independent semantic point {idx}.",
        "epistemic_status": "SOURCE_CLAIM",
        "confidence": "HIGH",
        "supports": [
            {
                "source_id": "RSX",
                "support_pointer": "PARA 0001",
                "support_excerpt": f"support {j}",
            }
            for j in range(n_supports)
        ],
        "note": "",
    }


def _batch(n_units: int = 1, *, supports_per_unit: int = 1) -> dict:
    return {
        "interface_version": "semantic-evidence-batch-v0.2",
        "batch_id": "RSX-semantic-batch-v0.2",
        "source_ids": ["RSX"],
        "event_frames": [],
        "non_event_units": [
            _unit(i, n_supports=supports_per_unit) for i in range(1, n_units + 1)
        ],
        "notes": [],
    }


def test_prompt_encodes_semantic_independence_not_attention_policy():
    text = "\n".join(message["content"] for message in build_messages(_source(), as_of="2026-09-07"))
    assert "MINIMAL SUFFICIENT" in text
    assert "If deleting a candidate unit does NOT remove an independent meaning, merge it." in text
    assert "Never output D, S, P, Delta" in text
    assert "user relevance" in text
    assert "Never exceed 12" in text


def test_compression_policy_rejects_more_than_twelve_units():
    obj = SemanticExtractionBatchV0_2.model_validate(_batch(MAX_NON_EVENT_UNITS + 1))
    with pytest.raises(ValueError, match="at most 12 non-event units"):
        _validate_compression_policy(obj)


def test_compression_policy_rejects_more_than_four_supports_per_unit():
    obj = SemanticExtractionBatchV0_2.model_validate(
        _batch(1, supports_per_unit=MAX_SUPPORTS_PER_NON_EVENT_UNIT + 1)
    )
    with pytest.raises(ValueError, match="at most 4 supports"):
        _validate_compression_policy(obj)


def test_first_pass_valid_candidate_is_scorable_without_repair():
    def fake_chat(messages, **kwargs):
        return _batch(2), {
            "latency_ms": 10,
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "model": "fake",
        }

    result = estimate_semantic_evidence_v0_2_3(
        _source(),
        as_of="2026-09-07",
        chat_fn=fake_chat,
    )
    assert result["scorable"] is True
    assert result["repair_used"] is False
    assert len(result["batch"]["non_event_units"]) == 2
    assert result["model_meta"]["schema_repaired"] is False


def test_invocation_records_minimal_sufficient_policy():
    record = invocation_record(
        requested_model="deepseek-v4-flash",
        provider_base_url="https://api.deepseek.com",
    )
    assert record["extractor_version"] == "semantic-evidence-extractor-v0.2.3"
    assert record["compression_policy"] == "minimal-sufficient-semantic-basis-v0.2.3"
    assert record["max_non_event_units"] == 12
    assert record["max_supports_per_non_event_unit"] == 4
