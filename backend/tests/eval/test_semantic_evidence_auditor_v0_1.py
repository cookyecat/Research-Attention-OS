from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_semantic_evidence_auditor_dev_v0_1 import (
    CONTROLLED_CASES,
    _rs02_source,
    _verify_case_supports_exist,
)
from eval.live.semantic_evidence_auditor_v0_1 import (
    audit_semantic_evidence_v0_1,
    build_messages,
    invocation_record,
)


def _evidence():
    return [
        {
            "source_id": "RS02",
            "support_pointer": "PARA 0005",
            "support_excerpt": "这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。",
        }
    ]


def test_auditor_prompt_preserves_occam_boundary():
    messages = build_messages(
        audit_id="audit-1",
        object_type="affected_system_population",
        semantic_object="The affected system is the Cursor codebase.",
        evidence=_evidence(),
    )
    text = "\n".join(message["content"] for message in messages)

    assert "semantic object <- cited evidence excerpts" in text
    assert "Do not use outside knowledge" in text
    assert "Do not search for, imagine, or request uncited nearby paragraphs" in text
    assert "Do not repair or rewrite the semantic object" in text
    assert "Do not propose replacement evidence" in text
    assert "SUFFICIENT" in text
    assert "INSUFFICIENT" in text
    assert "UNCERTAIN" in text
    assert "missing support is INSUFFICIENT" in text
    assert "Do not output D, S, P, Delta" in text


def test_auditor_accepts_first_pass_valid_result():
    def fake_chat(messages, **kwargs):
        return {
            "interface_version": "semantic-evidence-audit-result-v0.1",
            "audit_id": "audit-1",
            "verdict": "SUFFICIENT",
            "rationale": "The excerpt explicitly identifies the code as Cursor code.",
            "unsupported_or_uncertain_aspect": "",
        }, {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = audit_semantic_evidence_v0_1(
        audit_id="audit-1",
        object_type="affected_system_population",
        semantic_object="The affected system is the Cursor codebase.",
        evidence=_evidence(),
        chat_fn=fake_chat,
    )
    assert result["scorable"] is True
    assert result["repair_used"] is False
    assert result["result"]["verdict"] == "SUFFICIENT"


def test_auditor_repairs_structurally_invalid_first_output_once():
    calls = 0

    def fake_chat(messages, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "interface_version": "semantic-evidence-audit-result-v0.1",
                "audit_id": "audit-1",
                "verdict": "MAYBE",
                "rationale": "invalid enum for test",
                "unsupported_or_uncertain_aspect": "",
            }, {
                "model": "fake",
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "latency_ms": 1,
            }
        return {
            "interface_version": "semantic-evidence-audit-result-v0.1",
            "audit_id": "audit-1",
            "verdict": "INSUFFICIENT",
            "rationale": "The excerpt does not identify the affected codebase.",
            "unsupported_or_uncertain_aspect": "Cursor codebase identity",
        }, {
            "model": "fake",
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "latency_ms": 1,
        }

    result = audit_semantic_evidence_v0_1(
        audit_id="audit-1",
        object_type="affected_system_population",
        semantic_object="The affected system is the Cursor codebase.",
        evidence=_evidence(),
        chat_fn=fake_chat,
    )
    assert calls == 2
    assert result["scorable"] is True
    assert result["repair_used"] is True
    assert result["result"]["verdict"] == "INSUFFICIENT"
    assert result["schema_events"][0]["status"] == "invalid"
    assert result["schema_events"][1]["status"] == "repaired"


def test_controlled_cases_are_pinned_and_cover_three_verdicts():
    source = _rs02_source()
    _verify_case_supports_exist(source)

    assert [case["human_gold"] for case in CONTROLLED_CASES] == [
        "SUFFICIENT",
        "INSUFFICIENT",
        "UNCERTAIN",
    ]
    assert all(case["evidence"] for case in CONTROLLED_CASES)
    assert all(
        support["support_excerpt"] in source.rendered_text
        for case in CONTROLLED_CASES
        for support in case["evidence"]
    )


def test_invocation_records_narrow_audit_scope():
    record = invocation_record(
        requested_model="fake",
        provider_base_url="https://example.test",
    )
    assert record["structured_schema"] == "SemanticEvidenceAuditResultV0_1"
    assert record["audit_scope"] == "one-semantic-object-vs-cited-evidence-only"
