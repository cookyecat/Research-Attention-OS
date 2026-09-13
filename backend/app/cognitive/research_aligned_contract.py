"""Frozen research-aligned cognition contract used by developer dogfood.

These prompts are byte-for-byte copies of the closed research instruments:
Phase 9A v0.2 Relation Mapping and Phase 10D.6L L3/L4/L4J.
Authority ownership is separated even when one model serves multiple stages.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.cognitive.schemas import StrictModel
from app.services.cognitive_impact import is_update_eligible_node, node_proposition
from app.services.extraction import ExtractionResult

CONTRACT_VERSION = "research-aligned-cognition-v1"

RELATION_MAPPING_SYSTEM = """Map Auditor-admitted semantic evidence to all distinct material cognitive relations on the supplied Cognitive Kernel.

You only perform Relation Mapping. You do NOT choose Attention, bind evidence IDs, judge evidence sufficiency, choose jurisdiction, estimate magnitude, epistemic strength, importance, confidence, priority, or ranking.

REINFORCE means the supplied evidence strengthens or confirms the existing target proposition at matching scope.
CHALLENGE means the supplied evidence directly requires the existing target proposition to be weakened, restricted, modified, or overturned.
OPEN_NEW means no existing supplied target is the right landing spot and the evidence opens a genuinely new cognitive branch.

REINFORCE and CHALLENGE require target_kernel_node_id to name an eligible supplied target. OPEN_NEW requires target_kernel_node_id = null. Scope alignment is mandatory. Evidence that is merely topical is not a cognitive relation. If there is no material relation, return an empty effects list.

