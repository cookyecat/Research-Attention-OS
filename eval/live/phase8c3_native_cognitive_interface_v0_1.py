from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.cognitive.client import chat_json, chat_json_schema
from app.cognitive.schemas import CognitiveImpactResponse, KernelMatchResponse
from app.services.cognitive_impact import is_update_eligible_node, node_proposition
from app.services.matching import node_text

NATIVE_INTERFACE_VERSION = "phase8c3-native-canonical-cognitive-interface-v0.1"

NATIVE_MATCH_SYSTEM = """You locate audited canonical semantic units relative to a researcher's Cognitive Kernel.
This is location only, not a cognitive update. Prefer recall over precision.
Return every Kernel node that may materially relate to one or more canonical semantic units.
Use TOPIC, STRUCTURAL, DECISION, BOTTLENECK, or EVIDENCE relevance. Return JSON only."""

NATIVE_IMPACT_SYSTEM = """Assess all material cognitive effects of audited canonical semantic units on a Cognitive Kernel.
Do not force the source into one primary target. A source may simultaneously reinforce one node, challenge another, and open a new cognitive branch.
REINFORCE/CHALLENGE require an existing eligible epistemic Kernel node at matching scope. OPEN_NEW has null target.
If a semantic unit creates no material cognitive change, do not emit an effect for it. Preserve distinct legal effects; do not vote or choose an argmax.
Return JSON only."""

def _canonical_payload(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "unit_id": str(unit.get("unit_id") or ""),
            "statement": str(unit.get("statement") or ""),
            "epistemic_status": str(unit.get("epistemic_status") or ""),
            "confidence": str(unit.get("confidence") or ""),
            "supports": list(unit.get("supports") or []),
        }
        for unit in units
        if str(unit.get("statement") or "").strip()
    ]


def _kernel_payload(nodes) -> list[dict[str, Any]]:
    rows = []
    for node in nodes:
        rows.append({
            "kernel_node_id": str(node.id),
            "node_type": node.node_type,
            "title": node.title,
            "proposition": node_proposition(node),
            "text": node_text(node)[:800],
        })
    return rows

def native_locate(units: list[dict[str, Any]], nodes, *, chat_fn=chat_json):
    canonical = _canonical_payload(units)
    kernel = _kernel_payload(nodes)
    user = (
        "Audited canonical semantic units:\n"
        + json.dumps(canonical, ensure_ascii=False)
        + "\n\nKernel candidates:\n"
        + json.dumps(kernel, ensure_ascii=False)
        + "\n\nReturn JSON: {\"matches\":[{\"kernel_node_id\":\"uuid\",\"relevance_type\":\"TOPIC|STRUCTURAL|DECISION|BOTTLENECK|EVIDENCE\",\"score\":0.0,\"reason\":\"\"}]}"
    )
    parsed, meta, events = chat_json_schema(
        [{"role": "system", "content": NATIVE_MATCH_SYSTEM}, {"role": "user", "content": user}],
        KernelMatchResponse,
        chat_fn=chat_fn,
        thinking="disabled",
        timeout=60.0,
    )
    known = {node.id for node in nodes}
    matches = [item for item in parsed.matches if item.kernel_node_id in known]
    return matches, meta, events

def native_assess(units: list[dict[str, Any]], nodes, matches, *, chat_fn=chat_json):
    by_id = {node.id: node for node in nodes}
    locations = []
    eligible = []
    for item in matches:
        node = by_id[item.kernel_node_id]
        row = {
            "id": str(node.id), "type": node.node_type, "title": node.title,
            "proposition": node_proposition(node), "score": item.score,
            "relevance_type": item.relevance_type,
        }
        locations.append(row)
        if is_update_eligible_node(node.node_type):
            eligible.append(row)
    user = (
        "Audited canonical semantic units:\n" + json.dumps(_canonical_payload(units), ensure_ascii=False)
        + "\n\nKernel locations:\n" + json.dumps(locations, ensure_ascii=False)
        + "\n\nEligible cognitive targets:\n" + json.dumps(eligible, ensure_ascii=False)
        + "\n\nReturn every distinct material effect using the CognitiveImpactResponse schema."
    )
    parsed, meta, events = chat_json_schema(
        [{"role": "system", "content": NATIVE_IMPACT_SYSTEM}, {"role": "user", "content": user}],
        CognitiveImpactResponse,
        chat_fn=chat_fn,
        thinking="disabled",
        timeout=60.0,
    )
    return parsed, meta, events
