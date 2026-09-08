from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.semantic_evidence_batch_v0_1 import SemanticExtractionBatchV0_1
from eval.live.semantic_source_loader_v0_1 import (
    load_dev_manifest,
    load_manifest_source,
)


def _entry(source_id: str):
    manifest = load_dev_manifest()
    return next(item for item in manifest["sources"] if item["id"] == source_id)


def test_dev_corpus_is_13_with_rs15_and_reserves_13_14():
    manifest = load_dev_manifest()
    assert [item["id"] for item in manifest["sources"]] == [*[f"RS{i:02d}" for i in range(1, 13)], "RS15"]
    assert [item["id"] for item in manifest["reserved_unconsumed"]] == ["RS13", "RS14"]


def test_all_development_paths_match_pinned_git_blobs():
    manifest = load_dev_manifest()
    for entry in manifest["sources"]:
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        actual = subprocess.check_output(
            ["git", "hash-object", str(path)],
            cwd=ROOT,
            text=True,
        ).strip()
        assert actual == entry["git_blob_sha"], entry["id"]


def test_text_loader_verifies_blob_and_adds_paragraph_pointers():
    source = load_manifest_source(_entry("RS02"))
    assert source.git_blob_sha == "951a454800cb3e86378f370832ea8e4caee2be8f"
    assert source.page_count is None
    assert source.char_count > 1000
    assert source.rendered_text.startswith("[PARA 0001]")
    assert "[PARA 0002]" in source.rendered_text


def test_pdf_loader_uses_page_pointers_without_ocr():
    # RS04 is deliberately small enough for a lightweight CI PDF-path check.
    source = load_manifest_source(_entry("RS04"))
    assert source.page_count is not None
    assert source.page_count >= 1
    assert source.rendered_text.startswith("[PAGE 0001]")
    assert source.char_count > 0


def test_source_level_batch_allows_zero_event_frames_for_non_event_content():
    batch = SemanticExtractionBatchV0_1.model_validate(
        {
            "batch_id": "RS09-batch",
            "source_ids": ["RS09"],
            "event_frames": [],
            "non_event_units": [
                {
                    "unit_id": "RS09-U1",
                    "statement": "Participants discuss which older language models remain reliable for daily use.",
                    "epistemic_status": "SOURCE_CLAIM",
                    "confidence": "HIGH",
                    "source_id": "RS09",
                    "support_pointer": "PARA 0001",
                    "support_excerpt": "What's your most reliable model",
                    "note": "Discussion content; not forced into an event frame.",
                }
            ],
            "notes": [],
        }
    )
    assert batch.event_frames == []
    assert batch.non_event_units[0].source_id == "RS09"


def test_batch_rejects_unknown_source_for_non_event_unit():
    with pytest.raises(ValidationError):
        SemanticExtractionBatchV0_1.model_validate(
            {
                "batch_id": "bad",
                "source_ids": ["RS09"],
                "event_frames": [],
                "non_event_units": [
                    {
                        "unit_id": "U1",
                        "statement": "A statement",
                        "epistemic_status": "SOURCE_CLAIM",
                        "source_id": "MISSING",
                        "support_pointer": "PARA 0001",
                    }
                ],
            }
        )


def test_batch_rejects_policy_leakage():
    with pytest.raises(ValidationError):
        SemanticExtractionBatchV0_1.model_validate(
            {
                "batch_id": "leak",
                "source_ids": ["RS02"],
                "event_frames": [],
                "non_event_units": [],
                "D": "IN",
            }
        )
