from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.cognitive.schemas import StrictModel
from app.services.cognitive_impact import is_update_eligible_node, node_proposition

VERSION = "phase10d6f-effect-support-binding-v0.1"
CONTRACT_VERSION = "canonical-relation-support-binding-v0.2"

SYSTEM_PROMPT = """Map Auditor-admitted canonical semantic units to all distinct legal cognitive relations on the supplied Cognitive Kernel.

You do NOT choose Attention and you do NOT estimate numeric change magnitude, importance, epistemic strength, confidence, or priority. Downstream authoritative state owns those decisions.

For each relation:
- REINFORCE / CHALLENGE require one existing eligible epistemic Kernel target at matching scope.
- OPEN_NEW requires target_kernel_node_id = null and at least one supplied jurisdiction anchor.
- support_unit_ids must name the exact canonical semantic units that directly justify this relation. Never cite a unit merely because it is topically related.
- jurisdiction_anchor_ids must name only supplied frozen Kernel locations. For targeted relations they may be empty; for OPEN_NEW at least one is required.
- preserve multiple distinct legal effects; do not vote, rank, argmax, or choose a single public update.
- scope alignment is mandatory. Evidence that alternative A works does not challenge B unless it directly addresses B.
- if no material semantic cognitive relation exists, return an empty effects list.

Return JSON only."""


class SupportBoundEffect(StrictModel):
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    target_kernel_node_id: UUID | None = None
    support_unit_ids: list[str] = Field(min_length=1)
    jurisdiction_anchor_ids: list[UUID] = Field(default_factory=list)
    reason: str = Field(min_length=1)


class SupportBoundRelationResponse(StrictModel):
    effects: list[SupportBoundEffect] = Field(default_factory=list)


def user_prompt(units: list[dict], matches, nodes) -> str:
    by_id = {node.id: node for node in nodes}
    canonical = [
        {
            "unit_id": str(unit.get("unit_id") or ""),
            "statement": str(unit.get("statement") or ""),
            "epistemic_status": str(unit.get("epistemic_status") or ""),
            "confidence": str(unit.get("confidence") or ""),
            "supports": list(unit.get("supports") or []),
        }
        for unit in units
    ]
    locations = []
    eligible = []
    for match in matches:
        node = by_id[match.node_id]
        payload = node.payload or {}
        row = {
            "id": str(node.id),
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "scope": payload.get("scope") if isinstance(payload, dict) else None,
            "relevance_type": match.relevance_type,
            "score": float(match.score),
        }
        locations.append(row)
        if is_update_eligible_node(node.node_type):
            eligible.append(row)
    shape = {
        "effects": [
            {
                "operation": "REINFORCE",
                "target_kernel_node_id": None,
                "support_unit_ids": ["exact-unit-id"],
                "jurisdiction_anchor_ids": [],
                "reason": "semantic relation grounded in the cited units",
            }
        ]
    }
    return (
        "Canonical semantic units:\n" + json.dumps(canonical, ensure_ascii=False)
        + "\n\nFrozen Kernel locations / legal jurisdiction anchors:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nEligible targeted cognitive nodes:\n" + json.dumps(eligible, ensure_ascii=False)
        + "\n\nReturn JSON in exactly this shape:\n" + json.dumps(shape, ensure_ascii=False)
    )


def validate_effect(effect: SupportBoundEffect, *, units: list[dict], matches, nodes) -> tuple[bool, str | None]:
    known_units = {str(unit.get("unit_id") or "") for unit in units}
    match_ids = {match.node_id for match in matches}
    by_id = {node.id: node for node in nodes}
    if not effect.support_unit_ids or any(unit_id not in known_units for unit_id in effect.support_unit_ids):
        return False, "UNKNOWN_SUPPORT_UNIT"
    if any(anchor not in match_ids for anchor in effect.jurisdiction_anchor_ids):
        return False, "UNKNOWN_JURISDICTION_ANCHOR"
    if effect.operation == "OPEN_NEW":
        if effect.target_kernel_node_id is not None:
            return False, "OPEN_NEW_TARGET_NOT_NULL"
        if not effect.jurisdiction_anchor_ids:
            return False, "OPEN_NEW_WITHOUT_JURISDICTION"
        return True, None
    target = effect.target_kernel_node_id
    if target is None or target not in match_ids:
        return False, "TARGET_NOT_IN_FROZEN_LOCATE"
    node = by_id.get(target)
    if node is None or not is_update_eligible_node(node.node_type):
        return False, "TARGET_NOT_UPDATE_ELIGIBLE"
    return True, None


def effect_key(effect: SupportBoundEffect, *, nodes) -> tuple:
    code = {
        node.id: str((node.payload or {}).get("phase6b_fixture_code") or node.title)
        for node in nodes
    }
    if effect.operation == "OPEN_NEW":
        return ("OPEN_NEW", tuple(sorted(effect.support_unit_ids)))
    return (effect.operation, code.get(effect.target_kernel_node_id, str(effect.target_kernel_node_id)))
