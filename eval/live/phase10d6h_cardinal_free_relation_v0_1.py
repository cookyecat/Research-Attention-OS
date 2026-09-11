from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.cognitive.schemas import StrictModel
from app.services.cognitive_impact import is_update_eligible_node, node_proposition
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM, _canonical_payload

VERSION = "phase10d6h-cardinal-free-relation-v0.1"
CONTRACT_VERSION = "native-relation-plus-support-cardinal-free-v0.1"

SYSTEM_PROMPT = NATIVE_IMPACT_SYSTEM + """
For each effect that you would emit under the native relation semantics, also bind provenance:
- support_unit_ids must list exact unit_id values from the supplied audited canonical semantic units that support that effect;
- jurisdiction_anchor_ids must list only supplied Kernel locations; OPEN_NEW requires at least one anchor.
These provenance fields are additional bookkeeping. Do not add, suppress, rank, or redirect an otherwise valid cognitive relation merely to simplify provenance binding.
"""


class CardinalFreeEffect(StrictModel):
    target_kernel_node_id: UUID | None = None
    operation: Literal["REINFORCE", "CHALLENGE", "OPEN_NEW"]
    reason: str = Field(min_length=1)
    exploration_candidate: bool = False
    support_unit_ids: list[str] = Field(min_length=1)
    jurisdiction_anchor_ids: list[UUID] = Field(default_factory=list)


class CardinalFreeResponse(StrictModel):
    effects: list[CardinalFreeEffect] = Field(default_factory=list)
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
