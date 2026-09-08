from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.phase6b_cognitive_semantics_v0_1 import (
    admitted_epistemic_units,
    audit_epistemic_unit_edge,
    project_epistemic_unit_edge,
)


def sample_unit():
    return {
        "unit_id": "RSX-U1",
        "statement": "A supported statement.",
        "epistemic_status": "SOURCE_CLAIM",
        "confidence": "HIGH",
        "supports": [{
            "source_id": "RSX",
            "support_pointer": "PARA 0001",
            "support_excerpt": "A supported statement.",
        }],
    }


def test_projection_preserves_statement_and_evidence_context():
    edge = project_epistemic_unit_edge("RSX", sample_unit())
    assert edge["statement"] == "A supported statement."
    assert edge["supports"][0]["support_pointer"] == "PARA 0001"


def test_binary_audit_admits_only_sufficient_units():
    edge = project_epistemic_unit_edge("RSX", sample_unit())

    def fake_chat(messages, **kwargs):
        return {
            "interface_version": "semantic-evidence-audit-result-v0.1.1",
            "audit_id": edge["audit_id"],
            "verdict": "SUFFICIENT",
            "reason_code": "SUPPORTED",
            "rationale": "Directly supported.",
            "unsupported_aspect": "",
        }, {"model": "fake", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    row = audit_epistemic_unit_edge(edge, chat_fn=fake_chat)
    admitted = admitted_epistemic_units([row])
    assert row["scorable"] is True
    assert admitted[0]["statement"] == edge["statement"]
    assert admitted[0]["supports"] == edge["supports"]


def test_no_support_fails_closed_without_model_call():
    unit = sample_unit()
    unit["supports"] = []
    edge = project_epistemic_unit_edge("RSX", unit)
    row = audit_epistemic_unit_edge(edge, chat_fn=lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    assert row["scorable"] is False
    assert row["failure_kind"] == "no_cited_evidence"
    assert admitted_epistemic_units([row]) == []


def test_adapter_preserves_source_claim_as_claim_not_world_observation():
    from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction
    extraction = audited_units_to_extraction([sample_unit()])
    assert len(extraction.claims) == 1
    assert len(extraction.observations) == 0
    assert extraction.claims[0].attributed_to == "source"
    assert "A supported statement." in extraction.claims[0].text
    assert "A supported statement." in extraction.claims[0].source_span_text


def test_mvp_kernel_is_deterministic_and_contains_update_targets():
    from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
    a = build_phase6b_mvp_kernel_nodes()
    b = build_phase6b_mvp_kernel_nodes()
    assert [n.id for n in a] == [n.id for n in b]
    assert {n.node_type for n in a} >= {"BELIEF", "MODEL", "QUESTION", "BOTTLENECK"}
    assert len(a) == 10
