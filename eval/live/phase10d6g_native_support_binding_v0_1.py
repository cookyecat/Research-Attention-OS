from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.cognitive.schemas import StrictModel
from app.services.cognitive_impact import is_update_eligible_node, node_proposition
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM, _canonical_payload

VERSION = "phase10d6g-native-support-binding-v0.1"
CONTRACT_VERSION = "native-relation-plus-support-binding-v0.1"

SYSTEM_PROMPT = NATIVE_IMPACT_SYSTEM + """
For each effect that you would emit under the native relation semantics, also bind provenance:
- support_unit_ids must list exact unit_id values from the supplied audited canonical semantic units that support that effect;
- jurisdiction_anchor_ids must list only supplied Kernel locations; OPEN_NEW requires at least one anchor.
These provenance fields are additional bookkeeping. Do not add, suppress, rank, or redirect an otherwise valid cognitive relation merely to simplify provenance binding.
The compatibility numeric fields remain required by the response schema but are diagnostic only in this parity shadow.
"""


class NativeSupportBoundEffect(StrictModel):
    target_kernel_node_id: UUID | None = None
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    change_magnitude: float = Field(ge=0.0, le=1.0)
    epistemic_strength: float = Field(ge=0.0, le=1.0)
    target_importance: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    exploration_candidate: bool = False
    support_unit_ids: list[str] = Field(min_length=1)
    jurisdiction_anchor_ids: list[UUID] = Field(default_factory=list)


class NativeSupportBoundResponse(StrictModel):
    effects: list[NativeSupportBoundEffect] = Field(default_factory=list)
    attention_cost: float = 0.0
    exploration_candidate: bool = False
    evidence_maturity: float = 0.0
    threatens_active_work: bool = False
    marketing_heavy: bool = False
    high_quality_technical: bool = False
    foundational_paper: bool = False


def user_prompt(units: list[dict], matches, nodes) -> str:
    by_id = {node.id: node for node in nodes}
    locations = []
    eligible = []
    for item in matches:
        node = by_id[item.node_id]
        row = {
            "id": str(node.id),
            "type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "score": item.score,
            "relevance_type": item.relevance_type,
        }
        locations.append(row)
        if is_update_eligible_node(node.node_type):
            eligible.append(row)
    shape = {
        "effects": [{
            "target_kernel_node_id": None,
            "operation": "REINFORCE",
            "change_magnitude": 0.0,
            "epistemic_strength": 0.0,
            "target_importance": 0.0,
            "reason": "",
            "exploration_candidate": False,
            "support_unit_ids": ["exact-unit-id"],
            "jurisdiction_anchor_ids": [],
        }],
        "attention_cost": 0.0,
        "exploration_candidate": False,
        "evidence_maturity": 0.0,
        "threatens_active_work": False,
        "marketing_heavy": False,
        "high_quality_technical": False,
        "foundational_paper": False,
    }
    return (
        "Audited canonical semantic units:\n" + json.dumps(_canonical_payload(units), ensure_ascii=False)
        + "\n\nKernel locations:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nEligible cognitive targets:\n" + json.dumps(eligible, ensure_ascii=False)
        + "\n\nReturn JSON exactly in this shape:\n" + json.dumps(shape, ensure_ascii=False)
        + "\nReturn every distinct material effect. Empty effects is legal when nothing changes cognition."
    )


def validate_effect(effect: NativeSupportBoundEffect, *, units: list[dict], matches, nodes) -> tuple[bool, str | None]:
    known_units = {str(unit.get("unit_id") or "") for unit in units}
    match_ids = {match.node_id for match in matches}
    by_id = {node.id: node for node in nodes}
    if not effect.support_unit_ids or any(uid not in known_units for uid in effect.support_unit_ids):
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


def relation_family(effect: NativeSupportBoundEffect, *, nodes) -> tuple[str, str]:
    if effect.operation == "OPEN_NEW":
        return ("OPEN_NEW", "OPEN_NEW")
    by_id = {node.id: str((node.payload or {}).get("phase6b_fixture_code") or node.title) for node in nodes}
    return (effect.operation, by_id.get(effect.target_kernel_node_id, str(effect.target_kernel_node_id)))


def relation_identity(effect: NativeSupportBoundEffect, *, nodes) -> tuple:
    if effect.operation == "OPEN_NEW":
        return ("OPEN_NEW", tuple(sorted(effect.support_unit_ids)))
    return relation_family(effect, nodes=nodes)


def normalize_effects(effects: list[NativeSupportBoundEffect], *, nodes) -> list[NativeSupportBoundEffect]:
    seen = set()
    out = []
    for effect in effects:
        key = relation_identity(effect, nodes=nodes)
        if key in seen:
            continue
        seen.add(key)
        out.append(effect)
    return out
