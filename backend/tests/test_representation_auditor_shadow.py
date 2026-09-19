from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.event import EventEvidenceFrame, RepresentationAuditRun
from app.models.source import SourceEdge
from app.services.event_evidence_frames import persist_event_evidence_frames
from app.services.ingestion import ingest_text
from app.services.representation_auditor import (
    RepresentationAuditValidationError,
    audit_frame_pair_shadow,
)
from app.services.representation_evidence import build_frame_pair_evidence_bundle
from app.services.representation_snapshot import freeze_representation_snapshot


def _frame(db, source, title, summary):
    rows = persist_event_evidence_frames(
        db,
        source=source,
        extraction=SimpleNamespace(event_title=title, event_summary=summary, evidence_maturity=0.8),
        claims=[],
        observations=[],
        analysis_run_id=None,
        extraction_diagnostics={"mode": "legacy"},
        semantic_provenance={"mode": "LEGACY_EXTRACTION", "authority": "UNAUDITED_LEGACY"},
    )
    assert len(rows) == 1
    return rows[0]


def _fake_chat(payload, calls):
    def chat(messages, **kwargs):
        calls.append((messages, kwargs))
        return payload, {
            "latency_ms": 3,
            "prompt_tokens": 100,
            "completion_tokens": 30,
            "model": "fake-representation-model",
        }
    return chat


def test_evidence_bundle_is_digestible_and_contains_graph_facts(db):
    a = ingest_text(db, "Anthropic scaled CI because coding agents increased test load.", title="CI scaling")
    b = ingest_text(db, "Anthropic described scaling CI under agentic coding load.", title="Scaling CI")
    db.flush()
    fa = _frame(db, a, "Anthropic scales CI", "Anthropic scaled CI for agentic coding.")
    fb = _frame(db, b, "Scaling CI for coding agents", "Anthropic scaled CI for agentic coding.")
    db.add(
        SourceEdge(
            source_id=b.id,
            target_id=a.id,
            relationship="DERIVED_FROM",
            confidence=0.9,
            detected_by="AI",
            evidence="fixture",
        )
    )
    db.flush()

    bundle = build_frame_pair_evidence_bundle(db, fa.id, fb.id)
    kinds = {item["kind"] for item in bundle.payload["evidence"]}
    assert len(bundle.digest) == 64
    assert {"SOURCE_METADATA", "EVENT_FRAME", "EXISTING_SOURCE_GRAPH_FACT"} <= kinds
    assert {"SOURCE_A", "SOURCE_B", "FRAME_A", "FRAME_B"} <= bundle.evidence_ids


def test_shadow_auditor_persists_orthogonal_grounded_judgments_without_representation_mutation(db):
    a = ingest_text(db, "Anthropic scaled CI because coding agents increased test load.", title="CI scaling")
    b = ingest_text(db, "Anthropic described scaling CI under agentic coding load.", title="Scaling CI")
    db.flush()
    fa = _frame(db, a, "Anthropic scales CI", "Anthropic scaled CI for agentic coding.")
    fb = _frame(db, b, "Scaling CI for coding agents", "Anthropic scaled CI for agentic coding.")
    db.add(
        SourceEdge(
            source_id=b.id,
            target_id=a.id,
            relationship="DERIVED_FROM",
            confidence=0.9,
            detected_by="AI",
            evidence="fixture",
        )
    )
    db.flush()

    graph_edge_id = next(
        item["evidence_id"]
        for item in build_frame_pair_evidence_bundle(db, fa.id, fb.id).payload["evidence"]
        if item["kind"] == "EXISTING_SOURCE_GRAPH_FACT"
    )
    response = {
        "event_identity": {
            "value": "SAME_EVENT",
            "support_ids": ["FRAME_A", "FRAME_B"],
            "conflict_ids": [],
            "rationale": "Both frames describe the same CI scaling transition.",
            "missing_evidence": [],
        },
        "provenance_dependency": {
            "value": "DERIVED_FROM",
            "direction": "B_FROM_A",
            "support_ids": [graph_edge_id],
            "conflict_ids": [],
            "rationale": "The existing directed provenance fact supports derivation.",
            "missing_evidence": [],
        },
        "relation_context": {
            "value": "RELATED",
            "support_ids": ["FRAME_A", "FRAME_B"],
            "conflict_ids": [],
            "rationale": "The frames share the same event context.",
            "missing_evidence": [],
        },
    }
    calls = []
    before = freeze_representation_snapshot(db, a)
    audit, trace = audit_frame_pair_shadow(
        db,
        fa.id,
        fb.id,
        chat_fn=_fake_chat(response, calls),
        model="fake-model",
        provider_label="test",
    )
    after = freeze_representation_snapshot(db, a)

    assert len(calls) == 1
    assert audit.authority_result == "SHADOW_ONLY"
    assert audit.proposed_transition == {}
    assert audit.judgments["event_identity"]["value"] == "SAME_EVENT"
    assert audit.judgments["provenance_dependency"]["value"] == "DERIVED_FROM"
    assert trace["bundle_digest"] == audit.input_evidence_digest
    assert before.graph_digest == after.graph_digest
    assert before.decision_representation_digest == after.decision_representation_digest


