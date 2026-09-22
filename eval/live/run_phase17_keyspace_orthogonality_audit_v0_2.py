from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.cognitive.client import chat_json_schema, chat_json

RUN_VERSION = "phase17-keyspace-orthogonality-audit-v0.2"
SOURCE = ROOT / "eval/live/results/phase17_jev_longitudinal_state_replay_v0_6/phase17_jev_longitudinal_state_replay_v0.6_n8_20260922T070508Z.json"
OUT_DIR = ROOT / "eval/live/results/phase17_keyspace_orthogonality_audit_v0_2"


class SlotAudit(BaseModel):
    slot_id: str
    plane: str = Field(description="IDENTITY, WORLD, EVIDENCE, or MIXED")
    one_question: bool
    generic_state_question: str
    primitive_axis: str
    boundary_issue: str | None = None
    decomposition: list[str] = []


class PairAudit(BaseModel):
    slot_a: str
    slot_b: str
    a_can_change_while_b_fixed: bool
    b_can_change_while_a_fixed: bool
    orthogonal: bool
    explanation: str


class ProposedKey(BaseModel):
    key_name: str
    generic_question: str
    why_primitive: str
    derived_from_slot_ids: list[str]


class AuditReport(BaseModel):
    slot_audits: list[SlotAudit]
    pair_audits: list[PairAudit]
    proposed_world_keyspace: list[ProposedKey]
    identity_plane_note: str
    evidence_plane_note: str
    overall_conclusion: str


SYSTEM = """You are auditing a candidate semantic state key-space for RAOS.

A key is not a topic label. It is a coordinate of a materialized current-state space.

Apply these principles rigorously:

1. PLANE SEPARATION
- IDENTITY: what entity/event this is; stable referent definition. This belongs outside mutable WorldState.
- WORLD: mutable facts about the current world/event.
- EVIDENCE: provenance, confidence, validation, source quality, reliability, support. This belongs in EvidenceState / epistemic representation, not ordinary WorldState.
- MIXED: a key combines more than one plane.

2. COUNTERFACTUAL ORTHOGONALITY
For each pair A,B ask both:
- Can A change while B's answer remains fixed?
- Can B change while A's answer remains fixed?
If both are possible in a coherent world, treat the dimensions as semantically orthogonal even if the dataset often updates them together.
If not, explain the logical dependence or overlap.

3. GENERALITY
Rewrite each candidate key as a domain-agnostic question that could apply to many kinds of events/entities. Prefer fundamental questions over domain labels.
Do not invent a global fixed ontology. Discover the smallest abstractions justified by the supplied slots.

4. PRIMITIVENESS
A strong key should answer one basic kind of question, not concatenate identity + lifecycle, behavior + quality, provenance + world fact, etc.
Examples of philosophical upper-level distinctions may include persistence/lifecycle, structure, mechanism/dynamics, capability/behavior, quality/quantity, relation/context/affordance. These are inspirations, not a required list.

5. WORLD VS KNOWLEDGE
'This source does not say X' is not a WorldState change.
'Independent evidence supports X' is primarily epistemic/provenance information unless the Event itself is specifically an evidence/validation event.
Claims about tests/benchmarks having occurred can be World facts; credibility of those claims belongs to EvidenceState.

6. GENERALITY IS NOT BREADTH
- A good key should be domain-independent but primitive-bounded.
- Flag keys whose label/question is tied to one application, workflow, benchmark, product, game, or vertical.
- If a specific application workflow is better represented as a capability instance, affordance/relation, or value inside a more general process coordinate, say so.

7. DO NOT optimize for fewer keys.
Optimize for orthogonal, stable, general, reusable coordinates.

Return a proposed WORLD key-space only from dimensions actually justified by the current slots. Keep Identity and Evidence notes separate.
"""


def main():
    source = json.loads(SOURCE.read_text())
    slots = source["summary"]["final_slot_state"]["slots"]
    event_identity = {
        "title": source["trajectory"][0].get("title"),
        "benchmark_event_id": source.get("benchmark_event_id"),
    }
    payload = {
        "event_identity_context": event_identity,
        "candidate_slots": [
            {
                "slot_id": s["slot_id"],
                "slot_label": s["slot_label"],
                "primitive_family": s.get("primitive_family"),
                "state_question": s["state_question"],
                "value_excerpt": s["value"][:1200],
            }
            for s in slots
        ],
    }
    raw, meta = chat_json(
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": "Audit this candidate key-space. Use clear JSON field names and preserve slot ids.\n\n"
                + json.dumps(payload, ensure_ascii=False, indent=2),
            },
        ],
        timeout=90.0,
        thinking="disabled",
        reasoning_effort=None,
        temperature=0.1,
    )
    out = {
        "run_version": RUN_VERSION,
        "source_artifact": str(SOURCE.relative_to(ROOT)),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report": raw,
        "meta": meta,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print(json.dumps(raw, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
