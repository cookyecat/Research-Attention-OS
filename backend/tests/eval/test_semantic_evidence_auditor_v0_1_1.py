from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_semantic_evidence_auditor_real_edges_v0_1_1 import project_provenance_edges
from eval.live.semantic_evidence_auditor_v0_1_1 import (
    SemanticEvidenceAuditResultV0_1_1,
    audit_semantic_evidence_v0_1_1,
    build_messages,
    invocation_record,
)


def _evidence(pointer="PARA 0005", excerpt="这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。"):
    return [
        {
            "source_id": "RS02",
            "support_pointer": pointer,
            "support_excerpt": excerpt,
        }
    ]


def test_binary_prompt_has_no_third_verdict_and_preserves_occam_boundary():
    messages = build_messages(
        audit_id="audit-1",
        object_type="affected_system_population",
        semantic_object="The affected system is the Cursor codebase.",
        evidence=_evidence(),
    )
    text = "\n".join(message["content"] for message in messages)

    # Lock semantic invariants, not incidental prompt typography.
    assert "Binary verdict:" in text
    assert '"verdict": "SUFFICIENT" | "INSUFFICIENT"' in text
    assert "There is NO third verdict" in text
    assert '"verdict": "UNCERTAIN"' not in text
    assert "AMBIGUOUS_REFERENCE" in text
    assert "Do not use outside knowledge" in text
    assert "Do not search for, imagine, or request uncited nearby paragraphs" in text
    assert "Do not propose replacement evidence" in text
    assert "Do not output D, S, P, Delta" in text


def test_result_contract_enforces_decision_diagnosis_consistency():
    ok = SemanticEvidenceAuditResultV0_1_1.model_validate(
        {
            "interface_version": "semantic-evidence-audit-result-v0.1.1",
            "audit_id": "audit-1",
            "verdict": "SUFFICIENT",
            "reason_code": "SUPPORTED",
            "rationale": "The excerpt directly supports the object.",
            "unsupported_aspect": "",
        }
    )
    assert ok.verdict == "SUFFICIENT"

    with pytest.raises(ValidationError):
        SemanticEvidenceAuditResultV0_1_1.model_validate(
            {
                "interface_version": "semantic-evidence-audit-result-v0.1.1",
                "audit_id": "audit-1",
                "verdict": "INSUFFICIENT",
                "reason_code": "SUPPORTED",
                "rationale": "bad consistency",
                "unsupported_aspect": "missing thing",
            }
        )

    with pytest.raises(ValidationError):
        SemanticEvidenceAuditResultV0_1_1.model_validate(
            {
                "interface_version": "semantic-evidence-audit-result-v0.1.1",
                "audit_id": "audit-1",
                "verdict": "SUFFICIENT",
                "reason_code": "SUPPORTED",
                "rationale": "bad consistency",
                "unsupported_aspect": "should be empty",
            }
        )


def test_binary_auditor_accepts_first_pass_insufficient_with_diagnosis():
    def fake_chat(messages, **kwargs):
        return {
            "interface_version": "semantic-evidence-audit-result-v0.1.1",
            "audit_id": "audit-1",
            "verdict": "INSUFFICIENT",
            "reason_code": "MISSING_SUPPORT",
            "rationale": "The excerpt gives PR counts but does not identify the codebase.",
            "unsupported_aspect": "Cursor codebase identity",
        }, {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = audit_semantic_evidence_v0_1_1(
        audit_id="audit-1",
        object_type="affected_system_population",
        semantic_object="The affected system is the Cursor codebase.",
        evidence=_evidence(
            "PARA 0004",
            "上个月已经合入了 1000 个 PR。这个月才过去 12 天，她又合入了接近 800 个。",
        ),
        chat_fn=fake_chat,
    )
    assert result["scorable"] is True
    assert result["repair_used"] is False
    assert result["result"]["verdict"] == "INSUFFICIENT"
    assert result["result"]["reason_code"] == "MISSING_SUPPORT"


def _sensor_artifact():
    return {
        "name": "raos-semantic-evidence-development-run-v0.2.2",
        "sources": [
            {
                "source": {"source_id": "RS02"},
                "batch": {
                    "event_frames": [
                        {
                            "event": {"event_id": "evt-rs02-001"},
                            "evidence": [
                                {
                                    "evidence_id": "ev-rs02-001",
                                    "source_id": "RS02",
                                    "support_pointer": "PARA 0004",
                                    "support_excerpt": "上个月已经合入了 1000 个 PR。",
                                },
                                {
                                    "evidence_id": "ev-rs02-002",
                                    "source_id": "RS02",
                                    "support_pointer": "PARA 0011",
                                    "support_excerpt": "已经有 20 个 PR 自动进入 main。",
                                },
                            ],
                            "substantive_actors_objects": [],
                            "actions_changes": [
                                {
                                    "description": "Merged 1000 PRs in the previous month relative to the source.",
                                    "support_ids": ["ev-rs02-001"],
                                }
                            ],
                            "affected_systems_populations": [
                                {
                                    "description": "Cursor codebase",
                                    "reference_scope": "The codebase of the Cursor product.",
                                    "support_ids": ["ev-rs02-001", "ev-rs02-002"],
                                }
                            ],
                            "uncertainties": [],
                        }
                    ],
                    "non_event_units": [
                        {
                            "unit_id": "neu-rs02-006",
                            "statement": "Lauren Tan believes the biggest problem with AI coding is verification rather than generation.",
                            "supports": [
                                {
                                    "source_id": "RS02",
                                    "support_pointer": "PARA 0007",
                                    "support_excerpt": "她认为，用 AI coding 最大的问题不是生成代码，而是验证代码。",
                                }
                            ],
                        }
                    ],
                },
            }
        ],
    }


def test_real_edge_projection_preserves_actual_sensor_supports():
    edges = project_provenance_edges(_sensor_artifact())
    assert len(edges) == 3

    affected = next(edge for edge in edges if edge["object_type"] == "affected_system_population")
    assert "Cursor codebase" in affected["semantic_object"]
    assert [item["support_pointer"] for item in affected["evidence"]] == ["PARA 0004", "PARA 0011"]

    epistemic = next(edge for edge in edges if edge["object_type"] == "epistemic_unit")
    assert epistemic["evidence"][0]["support_pointer"] == "PARA 0007"


def test_invocation_records_binary_policy():
    record = invocation_record(
        requested_model="fake",
        provider_base_url="https://example.test",
    )
    assert record["structured_schema"] == "SemanticEvidenceAuditResultV0_1_1"
    assert record["decision_policy"] == "binary-sufficiency-v0.1.1"