def test_shadow_auditor_is_idempotent_for_same_bundle_contract_model_and_tag(db):
    a = ingest_text(db, "A body", title="A")
    b = ingest_text(db, "B body", title="B")
    db.flush()
    fa = _frame(db, a, "A event", "A transition.")
    fb = _frame(db, b, "B event", "B transition.")
    response = {
        "event_identity": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "Insufficient evidence.",
            "missing_evidence": ["shared event anchors"],
        },
        "provenance_dependency": {
            "value": "UNKNOWN",
            "direction": "UNKNOWN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "No positive provenance evidence.",
            "missing_evidence": ["explicit provenance"],
        },
        "relation_context": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "Insufficient evidence.",
            "missing_evidence": [],
        },
    }
    calls = []
    first, first_trace = audit_frame_pair_shadow(
        db, fa.id, fb.id, chat_fn=_fake_chat(response, calls), model="fake-model"
    )
    second, second_trace = audit_frame_pair_shadow(
        db, fa.id, fb.id, chat_fn=_fake_chat(response, calls), model="fake-model"
    )
    assert first.id == second.id
    assert len(calls) == 1
    assert first_trace["reused"] is False
    assert second_trace["reused"] is True


def test_shadow_auditor_rejects_unknown_evidence_ids(db):
    a = ingest_text(db, "A body", title="A")
    b = ingest_text(db, "B body", title="B")
    db.flush()
    fa = _frame(db, a, "A event", "A transition.")
    fb = _frame(db, b, "B event", "B transition.")
    response = {
        "event_identity": {
            "value": "SAME_EVENT",
            "support_ids": ["MADE_UP"],
            "conflict_ids": [],
            "rationale": "bad",
            "missing_evidence": [],
        },
        "provenance_dependency": {
            "value": "UNKNOWN",
            "direction": "UNKNOWN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "unknown",
            "missing_evidence": [],
        },
        "relation_context": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "unknown",
            "missing_evidence": [],
        },
    }
    with pytest.raises(RepresentationAuditValidationError, match="unknown evidence"):
        audit_frame_pair_shadow(
            db, fa.id, fb.id, chat_fn=_fake_chat(response, []), model="fake-model"
        )
    assert db.execute(select(RepresentationAuditRun)).scalars().all() == []


def test_same_event_similarity_only_and_independence_without_positive_evidence_fail_closed(db):
    a = ingest_text(db, "same-looking content A", title="Same title")
    b = ingest_text(db, "same-looking content B", title="Same title")
    db.flush()
    fa = _frame(db, a, "Same title", "Similar summary.")
    fb = _frame(db, b, "Same title", "Similar summary.")

    similarity_only = {
        "event_identity": {
            "value": "SAME_EVENT",
            "support_ids": ["PAIR_SIMILARITY"],
            "conflict_ids": [],
            "rationale": "similar",
            "missing_evidence": [],
        },
        "provenance_dependency": {
            "value": "UNKNOWN",
            "direction": "UNKNOWN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "unknown",
            "missing_evidence": [],
        },
        "relation_context": {
            "value": "RELATED",
            "support_ids": ["PAIR_SIMILARITY"],
            "conflict_ids": [],
            "rationale": "related",
            "missing_evidence": [],
        },
    }
    with pytest.raises(RepresentationAuditValidationError, match="SAME_EVENT requires"):
        audit_frame_pair_shadow(
            db, fa.id, fb.id, chat_fn=_fake_chat(similarity_only, []), model="fake-model", run_tag="s"
        )

    unsupported_independent = {
        "event_identity": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "unknown",
            "missing_evidence": [],
        },
        "provenance_dependency": {
            "value": "INDEPENDENT",
            "direction": "NOT_APPLICABLE",
            "support_ids": ["SOURCE_A", "SOURCE_B"],
            "conflict_ids": [],
            "rationale": "different publishers",
            "missing_evidence": [],
        },
        "relation_context": {
            "value": "UNCERTAIN",
            "support_ids": [],
            "conflict_ids": [],
            "rationale": "unknown",
            "missing_evidence": [],
        },
    }
    with pytest.raises(RepresentationAuditValidationError, match="positive independence"):
        audit_frame_pair_shadow(
            db, fa.id, fb.id, chat_fn=_fake_chat(unsupported_independent, []), model="fake-model", run_tag="i"
        )
