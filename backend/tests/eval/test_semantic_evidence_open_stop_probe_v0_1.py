from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.semantic_evidence_open_stop_probe_v0_1 import (
    MAX_TOKENS,
    SemanticExtractionOpenStopBatchV0_1,
    build_messages,
)
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource


def _source():
    text = "[PARA 0001]\nA principle.\n\n[PARA 0002]\nAn example of the same principle."
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


def _unit(i):
    return {
        "unit_id": f"u{i}",
        "statement": f"Independent point {i}",
        "epistemic_status": "SOURCE_CLAIM",
        "confidence": "HIGH",
        "supports": [{
            "source_id": "RSX",
            "support_pointer": "PARA 0001",
            "support_excerpt": "A principle.",
        }],
        "note": "",
    }


def test_prompt_has_open_semantic_stop_and_no_numeric_unit_target():
    text = "\n".join(m["content"] for m in build_messages(_source(), as_of="2026-09-07"))
    assert "There is no desired unit count" in text
    assert "Stop only when every remaining substantive passage" in text
    assert "6-10" not in text
    assert "Never exceed 12" not in text
    assert "hard cap 12" not in text.lower()


def test_open_stop_schema_does_not_reintroduce_twenty_unit_cap():
    obj = SemanticExtractionOpenStopBatchV0_1.model_validate({
        "interface_version": "semantic-evidence-batch-v0.2",
        "batch_id": "RSX-semantic-batch-v0.2",
        "source_ids": ["RSX"],
        "event_frames": [],
        "non_event_units": [_unit(i) for i in range(1, 26)],
        "notes": [],
    })
    assert len(obj.non_event_units) == 25


def test_probe_transport_headroom_is_explicitly_16k():
    assert MAX_TOKENS == 16384
