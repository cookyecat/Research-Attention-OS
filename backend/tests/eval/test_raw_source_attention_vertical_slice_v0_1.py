"""Tests for Phase 6A audited-event projection."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.raw_source_attention_vertical_slice_v0_1 import (
    build_audited_event_projection,
    project_event_audit_edges,
)


def _frame() -> dict:
    return {
        "event": {"event_id": "E1", "summary": "UNAUDITED SUMMARY MUST NOT ROUTE"},
        "evidence": [
            {"evidence_id": "ev1", "source_id": "RSX", "support_pointer": "PARA 0001", "support_excerpt": "Company released model."},
            {"evidence_id": "ev2", "source_id": "RSX", "support_pointer": "PARA 0002", "support_excerpt": "Researchers use it."},
        ],
        "substantive_actors_objects": [{
            "name": "Company", "role": "developer", "substantive_basis": "released model", "support_ids": ["ev1"]
        }],
        "actions_changes": [{
            "description": "released model", "temporal_status": "ANNOUNCED", "support_ids": ["ev1"]
        }],
        "affected_systems_populations": [{
            "description": "AI developer ecosystem", "reference_scope": "field", "support_ids": ["ev2"]
        }],
        "uncertainties": [],
    }


def _row(edge: dict, verdict: str) -> dict:
    return {
        **edge,
        "scorable": True,
        "failure_kind": None,
        "audit_result": {
            "verdict": verdict,
            "reason_code": "SUPPORTED" if verdict == "SUFFICIENT" else "MISSING_SUPPORT",
        },
    }


def test_project_edges_include_temporal_status_and_cited_evidence():
    edges = project_event_audit_edges("RSX", _frame())
    action = next(x for x in edges if x["group"] == "action_change")
    assert "temporal_status=ANNOUNCED" in action["semantic_object"]
    assert action["evidence"][0]["support_pointer"] == "PARA 0001"


def test_projection_uses_only_sufficient_objects_and_never_summary():
    frame = _frame()
    edges = project_event_audit_edges("RSX", frame)
    rows = [_row(e, "SUFFICIENT") for e in edges]
    projection = build_audited_event_projection(frame, rows)
    assert projection["routing_status"] == "ROUTABLE"
    assert "UNAUDITED SUMMARY MUST NOT ROUTE" not in projection["rendered_event_text"]
    assert "released model" in projection["rendered_event_text"]


def test_projection_blocks_when_action_is_not_sufficient():
    frame = _frame()
    edges = project_event_audit_edges("RSX", frame)
    rows = [
        _row(e, "INSUFFICIENT" if e["group"] == "action_change" else "SUFFICIENT")
        for e in edges
    ]
    projection = build_audited_event_projection(frame, rows)
    assert projection["routing_status"] == "AUDIT_BLOCKED_NO_SUPPORTED_ACTION"
    assert projection["rendered_event_text"] == ""
    assert len(projection["rejected_or_unscorable_objects"]) == 1