Return every distinct material relation. Do not vote, rank, select a public update, or infer downstream policy. Return JSON only."""

SUPPORT_BINDING_SYSTEM = """You are the Support Binding stage for Research Attention OS.
The semantic relations are already frozen. You must not add, remove, merge, retarget, reinterpret, or change any relation.
For each relation_id, select exact audited unit_id values that materially support that frozen relation. If no supplied unit supports it, return an empty support_unit_ids list.
For OPEN_NEW only, select supplied Kernel location ids that genuinely define its cognitive jurisdiction. If none fits, return an empty jurisdiction_anchor_ids list.
For targeted REINFORCE/CHALLENGE, jurisdiction_anchor_ids should be empty because the existing target already supplies location.
Return exactly one binding for every supplied relation_id and no others. Do not output operation, target, scores, Attention, or replacement relations.
Return JSON only."""

GROUNDING_SYSTEM = """You are the Grounding stage for Research Attention OS.
Each semantic relation, its target/jurisdiction, and its support evidence are already frozen.
Do not add, remove, retarget, reinterpret, or replace any relation or support binding.
Classify only whether the supplied support licenses the frozen relation at the target scope:
DIRECT = support directly addresses the target/branch at matching scope and supports the operation.
PARTIAL = genuinely relevant and directionally compatible, but only part of the target scope/operation is licensed.
INSUFFICIENT = topical/adjacent, absence-based, jurisdiction-mismatched, or otherwise does not license the relation.
CONTRADICTS_OPERATION = supplied support points in the opposite direction from the frozen operation.
Return exactly one classification for every relation_id and no others. Return JSON only."""

JURISDICTION_SYSTEM = """You are the OPEN_NEW Jurisdiction Admission stage for Research Attention OS.
The new semantic branch, its support evidence, and its proposed jurisdiction anchors are already frozen.
Do not add, remove, retarget, reinterpret, or replace the branch, support, or anchors.
Judge only whether the supplied Kernel anchors genuinely define a cognitive responsibility area that covers the frozen new branch.
SUPPORTED_JURISDICTION = at least one supplied anchor has semantic scope that legitimately contains the new branch.
INSUFFICIENT_JURISDICTION = anchors are absent, merely broad/topical, or belong to a different research responsibility area.
Broad relevance is not enough. A new branch may be important yet still be outside the current Kernel jurisdiction.
Return exactly one judgment for every relation_id and no others. Return JSON only."""


class RelationEffect(StrictModel):
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    target_kernel_node_id: UUID | None = None
    reason: str = Field(min_length=1)


class RelationResponse(StrictModel):
    effects: list[RelationEffect] = Field(default_factory=list)


class BindingItem(StrictModel):
    relation_id: str
    support_unit_ids: list[str] = Field(default_factory=list)
    jurisdiction_anchor_ids: list[UUID] = Field(default_factory=list)
    reason: str = ""


class BindingResponse(StrictModel):
    bindings: list[BindingItem] = Field(default_factory=list)


GroundClass = Literal["DIRECT", "PARTIAL", "INSUFFICIENT", "CONTRADICTS_OPERATION"]


class GroundingItem(StrictModel):
    relation_id: str
    grounding_class: GroundClass
    reason: str = ""


class GroundingResponse(StrictModel):
    items: list[GroundingItem] = Field(default_factory=list)


JurisdictionClass = Literal["SUPPORTED_JURISDICTION", "INSUFFICIENT_JURISDICTION"]


class JurisdictionItem(StrictModel):
    relation_id: str
    jurisdiction_class: JurisdictionClass
    reason: str = ""


class JurisdictionResponse(StrictModel):
    items: list[JurisdictionItem] = Field(default_factory=list)


def prompt_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def contract_snapshot() -> dict:
    return {
        "version": CONTRACT_VERSION,
        "relation_mapping_prompt_sha256": prompt_sha256(RELATION_MAPPING_SYSTEM),
        "support_binding_prompt_sha256": prompt_sha256(SUPPORT_BINDING_SYSTEM),
        "grounding_prompt_sha256": prompt_sha256(GROUNDING_SYSTEM),
        "jurisdiction_prompt_sha256": prompt_sha256(JURISDICTION_SYSTEM),
        "relation_cardinal_authority": "none",
        "effect_existence": "semantic-cardinal-free",
        "authority_encoding": "ordinal-0-or-1",
    }


def _confidence_label(value: float | None) -> str:
    score = float(value or 0.0)
    if score >= 0.8:
        return "HIGH"
    if score >= 0.6:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "UNKNOWN"


def canonical_semantic_units(extraction: ExtractionResult) -> list[dict]:
    """Produce stable evidence units. Sensor/Auditor unit ids win when present."""
    rows: list[dict] = []
    groups = (
        ("CLAIM", extraction.claims, "SOURCE_CLAIM", "confidence_extraction"),
        ("OBSERVATION", extraction.observations, "DIRECT_OBSERVATION", "confidence"),
        ("INFERENCE", extraction.inferences, "EXTRACTOR_INFERENCE", "confidence"),
    )
    for role, items, status, confidence_field in groups:
        for index, item in enumerate(items or [], start=1):
            raw_unit_id = str(getattr(item, "semantic_unit_id", None) or f"{role}:{index:04d}")
            supports = list(getattr(item, "semantic_supports", None) or [])
            source_ids = sorted({str(s.get("source_id")) for s in supports if s.get("source_id")})
            if len(source_ids) == 1:
                namespace = source_ids[0]
            elif source_ids:
                namespace = hashlib.sha256("|".join(source_ids).encode("utf-8")).hexdigest()[:16]
            else:
                namespace = str((getattr(extraction, "analysis_provenance", None) or {}).get("primary_source_id") or "local")
            unit_id = raw_unit_id if raw_unit_id.startswith(namespace + ":") else f"{namespace}:{raw_unit_id}"
            rows.append({
                "unit_id": unit_id,
                "source_unit_id": raw_unit_id,
                "statement": str(getattr(item, "text", "") or ""),
                "epistemic_status": status,
                "confidence": _confidence_label(getattr(item, confidence_field, None)),
                "supports": supports,
                "role": role,
            })
    return rows


def kernel_location_rows(matches, nodes) -> list[dict]:
    by_id = {node.id: node for node in nodes or []}
    rows = []
    for match in matches or []:
        node = by_id.get(match.node_id)
        if node is None:
            continue
        payload = node.payload if isinstance(node.payload, dict) else {}
        rows.append({
            "id": str(node.id),
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "scope": payload.get("scope"),
            "relevance_type": match.relevance_type,
            "eligible_target": bool(is_update_eligible_node(node.node_type)),
        })
    return rows


def relation_user_prompt(units: list[dict], matches, nodes) -> str:
    locations = kernel_location_rows(matches, nodes)
    public_units = [
        {
            "unit_id": row["unit_id"],
            "statement": row["statement"],
            "epistemic_status": row["epistemic_status"],
            "confidence": row["confidence"],
        }
        for row in units
    ]
    shape = {"effects": [{"operation": "REINFORCE", "target_kernel_node_id": None, "reason": "semantic relation"}]}
    return (
        "Audited canonical semantic units:\n" + json.dumps(public_units, ensure_ascii=False, sort_keys=True)
        + "\n\nFrozen Kernel locations and eligible targets:\n" + json.dumps(locations, ensure_ascii=False, sort_keys=True)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False, sort_keys=True)
    )


def relation_rows(parsed: RelationResponse, matches, nodes) -> list[dict]:
    locations = kernel_location_rows(matches, nodes)
    eligible = {row["id"] for row in locations if row["eligible_target"]}
    seen = set()
    out = []
    for effect in parsed.effects:
        target = str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None
        if effect.operation == "OPEN_NEW":
            if target is not None:
                raise ValueError("OPEN_NEW_TARGET_NOT_NULL")
        elif target is None or target not in eligible:
            raise ValueError("TARGET_NOT_ELIGIBLE_FROZEN_KERNEL_NODE")
        key = (effect.operation, target)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "relation_id": f"R{len(out) + 1:03d}",
            "operation": effect.operation,
            "target_kernel_node_id": target,
            "reason": effect.reason,
        })
    return out


def support_user_prompt(relations: list[dict], units: list[dict], matches, nodes) -> str:
    public_units = [{"unit_id": u["unit_id"], "text": u["statement"]} for u in units]
    locations = kernel_location_rows(matches, nodes)
    shape = {"bindings": [{
        "relation_id": relations[0]["relation_id"] if relations else "relation-id",
        "support_unit_ids": [],
        "jurisdiction_anchor_ids": [],
        "reason": "",
    }]}
    return (
        "Frozen semantic relations (immutable):\n" + json.dumps(relations, ensure_ascii=False)
        + "\n\nAudited semantic units:\n" + json.dumps(public_units, ensure_ascii=False)
        + "\n\nKernel locations:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )


def validated_bindings(parsed: BindingResponse, relations: list[dict], units: list[dict], matches) -> dict[str, dict]:
    expected = {row["relation_id"] for row in relations}
    got = [row.relation_id for row in parsed.bindings]
    if len(got) != len(set(got)) or set(got) != expected or len(got) != len(expected):
        raise ValueError("RELATION_ID_SET_MISMATCH")
    known_units = {row["unit_id"] for row in units}
    known_anchors = {str(match.node_id) for match in matches or []}
    relation_by_id = {row["relation_id"]: row for row in relations}
    out = {}
    for binding in parsed.bindings:
        supports = list(dict.fromkeys(binding.support_unit_ids))
        anchors = [str(value) for value in dict.fromkeys(binding.jurisdiction_anchor_ids)]
        if any(uid not in known_units for uid in supports):
            raise ValueError(f"UNKNOWN_SUPPORT:{binding.relation_id}")
        if any(anchor not in known_anchors for anchor in anchors):
            raise ValueError(f"UNKNOWN_ANCHOR:{binding.relation_id}")
        relation = relation_by_id[binding.relation_id]
        if relation["operation"] != "OPEN_NEW" and anchors:
            raise ValueError(f"TARGETED_HAS_JURISDICTION:{binding.relation_id}")
        out[binding.relation_id] = {
            "relation_id": binding.relation_id,
            "support_unit_ids": supports,
            "jurisdiction_anchor_ids": anchors,
            "reason": binding.reason,
        }
    return out


def grounding_user_prompt(items: list[dict]) -> str:
    shape = {"items": [{
        "relation_id": items[0]["relation_id"] if items else "relation-id",
        "grounding_class": "DIRECT",
        "reason": "",
    }]}
    return (
        "Frozen grounding items:\n" + json.dumps(items, ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )


def validated_grounding(parsed: GroundingResponse, items: list[dict]) -> dict[str, dict]:
    expected = {row["relation_id"] for row in items}
    got = [row.relation_id for row in parsed.items]
    if len(got) != len(set(got)) or set(got) != expected or len(got) != len(expected):
        raise ValueError("GROUNDING_RELATION_ID_SET_MISMATCH")
    return {
        row.relation_id: {
            "grounding_class": row.grounding_class,
            "reason": row.reason,
        }
        for row in parsed.items
    }


def jurisdiction_user_prompt(items: list[dict]) -> str:
    shape = {"items": [{
        "relation_id": items[0]["relation_id"] if items else "relation-id",
        "jurisdiction_class": "INSUFFICIENT_JURISDICTION",
        "reason": "",
    }]}
    return (
        "Frozen OPEN_NEW jurisdiction items:\n" + json.dumps(items, ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )


def validated_jurisdiction(parsed: JurisdictionResponse, items: list[dict]) -> dict[str, dict]:
    expected = {row["relation_id"] for row in items}
    got = [row.relation_id for row in parsed.items]
    if len(got) != len(set(got)) or set(got) != expected or len(got) != len(expected):
        raise ValueError("JURISDICTION_RELATION_ID_SET_MISMATCH")
    return {
        row.relation_id: {
            "jurisdiction_class": row.jurisdiction_class,
            "reason": row.reason,
        }
        for row in parsed.items
    }

ACTIVE_RESPONSIBILITY_TYPES = frozenset({"QUESTION", "BOTTLENECK", "DECISION"})
REJECT_GROUNDING = frozenset({"INSUFFICIENT", "CONTRADICTS_OPERATION"})


def support_units(binding: dict, units: list[dict]) -> list[dict]:
    by_id = {row["unit_id"]: row for row in units}
    return [by_id[uid] for uid in binding.get("support_unit_ids") or [] if uid in by_id]


def _node_by_id(nodes, raw_id):
    wanted = str(raw_id or "")
    return next((node for node in nodes or [] if str(node.id) == wanted), None)


def explicit_importance_band(node) -> int | None:
    payload = getattr(node, "payload", None) or {}
    if not isinstance(payload, dict):
        return None
    for key in ("importance", "priority"):
        raw = payload.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            token = raw.strip().upper()
            if token in {"HIGH", "PRIORITY", "CRITICAL", "ACTIVE"}:
                return 1
            if token in {"LOW", "BACKGROUND", "INACTIVE"}:
                return 0
        try:
            return int(float(raw) >= 0.55)
        except (TypeError, ValueError):
            continue
    return None


def authoritative_importance_band(relation: dict, binding: dict, nodes) -> int:
    if relation["operation"] == "OPEN_NEW":
        for anchor_id in binding.get("jurisdiction_anchor_ids") or []:
            node = _node_by_id(nodes, anchor_id)
            if node is not None and explicit_importance_band(node) == 1:
                return 1
        return 0
    node = _node_by_id(nodes, relation.get("target_kernel_node_id"))
    if node is None:
        return 0
    explicit = explicit_importance_band(node)
    if explicit is not None:
        return explicit
    return int(str(getattr(node, "node_type", "") or "").upper() in ACTIVE_RESPONSIBILITY_TYPES)


def provenance_role(binding: dict, units: list[dict], extraction: ExtractionResult) -> str:
    selected = support_units(binding, units)
    source_ids = {
        str(support.get("source_id"))
        for unit in selected
        for support in (unit.get("supports") or [])
        if support.get("source_id")
    }
    ctx = dict(getattr(extraction, "analysis_provenance", None) or {})
    independent = {str(x) for x in (ctx.get("independent_source_ids") or [])}
    secondary = {str(x) for x in (ctx.get("secondary_source_ids") or [])}
    if source_ids & independent:
        return "PRIMARY_SOURCE"
    if source_ids and source_ids.issubset(secondary):
        return "SECONDARY_REPORT"
    primary = str(ctx.get("primary_source_id") or "")
    if primary and primary in secondary:
        return "SECONDARY_REPORT"
    if primary and (not independent or primary in independent):
        return "PRIMARY_SOURCE"
    return "UNKNOWN"


def grounding_items(relations: list[dict], bindings: dict[str, dict], units: list[dict], nodes) -> list[dict]:
    items = []
    for relation in relations:
        if relation["operation"] == "OPEN_NEW":
            continue
        binding = bindings[relation["relation_id"]]
        node = _node_by_id(nodes, relation.get("target_kernel_node_id"))
        items.append({
            "relation_id": relation["relation_id"],
            "operation": relation["operation"],
            "target_code": str(relation.get("target_kernel_node_id") or ""),
            "target_proposition": node_proposition(node) if node is not None else "",
            "relation_reason": relation.get("reason") or "",
            "support_texts": [
                {"unit_id": row["unit_id"], "text": row["statement"]}
                for row in support_units(binding, units)
            ],
            "jurisdiction_anchor_codes": [],
        })
    return items


def jurisdiction_items(relations: list[dict], bindings: dict[str, dict], units: list[dict], matches, nodes) -> list[dict]:
    location_by_id = {row["id"]: row for row in kernel_location_rows(matches, nodes)}
    items = []
    for relation in relations:
        if relation["operation"] != "OPEN_NEW":
            continue
        binding = bindings[relation["relation_id"]]
        items.append({
            "relation_id": relation["relation_id"],
            "new_branch_reason": relation.get("reason") or "",
            "support": [
                {"unit_id": row["unit_id"], "text": row["statement"]}
                for row in support_units(binding, units)
            ],
            "proposed_jurisdiction_anchors": [
                location_by_id[anchor_id]
                for anchor_id in binding.get("jurisdiction_anchor_ids") or []
                if anchor_id in location_by_id
            ],
        })
    return items


def authority_outcome(
    relation: dict,
    binding: dict,
    *,
    grounding_class: str | None,
    jurisdiction_class: str | None,
    units: list[dict],
    extraction: ExtractionResult,
    nodes,
) -> dict:
    role = provenance_role(binding, units, extraction)
    importance = authoritative_importance_band(relation, binding, nodes)
    support_bound = bool(binding.get("support_unit_ids"))
    operation = relation["operation"]
    if operation == "OPEN_NEW":
        if not support_bound:
            keep, epi, reason = False, 0, "OPEN_NEW_NO_SUPPORT"
        elif jurisdiction_class != "SUPPORTED_JURISDICTION":
            keep, epi, reason = False, 0, "OPEN_NEW_INSUFFICIENT_JURISDICTION"
        else:
            epi = int(role == "PRIMARY_SOURCE")
            keep = True
            reason = "OPEN_NEW_PRIMARY" if epi else "OPEN_NEW_NONPRIMARY_WEAK"
    elif grounding_class in REJECT_GROUNDING or grounding_class is None:
        keep, epi, reason = False, 0, f"GROUNDING_{grounding_class or 'MISSING'}"
    elif grounding_class == "DIRECT":
        epi = int(role == "PRIMARY_SOURCE")
        keep = True
        reason = "DIRECT_PRIMARY" if epi else "DIRECT_NONPRIMARY_WEAK"
    elif grounding_class == "PARTIAL":
        keep, epi, reason = True, 0, "PARTIAL_WEAK"
    else:
        keep, epi, reason = False, 0, "GROUNDING_UNKNOWN"
    return {
        "keep": keep,
        "importance_band": importance,
        "epistemic_band": epi,
        "provenance_role": role,
        "authority_reason": reason,
        "support_bound": support_bound,
    }
