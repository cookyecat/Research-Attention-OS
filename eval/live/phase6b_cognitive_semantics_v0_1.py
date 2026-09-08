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


def audited_units_to_extraction(units: list[dict[str, Any]]):
    """Narrow adapter from audited Sensor semantics to production Impact input.

    The adapter does not re-extract or upgrade source claims into world facts.
    """
    from app.enums import (
        AttributionType, AuthorType, ClaimType, ObservationType, ObserverType,
    )
    from app.services.extraction import (
        ExtractedClaim, ExtractedInference, ExtractedObservation, ExtractionResult,
    )

    result = ExtractionResult()
    for unit in units:
        statement = str(unit["statement"])
        status = str(unit.get("epistemic_status") or "SOURCE_CLAIM")
        confidence = {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.5}.get(
            str(unit.get("confidence") or "").upper(), 0.6
        )
        excerpts = [str(s["support_excerpt"]) for s in unit.get("supports") or []]
        span = "\n".join(excerpts) or statement
        if status == "DIRECT_OBSERVATION":
            result.observations.append(ExtractedObservation(
                text=statement,
                observer_type=ObserverType.SYSTEM_EXTRACTED,
                observation_type=ObservationType.OTHER,
                confidence=confidence,
                source_span_text=span,
            ))
        elif status == "EXTRACTOR_INFERENCE":
            result.inferences.append(ExtractedInference(
                text=statement,
                author_type=AuthorType.AI,
                confidence=confidence,
                source_roles=["audited_sensor_unit"],
                source_span_text=span,
            ))
        else:
            result.claims.append(ExtractedClaim(
                text=statement,
                claim_type=ClaimType.FACTUAL,
                attributed_to="source",
                attribution_type=AttributionType.UNKNOWN,
                confidence_extraction=confidence,
                temporal_status="CURRENT",
                source_span_text=span,
            ))
    result.event_summary = "\n".join(str(u["statement"]) for u in units)[:2000] or None
    result.evidence_maturity = 0.45 if result.observations else (0.35 if result.claims else 0.3)
    return result


def render_audited_cognitive_context(units: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for unit in units:
        lines.append(f"Semantic unit: {unit['statement']}")
        for support in unit.get("supports") or []:
            lines.append(
                f"Evidence context [{support['support_pointer']}]: {support['support_excerpt']}"
            )
    return "\n".join(lines)


def build_phase6b_mvp_kernel_nodes():
    """In-memory deterministic copy of the existing MVP Kernel; never touches user DB."""
    from uuid import NAMESPACE_URL, uuid5
    from app.models.kernel import KernelNode

    specs = [
        ("G1", "GOAL", "Build better embodied and multi-agent intelligence systems.", "ACTIVE", "description"),
        ("P1", "PROJECT", "Motor Intelligence", "ACTIVE", "description"),
        ("BT1", "BOTTLENECK", "Lack of latency × energy × task-success evaluation for high-frequency embodied control.", "ACTIVE", "description"),
        ("Q1", "QUESTION", "Should high-frequency motor control depend on a large unified model?", "OPEN", "text"),
        ("B1", "BELIEF", "Large unified models may be unsuitable for the fastest embodied-control loop.", "ACTIVE", "proposition"),
        ("M1", "MODEL", "Embodied intelligence contains partially separable cognitive intelligence and temporal motor intelligence.", "ACTIVE", "description"),
        ("P2", "PROJECT", "Collective Intelligence", "ACTIVE", "description"),
        ("Q2", "QUESTION", "Can shared world models reduce explicit multi-agent communication?", "OPEN", "text"),
        ("B2", "BELIEF", "True swarm-style collective intelligence requires meaningful decentralized local intelligence.", "ACTIVE", "proposition"),
        ("D1", "DECISION", "Evaluate startup equity terms independently from employment obligations.", "PENDING", "rationale"),
    ]
    nodes = []
    for code, node_type, title, status, payload_key in specs:
        payload = {payload_key: title, "phase6b_fixture_code": code}
        if code in {"Q1", "B1", "M1", "BT1"}:
            payload["scope"] = "high-frequency embodied control"
        if code in {"Q2", "B2"}:
            payload["scope"] = "large-scale multi-agent embodied systems"
        nodes.append(KernelNode(
            id=uuid5(NAMESPACE_URL, f"raos.phase6b.mvp.{code}"),
            node_type=node_type,
            title=title,
            status=status,
            payload=payload,
            current_version=1,
        ))
    return nodes
