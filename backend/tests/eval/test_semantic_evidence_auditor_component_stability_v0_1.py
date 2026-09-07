from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_semantic_evidence_auditor_component_stability_v0_1 import (
    TARGETS,
    build_condition_evidence,
    summarize_trials,
)
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource


def _source():
    return LoadedSemanticSource(
        source_id="RS02",
        path="eval_samples/02_AI_Coding_work_flow.txt",
        media_type="text/plain",
        git_blob_sha="blob",
        file_sha256="file",
        text_sha256="text",
        char_count=100,
        page_count=None,
        rendered_text=(
            "[PARA 0004]\n原始第四段完整内容。\n\n"
            "[PARA 0005]\n绝不能被 PARA 0004 自动取到。\n\n"
            "[PARA 0006]\n前文上下文。Lauren 在视频里讲她怎么走到这一步。"
        ),
        published_at="unknown",
        updated_at="unknown",
        captured_at="unknown",
    )


def _edge(pointer, excerpt):
    return {
        "audit_id": "x",
        "source_id": "RS02",
        "object_type": "epistemic_unit",
        "semantic_object": "object",
        "evidence": [
            {
                "source_id": "RS02",
                "support_pointer": pointer,
                "support_excerpt": excerpt,
            }
        ],
    }


def test_component_study_has_only_three_diagnostic_targets():
    assert set(TARGETS) == {
        "positive_pr_count",
        "temporal_uncertainty",
        "workflow_context",
    }
    assert TARGETS["positive_pr_count"]["conditions"] == ["BASELINE", "METADATA_ONLY"]
    assert TARGETS["temporal_uncertainty"]["conditions"] == ["BASELINE", "METADATA_ONLY"]
    assert TARGETS["workflow_context"]["conditions"] == ["BASELINE", "CONTEXT_ONLY"]


def test_metadata_only_adds_metadata_but_no_context():
    evidence = build_condition_evidence(
        condition="METADATA_ONLY",
        edge=_edge("PARA 0004", "短摘录"),
        source=_source(),
    )
    assert [item["support_pointer"] for item in evidence] == [
        "PARA 0004",
        "TRUSTED_SOURCE_METADATA",
    ]
    assert all("PARA 0005" not in item["support_excerpt"] for item in evidence)


def test_context_only_expands_same_pointer_and_never_adjacent():
    evidence = build_condition_evidence(
        condition="CONTEXT_ONLY",
        edge=_edge("PARA 0006", "Lauren 在视频里讲她怎么走到这一步。"),
        source=_source(),
    )
    assert [item["support_pointer"] for item in evidence] == [
        "PARA 0006",
        "PARA 0006 [FULL CITED CONTAINER]",
    ]
    assert "前文上下文" in evidence[1]["support_excerpt"]
    assert all("PARA 0005" not in item["support_excerpt"] for item in evidence)
    assert all(item["support_pointer"] != "TRUSTED_SOURCE_METADATA" for item in evidence)


def test_summary_keeps_repeat_distribution_not_single_verdict():
    rows = [
        {
            "case": "positive_pr_count",
            "condition": "BASELINE",
            "scorable": True,
            "repair_used": False,
            "audit_result": {"verdict": "SUFFICIENT", "reason_code": "SUPPORTED"},
        },
        {
            "case": "positive_pr_count",
            "condition": "BASELINE",
            "scorable": True,
            "repair_used": False,
            "audit_result": {"verdict": "INSUFFICIENT", "reason_code": "OTHER"},
        },
    ]
    summary = summarize_trials(rows)
    assert summary["positive_pr_count"]["BASELINE"]["verdict_counts"] == {
        "INSUFFICIENT": 1,
        "SUFFICIENT": 1,
    }
