"""Phase 6B helpers for audited cognitive semantics.

Bridges Semantic Sensor non-event epistemic units into the existing
Semantic Evidence Auditor without changing either module's semantics.
"""
from __future__ import annotations

from typing import Any

from eval.live.semantic_evidence_auditor_v0_1_1 import audit_semantic_evidence_v0_1_1

COGNITIVE_SLICE_VERSION = "phase6b-cognitive-semantics-v0.1"


def project_epistemic_unit_edge(source_id: str, unit: dict[str, Any]) -> dict[str, Any]:
    supports = [
        {
            "source_id": str(s["source_id"]),
            "support_pointer": str(s["support_pointer"]),
            "support_excerpt": str(s["support_excerpt"]),
        }
        for s in (unit.get("supports") or [])
    ]
    return {
        "audit_id": f"{source_id}:{unit['unit_id']}:epistemic_unit",
        "source_id": source_id,
        "unit_id": str(unit["unit_id"]),
        "statement": str(unit["statement"]),
        "epistemic_status": str(unit.get("epistemic_status") or "SOURCE_CLAIM"),
        "confidence": str(unit.get("confidence") or "UNKNOWN"),
        "supports": supports,
    }


def audit_epistemic_unit_edge(edge: dict[str, Any], *, chat_fn=None) -> dict[str, Any]:
    if not edge["supports"]:
        return {
            **edge,
            "scorable": False,
            "failure_kind": "no_cited_evidence",
            "audit_result": None,
            "model_meta": None,
        }
    result = audit_semantic_evidence_v0_1_1(
        audit_id=edge["audit_id"],
        object_type="epistemic_unit",
        semantic_object=edge["statement"],
        evidence=edge["supports"],
        chat_fn=chat_fn,
    )
    return {
        **edge,
        "scorable": bool(result.get("scorable")),
        "failure_kind": result.get("failure_kind"),
        "error": result.get("error"),
        "repair_used": bool(result.get("repair_used")),
        "audit_result": result.get("result") if result.get("scorable") else None,
        "model_meta": result.get("model_meta"),
    }


def admitted_epistemic_units(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only SUFFICIENT units plus the evidence context that passed with them."""
    return [
        {
            "unit_id": row["unit_id"],
            "statement": row["statement"],
            "epistemic_status": row["epistemic_status"],
            "confidence": row["confidence"],
            "supports": list(row["supports"]),
        }
        for row in rows
        if row.get("scorable") and (row.get("audit_result") or {}).get("verdict") == "SUFFICIENT"
    ]
