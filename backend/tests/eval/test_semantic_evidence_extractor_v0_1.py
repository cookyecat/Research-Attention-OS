import pytest

from eval.live.semantic_evidence_batch_v0_1 import SemanticExtractionBatchV0_1
from eval.live.semantic_evidence_extractor_v0_1 import (
    _validate_source_binding,
    build_messages,
    prompt_sha256,
)
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource


def _source() -> LoadedSemanticSource:
    return LoadedSemanticSource(
        source_id="RSX",
        path="eval_samples/x.txt",
        media_type="text/plain",
        git_blob_sha="abc",
        file_sha256="f" * 64,
        text_sha256="e" * 64,
        char_count=34,
        page_count=None,
        rendered_text="[PARA 0001]\nA source-grounded statement.",
    )


def _batch(locator: str = "eval_samples/x.txt") -> SemanticExtractionBatchV0_1:
    return SemanticExtractionBatchV0_1.model_validate(
        {
            "batch_id": "RSX-semantic-batch-v0.1",
            "source_ids": ["RSX"],
            "event_frames": [
                {
                    "event": {
                        "event_id": "RSX-E1",
                        "as_of": "2026-09-07",
                        "summary": "The source reports a concrete change.",
                    },
                    "sources": [
                        {
                            "source_id": "RSX",
                            "source_type": "text/plain",
                            "published_at": "unknown",
                            "locator": locator,
                        }
                    ],
                    "evidence": [
                        {
                            "evidence_id": "RSX-EV1",
                            "source_id": "RSX",
                            "support_pointer": "PARA 0001",
                            "support_excerpt": "A source-grounded statement.",
                            "epistemic_status": "SOURCE_CLAIM",
                            "confidence": "HIGH",
                        }
                    ],
                    "substantive_actors_objects": [
                        {
                            "name": "Example actor",
                            "role": "actor",
                            "substantive_basis": "The source says the actor made the change.",
                            "support_ids": ["RSX-EV1"],
                        }
                    ],
                    "actions_changes": [
                        {
                            "description": "A concrete change is reported.",
                            "temporal_status": "ANNOUNCED",
                            "support_ids": ["RSX-EV1"],
                        }
                    ],
                    "affected_systems_populations": [],
                    "temporal_context": {
                        "event_time": "unknown",
                        "effective_time": "unknown",
                        "as_of": "2026-09-07",
                        "notes": "",
                    },
                    "uncertainties": [],
                }
            ],
            "non_event_units": [],
            "notes": [],
        }
    )


def test_prompt_is_source_grounded_and_not_truncated():
    source = _source()
    messages = build_messages(source, as_of="2026-09-07")
    user = messages[1]["content"]
    assert source.rendered_text in user
    assert "source_id: RSX" in user
    assert "locator: eval_samples/x.txt" in user
    assert len(prompt_sha256()) == 64


def test_source_binding_accepts_exact_pinned_snapshot():
    _validate_source_binding(_batch(), _source(), as_of="2026-09-07")


def test_source_binding_rejects_model_replacing_locator():
    with pytest.raises(ValueError, match="locator"):
        _validate_source_binding(
            _batch(locator="https://example.com/original"),
            _source(),
            as_of="2026-09-07",
        )
