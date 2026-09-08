"""Phase 6A raw-source → audited-event projection helpers.

This module does not redefine Sensor, Auditor, D/S/P, or Attention Policy semantics.
It only composes their existing interfaces and keeps causal diagnostics explicit.
"""
from __future__ import annotations

from typing import Any

from eval.live.semantic_evidence_auditor_v0_1_1 import audit_semantic_evidence_v0_1_1

VERTICAL_SLICE_VERSION = "raw-source-attention-vertical-slice-v0.1"


def _event_support(item: dict[str, Any]) -> dict[str, str]:
    return {
        "source_id": str(item["source_id"]),
        "support_pointer": str(item["support_pointer"]),
        "support_excerpt": str(item["support_excerpt"]),
    }


def _supports_from_ids(ids: list[str], evidence_by_id: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    out = []
    for support_id in ids:
        if support_id not in evidence_by_id:
            raise ValueError(f"missing event evidence id: {support_id}")
        out.append(_event_support(evidence_by_id[support_id]))
    return out
def project_event_audit_edges(source_id: str, frame: dict[str, Any]) -> list[dict[str, Any]]:
    """Project one Event Frame into local semantic-object <- evidence audit edges."""
    event_id = str((frame.get("event") or {}).get("event_id") or "unknown-event")
    evidence_by_id = {
        str(item["evidence_id"]): item
        for item in frame.get("evidence") or []
        if item.get("evidence_id")
    }
    groups = [
        ("actor_object", frame.get("substantive_actors_objects") or [], _render_actor),
        ("action_change", frame.get("actions_changes") or [], _render_action),
        ("affected_system_population", frame.get("affected_systems_populations") or [], _render_system),
        ("uncertainty", frame.get("uncertainties") or [], _render_uncertainty),
    ]
    edges = []
    for group, objects, render in groups:
        for index, obj in enumerate(objects):
            support_ids = [str(x) for x in obj.get("support_ids") or []]
            edges.append({
                "audit_id": f"{source_id}:{event_id}:{group}:{index + 1}",
                "source_id": source_id,
                "event_id": event_id,
                "group": group,
                "index": index,
                "semantic_object": render(obj),
                "support_ids": support_ids,
                "evidence": _supports_from_ids(support_ids, evidence_by_id),
            })
    return edges


def _render_actor(obj: dict[str, Any]) -> str:
    return f"name={obj.get('name','')}; role={obj.get('role','')}; substantive_basis={obj.get('substantive_basis','')}"


def _render_action(obj: dict[str, Any]) -> str:
    return f"description={obj.get('description','')}; temporal_status={obj.get('temporal_status','UNKNOWN')}"


def _render_system(obj: dict[str, Any]) -> str:
    return f"description={obj.get('description','')}; reference_scope={obj.get('reference_scope','')}"


def _render_uncertainty(obj: dict[str, Any]) -> str:
    return f"field={obj.get('field','')}; kind={obj.get('kind','')}; note={obj.get('note','')}"


def audit_event_edges(edges: list[dict[str, Any]], *, chat_fn=None) -> list[dict[str, Any]]:
    rows = []
    for edge in edges:
        if not edge["evidence"]:
            rows.append({
                **edge,
                "scorable": False,
                "failure_kind": "no_cited_evidence",
                "audit_result": None,
                "model_meta": None,
            })
            continue
        result = audit_semantic_evidence_v0_1_1(
            audit_id=edge["audit_id"],
            object_type=edge["group"],
            semantic_object=edge["semantic_object"],
            evidence=edge["evidence"],
            chat_fn=chat_fn,
        )
        rows.append({
            **edge,
            "scorable": bool(result.get("scorable")),
            "failure_kind": result.get("failure_kind"),
            "error": result.get("error"),
            "repair_used": bool(result.get("repair_used")),
            "audit_result": result.get("result") if result.get("scorable") else None,
            "model_meta": result.get("model_meta"),
        })
    return rows


def build_audited_event_projection(
    frame: dict[str, Any],
    audit_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Admit only SUFFICIENT event subobjects; never use unaudited event.summary downstream."""
    sufficient = {
        (row["group"], row["index"])
        for row in audit_rows
        if row.get("scorable") and (row.get("audit_result") or {}).get("verdict") == "SUFFICIENT"
    }
    admitted = {
        "actor_objects": [],
        "actions_changes": [],
        "affected_systems_populations": [],
        "uncertainties": [],
    }
    mappings = [
        ("actor_object", "substantive_actors_objects", "actor_objects"),
        ("action_change", "actions_changes", "actions_changes"),
        ("affected_system_population", "affected_systems_populations", "affected_systems_populations"),
        ("uncertainty", "uncertainties", "uncertainties"),
    ]
    for group, source_key, target_key in mappings:
        for index, obj in enumerate(frame.get(source_key) or []):
            if (group, index) in sufficient:
                admitted[target_key].append(obj)

    rejected = [
        {
            "group": row["group"],
            "index": row["index"],
            "semantic_object": row["semantic_object"],
            "verdict": (row.get("audit_result") or {}).get("verdict"),
            "reason_code": (row.get("audit_result") or {}).get("reason_code"),
            "failure_kind": row.get("failure_kind"),
        }
        for row in audit_rows
        if (row["group"], row["index"]) not in sufficient
    ]
    routable = bool(admitted["actions_changes"])
    projection = {
        "event_id": str((frame.get("event") or {}).get("event_id") or "unknown-event"),
        "sensor_event_summary_diagnostic_only": str((frame.get("event") or {}).get("summary") or ""),
        "routing_status": "ROUTABLE" if routable else "AUDIT_BLOCKED_NO_SUPPORTED_ACTION",
        **admitted,
        "rejected_or_unscorable_objects": rejected,
    }
    projection["rendered_event_text"] = render_audited_event_projection(projection) if routable else ""
    return projection


def render_audited_event_projection(projection: dict[str, Any]) -> str:
    lines = ["Audited event representation:"]
    if projection.get("actions_changes"):
        lines.append("Actions / changes:")
        for obj in projection["actions_changes"]:
            lines.append(f"- [{obj.get('temporal_status','UNKNOWN')}] {obj.get('description','')}")
    if projection.get("actor_objects"):
        lines.append("Substantive actors / objects:")
        for obj in projection["actor_objects"]:
            lines.append(f"- {obj.get('name','')}: {obj.get('role','')} — {obj.get('substantive_basis','')}")
    if projection.get("affected_systems_populations"):
        lines.append("Affected systems / populations:")
        for obj in projection["affected_systems_populations"]:
            lines.append(f"- {obj.get('description','')} (scope: {obj.get('reference_scope','unknown')})")
    if projection.get("uncertainties"):
        lines.append("Audited uncertainties:")
        for obj in projection["uncertainties"]:
            lines.append(f"- {obj.get('field','')}: {obj.get('kind','')} — {obj.get('note','')}")
    return "\n".join(lines)
