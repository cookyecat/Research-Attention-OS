from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.semantic_evidence_extractor_v0_2_1 import (
    build_messages,
    estimate_semantic_evidence_v0_2_1,
)
from eval.live.semantic_source_loader_v0_1 import (
    LoadedSemanticSource,
    load_dev_manifest,
    load_manifest_source,
)


def _source(source_id: str = "RS02"):
    manifest = load_dev_manifest()
    entry = next(item for item in manifest["sources"] if item["id"] == source_id)
    return load_manifest_source(entry)


def _event_batch(source: LoadedSemanticSource, *, published_at: str | None = None):
    pinned_published_at = source.published_at if published_at is None else published_at
    return {
        "interface_version": "semantic-evidence-batch-v0.2",
        "batch_id": f"{source.source_id}-semantic-batch-v0.2",
        "source_ids": [source.source_id],
        "event_frames": [
            {
                "interface_version": "semantic-evidence-frame-v0.1",
                "event": {
                    "event_id": "evt-1",
                    "as_of": "2026-09-07",
                    "summary": "The source reports PR activity across the previous and current month.",
                },
                "sources": [
                    {
                        "source_id": source.source_id,
                        "source_type": source.media_type,
                        "published_at": pinned_published_at,
                        "locator": source.path,
                    }
                ],
                "evidence": [
                    {
                        "evidence_id": "ev-1",
                        "source_id": source.source_id,
                        "support_pointer": "PARA 0004",
                        "support_excerpt": "上个月已经合入了 1000 个 PR。这个月才过去 12 天",
                        "epistemic_status": "SOURCE_CLAIM",
                        "confidence": "HIGH",
                    }
                ],
                "substantive_actors_objects": [],
                "actions_changes": [],
                "affected_systems_populations": [],
                "temporal_context": {
                    "event_time": "previous month and first 12 days of current month relative to the source; absolute calendar dates unresolved",
                    "effective_time": "unknown",
                    "as_of": "2026-09-07",
                    "notes": "measurement_as_of is not used as the source-time anchor",
                },
                "uncertainties": [
                    {
                        "field": "absolute calendar dates",
                        "kind": "UNKNOWN",
                        "note": "The pinned source publication time is unknown.",
                        "support_ids": ["ev-1"],
                    }
                ],
            }
        ],
        "non_event_units": [],
        "notes": [],
    }


def test_loader_defaults_missing_source_time_metadata_to_unknown():
    source = _source("RS02")
    assert source.published_at == "unknown"
    assert source.updated_at == "unknown"
    assert source.captured_at == "unknown"


def test_v0_2_1_prompt_explicitly_separates_measurement_and_source_time():
    source = _source("RS02")
    messages = build_messages(source, as_of="2026-09-07")
    text = "\n".join(message["content"] for message in messages)
    assert "measurement_as_of is NOT a source-time anchor" in text
    assert "source_published_at: unknown" in text
    assert "Never invent an absolute date merely because measurement_as_of is known." in text
    assert "preserve the source-relative expression" in text


def test_v0_2_1_accepts_unresolved_source_relative_time_first_pass():
    source = _source("RS02")

    def fake_chat(messages, **kwargs):
        return _event_batch(source), {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = estimate_semantic_evidence_v0_2_1(
        source,
        as_of="2026-09-07",
        chat_fn=fake_chat,
    )
    assert result["scorable"] is True
    assert result["repair_used"] is False
    event_time = result["batch"]["event_frames"][0]["temporal_context"]["event_time"]
    assert "relative to the source" in event_time
    assert "unresolved" in event_time


def test_v0_2_1_rejects_event_source_published_at_mismatch():
    source = _source("RS02")
    calls = 0

    def fake_chat(messages, **kwargs):
        nonlocal calls
        calls += 1
        return _event_batch(source, published_at="2026-09-07"), {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = estimate_semantic_evidence_v0_2_1(
        source,
        as_of="2026-09-07",
        chat_fn=fake_chat,
    )
    assert calls == 2
    assert result["scorable"] is False
    assert result["failure_kind"] == "schema_validation"
    assert result["repair_used"] is True
    assert any(
        "published_at does not match pinned source metadata" in error.get("msg", "")
        for event in result["schema_events"]
        for error in event.get("errors", [])
    )
