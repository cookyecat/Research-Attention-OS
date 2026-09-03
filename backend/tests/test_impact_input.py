"""Frozen Impact input identity, EXACT vs RECONSTRUCTED, fingerprint coverage."""

from __future__ import annotations

from uuid import uuid4

from app.models.kernel import KernelNode
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.impact_input import (
    FIDELITY_EXACT,
    capture_impact_input,
    fingerprint_snapshot,
    freeze_kernel_target,
    stored_is_exact,
)
from app.services.matching import KernelMatch
from app.enums import ClaimType


def _extraction() -> ExtractionResult:
    result = ExtractionResult(event_title="t", marketing_heavy=False, evidence_maturity=0.4)
    result.claims.append(ExtractedClaim(text="latency matters", claim_type=ClaimType.TECHNICAL))
    return result


def _node(*, proposition: str, title: str = "Motor Intelligence") -> KernelNode:
    node = KernelNode(
        node_type="BELIEF",
        title=title,
        status="ACTIVE",
        payload={"proposition": proposition, "scope": "embodied-control", "importance": 0.8},
        current_version=1,
    )
    node.id = uuid4()
    return node


def test_fingerprint_covers_kernel_target_semantics():
    node = _node(proposition="original proposition")
    match = KernelMatch(
        node_id=node.id,
        node_type="BELIEF",
        title=node.title,
        score=0.7,
        reason="topic",
        structural=False,
        relevance_type="TOPIC",
    )
    frozen = capture_impact_input(
        source_text="paper text",
        extraction=_extraction(),
        matches=[match],
        nodes=[node],
        is_duplicate=False,
        independent_source_count=1,
        secondary_report_count=0,
        analysis_run_id=str(uuid4()),
    )
    assert frozen["input_fidelity"] == FIDELITY_EXACT
    assert stored_is_exact(frozen)
    assert frozen["kernel_targets"][0]["proposition"] == "original proposition"
    assert frozen["kernel_targets"][0]["scope"] == "embodied-control"
    assert frozen["kernel_targets"][0]["id"] == str(node.id)
    baseline = frozen["input_fingerprint"]

    drifted = dict(frozen)
    drifted["kernel_targets"] = [
        {**frozen["kernel_targets"][0], "proposition": "later edited proposition", "scope": "new-scope"}
    ]
    assert fingerprint_snapshot(drifted) != baseline

    same_label_fields = dict(frozen)
    same_label_fields["analysis_run_id"] = str(uuid4())
    same_label_fields["input_hash"] = "other"
    same_label_fields["original_stages"] = {"raw_effects": [{"operation": "OPEN_NEW"}]}
    assert fingerprint_snapshot(same_label_fields) == baseline


def test_fingerprint_covers_source_text_and_extraction():
    node = _node(proposition="p")
    match = KernelMatch(node_id=node.id, node_type="BELIEF", title="t", score=0.5, reason="r")
    frozen = capture_impact_input(
        source_text="aaa",
        extraction=_extraction(),
        matches=[match],
        nodes=[node],
        is_duplicate=False,
        independent_source_count=1,
        secondary_report_count=0,
    )
    other_text = dict(frozen)
    other_text["source_text"] = "bbb"
    assert fingerprint_snapshot(other_text) != frozen["input_fingerprint"]
    other_claim = dict(frozen)
    other_claim["extraction"] = {
        **frozen["extraction"],
        "claims": [{**frozen["extraction"]["claims"][0], "text": "different claim"}],
    }
    assert fingerprint_snapshot(other_claim) != frozen["input_fingerprint"]


def test_incomplete_stored_snapshot_is_not_exact():
    node = _node(proposition="p")
    assert "proposition" in freeze_kernel_target(node)
    assert not stored_is_exact(None)
    assert not stored_is_exact({"source_text": "x"})
    assert not stored_is_exact(
        {
            "source_text": "x",
            "extraction": {},
            "matches": [{"node_id": "abc"}],
            "kernel_targets": [{"id": "abc", "type": "BELIEF", "title": "t"}],
            "independence": {
                "is_duplicate": False,
                "independent_source_count": 1,
                "secondary_report_count": 0,
            },
        }
    )
