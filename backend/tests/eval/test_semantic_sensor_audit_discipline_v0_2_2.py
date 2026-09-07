from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.semantic_evidence_extractor_v0_2_2 import (
    build_messages,
    estimate_semantic_evidence_v0_2_2,
    invocation_record,
)
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source


def _source(source_id: str = "RS02"):
    manifest = load_dev_manifest()
    entry = next(item for item in manifest["sources"] if item["id"] == source_id)
    return load_manifest_source(entry)


def _auditable_batch(source):
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
                    "summary": "The source reports high PR activity by Lauren Tan at Cursor.",
                },
                "sources": [
                    {
                        "source_id": source.source_id,
                        "source_type": source.media_type,
                        "published_at": source.published_at,
                        "locator": source.path,
                    }
                ],
                "evidence": [
                    {
                        "evidence_id": "ev-count",
                        "source_id": source.source_id,
                        "support_pointer": "PARA 0004",
                        "support_excerpt": "上个月已经合入了 1000 个 PR。",
                        "epistemic_status": "SOURCE_CLAIM",
                        "confidence": "HIGH",
                    },
                    {
                        "evidence_id": "ev-codebase",
                        "source_id": source.source_id,
                        "support_pointer": "PARA 0005",
                        "support_excerpt": "而是你每天都在使用的 Cursor 的代码。",
                        "epistemic_status": "SOURCE_CLAIM",
                        "confidence": "HIGH",
                    },
                ],
                "substantive_actors_objects": [
                    {
                        "name": "Lauren Tan",
                        "role": "Cursor engineer",
                        "substantive_basis": "The source attributes the PR activity to Lauren Tan at Cursor.",
                        "support_ids": ["ev-count"],
                    }
                ],
                "actions_changes": [
                    {
                        "description": "Merged 1000 PRs in the previous month relative to the source.",
                        "temporal_status": "HISTORICAL",
                        "support_ids": ["ev-count"],
                    }
                ],
                "affected_systems_populations": [
                    {
                        "description": "Cursor codebase",
                        "reference_scope": "The source explicitly identifies the merged code as Cursor code.",
                        "support_ids": ["ev-codebase"],
                    }
                ],
                "temporal_context": {
                    "event_time": "previous month relative to the source; absolute calendar date unresolved",
                    "effective_time": "unknown",
                    "as_of": "2026-09-07",
                    "notes": "measurement time is not used as the source-time anchor",
                },
                "uncertainties": [],
            }
        ],
        "non_event_units": [
            {
                "unit_id": "neu-method",
                "statement": "Lauren Tan believes AI coding is bottlenecked by verification rather than generation.",
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
                "supports": [
                    {
                        "source_id": source.source_id,
                        "support_pointer": "PARA 0007",
                        "support_excerpt": "用 AI coding 最大的问题不是生成代码，而是验证代码。",
                    }
                ],
                "note": "Distinct methodological claim, not a restatement of the PR-count event.",
            }
        ],
        "notes": [],
    }


def test_v0_2_2_prompt_locks_audit_discipline():
    source = _source()
    messages = build_messages(source, as_of="2026-09-07")
    text = "\n".join(message["content"] for message in messages)

    assert "Traceability is not enough" in text
    assert "actually be sufficient" in text
    assert "Do not rely on an uncited nearby paragraph" in text
    assert "Bare URLs" in text
    assert "Never infer what a linked page/video 'presumably contains'" in text
    assert "Do not label your own inference as SOURCE_CLAIM" in text
    assert "Avoid duplicating the same semantic payload" in text


def test_v0_2_2_preserves_v0_2_1_temporal_anchor_rule():
    source = _source()
    messages = build_messages(source, as_of="2026-09-07")
    text = "\n".join(message["content"] for message in messages)

    assert "measurement_as_of is NOT a source-time anchor" in text
    assert "source_published_at: unknown" in text
    assert "Never invent an absolute date merely because measurement_as_of is known." in text


def test_v0_2_2_accepts_first_pass_auditable_output_without_schema_change():
    source = _source()

    def fake_chat(messages, **kwargs):
        return _auditable_batch(source), {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = estimate_semantic_evidence_v0_2_2(
        source,
        as_of="2026-09-07",
        chat_fn=fake_chat,
    )
    assert result["scorable"] is True
    assert result["repair_used"] is False
    frame = result["batch"]["event_frames"][0]
    affected = frame["affected_systems_populations"][0]
    assert affected["support_ids"] == ["ev-codebase"]
    assert len(result["batch"]["non_event_units"]) == 1


def test_v0_2_2_invocation_records_audit_policy():
    record = invocation_record(requested_model="fake", provider_base_url="https://example.test")
    assert record["structured_schema"] == "SemanticExtractionBatchV0_2"
    assert record["temporal_anchor_policy"] == "measurement-time-never-substitutes-source-time-v0.2.1"
    assert record["audit_policy"] == "sufficient-provenance-attribution-locator-dedup-v0.2.2"
