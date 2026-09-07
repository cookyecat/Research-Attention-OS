from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.semantic_evidence_auditor_v0_1_1 import build_messages
from eval.live.semantic_evidence_packet_v0_1 import (
    build_evidence_packet_v0_1,
    packet_kind_counts,
    packet_to_auditor_evidence,
    resolve_cited_container,
)
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source


def _rs02():
    manifest = load_dev_manifest()
    entry = next(item for item in manifest["sources"] if item["id"] == "RS02")
    return load_manifest_source(entry)


def test_resolve_cited_container_returns_exact_paragraph():
    source = _rs02()
    para6 = resolve_cited_container(source, "PARA 0006")
    assert para6 is not None
    assert "很多人，包括 Claude Code 的 Boris" in para6
    assert "Lauren 在这个一小时的视频里" in para6
    assert "这不是 AI slop code" not in para6


def test_packet_expands_only_same_cited_container_not_adjacent_paragraph():
    source = _rs02()
    packet, notes = build_evidence_packet_v0_1(
        source=source,
        primary_evidence=[
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0004",
                "support_excerpt": "上个月已经合入了 1000 个 PR。",
            }
        ],
    )
    combined = "\n".join(item.support_excerpt for item in packet)
    pointers = [item.support_pointer for item in packet]

    assert any("PARA 0004 [FULL CITED CONTAINER]" == pointer for pointer in pointers)
    assert "这不是 AI slop code" not in combined
    assert not any("PARA 0005" in pointer for pointer in pointers)
    assert notes == []


def test_packet_recovers_full_same_paragraph_discourse_context():
    source = _rs02()
    packet, _ = build_evidence_packet_v0_1(
        source=source,
        primary_evidence=[
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0006",
                "support_excerpt": "Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。",
            }
        ],
    )
    context = next(item for item in packet if item.evidence_kind == "CITATION_CONTEXT")
    assert "达到了类似的效率" in context.support_excerpt
    assert "工作方法完整分享" in context.support_excerpt
    assert "Lauren 在这个一小时的视频里" in context.support_excerpt


def test_packet_adds_explicit_trusted_source_metadata():
    source = _rs02()
    packet, _ = build_evidence_packet_v0_1(
        source=source,
        primary_evidence=[
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0004",
                "support_excerpt": "她加入 Cursor 只有五个月。",
            }
        ],
    )
    metadata = next(item for item in packet if item.evidence_kind == "SOURCE_METADATA")
    assert metadata.support_pointer == "TRUSTED_SOURCE_METADATA"
    assert "published_at=unknown" in metadata.support_excerpt
    assert "captured_at=unknown" in metadata.support_excerpt


def test_packet_projection_remains_compatible_with_binary_auditor():
    source = _rs02()
    packet, _ = build_evidence_packet_v0_1(
        source=source,
        primary_evidence=[
            {
                "source_id": "RS02",
                "support_pointer": "PARA 0006",
                "support_excerpt": "Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。",
            }
        ],
    )
    counts = packet_kind_counts(packet)
    assert counts == {
        "PRIMARY_EXCERPT": 1,
        "CITATION_CONTEXT": 1,
        "SOURCE_METADATA": 1,
    }

    evidence = packet_to_auditor_evidence(packet)
    messages = build_messages(
        audit_id="packet-audit-1",
        object_type="epistemic_unit",
        semantic_object="Lauren Tan shared her workflow in a one-hour video.",
        evidence=evidence,
    )
    text = "\n".join(message["content"] for message in messages)
    assert "TRUSTED_SOURCE_METADATA" in text
    assert "PARA 0006 [FULL CITED CONTAINER]" in text
