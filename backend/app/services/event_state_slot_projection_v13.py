from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.cognitive.client import chat_json_schema
from app.services.event_observation import EventObservationV01
from app.services.semantic_primitives import PrimitiveFamily
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    DraftTarget,
    EventPhase,
    SemanticSlotStateV01,
    SlotDeltaV01,
    SlotMutationMode,
    SlotMutationV01,
    _new_slot_id,
)


PROPOSITION_NORMALIZER_CONTRACT = "event-proposition-normalizer-v0.1"
KEY_PROJECTOR_CONTRACT = "event-state-key-projector-v0.1"

Plane = Literal["WORLD", "IDENTITY", "EVIDENCE", "PERIPHERAL_OR_REDUNDANT"]
SupportMode = Literal["MERGE", "REPLACE"]


class AtomicPropositionDraftV01(BaseModel):
    support_key: str = Field(min_length=1)
    proposition: str = Field(min_length=1, max_length=2000)
    plane: Plane
    primitive_family: PrimitiveFamily | None = None
    rationale: str | None = Field(default=None, max_length=1200)

    @model_validator(mode="after")
    def validate_plane(self):
        object.__setattr__(self, "proposition", " ".join(self.proposition.split()))
        if self.plane == "WORLD":
            if self.primitive_family is None:
                raise ValueError("WORLD proposition requires primitive_family")
        elif self.primitive_family is not None:
            raise ValueError(f"{self.plane} proposition may not set primitive_family")
        return self


class PropositionBasisDraftV01(BaseModel):
    contract: str = PROPOSITION_NORMALIZER_CONTRACT
    propositions: tuple[AtomicPropositionDraftV01, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != PROPOSITION_NORMALIZER_CONTRACT:
            raise ValueError(f"contract must be {PROPOSITION_NORMALIZER_CONTRACT}")
        return self


class AtomicPropositionV01(BaseModel):
    proposition_id: str
    support_key: str
    proposition: str
    plane: Plane
    primitive_family: PrimitiveFamily | None = None


class KeyProjectionMutationDraftV01(BaseModel):
    target: DraftTarget
    existing_slot_key: str | None = None
    primitive_family: PrimitiveFamily | None = None
    slot_label: str | None = Field(default=None, max_length=200)
    state_question: str | None = Field(default=None, max_length=1000)
    value: str = Field(min_length=1, max_length=6000)
    proposition_ids: tuple[str, ...] = Field(min_length=1)
    support_mode: SupportMode = "MERGE"
    contest: bool = False
    rationale: str | None = Field(default=None, max_length=1600)

    @model_validator(mode="after")
    def validate_target(self):
        ids = tuple(dict.fromkeys(self.proposition_ids))
        object.__setattr__(self, "proposition_ids", ids)
        if self.target == "EXISTING":
            if not self.existing_slot_key:
                raise ValueError("EXISTING requires existing_slot_key")
            if any(v is not None for v in (
                self.primitive_family, self.slot_label, self.state_question
            )):
                raise ValueError(
                    "EXISTING derives primitive/label/question from the stable slot key"
                )
        else:
            if self.existing_slot_key is not None:
                raise ValueError("CREATE may not set existing_slot_key")
            if self.primitive_family is None or not self.slot_label or not self.state_question:
                raise ValueError(
                    "CREATE requires primitive_family, slot_label, and state_question"
                )
            if self.support_mode != "MERGE":
                raise ValueError("CREATE support_mode must be MERGE")
        if self.contest and self.target != "EXISTING":
            raise ValueError("Only EXISTING may be CONTEST")
        return self


class KeyProjectionDraftV01(BaseModel):
    contract: str = KEY_PROJECTOR_CONTRACT
    mutations: tuple[KeyProjectionMutationDraftV01, ...] = ()
    no_change_proposition_ids: tuple[str, ...] = ()
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=2400)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != KEY_PROJECTOR_CONTRACT:
            raise ValueError(f"contract must be {KEY_PROJECTOR_CONTRACT}")
        return self


class TwoStageSlotDecisionV01(BaseModel):
    delta: SlotDeltaV01 | None
    proposition_basis: tuple[AtomicPropositionV01, ...]


_NORMALIZER_SYSTEM = """You are the RAOS semantic normalizer.

Do exactly one job: convert NEW audited semantic units into an atomic proposition basis.
Do NOT resolve Current State keys. Do NOT decide CREATE/UPSERT. Do NOT write slot values.

Return JSON only:
{
  "contract": "event-proposition-normalizer-v0.1",
  "propositions": [
    {
      "support_key": "N001",
      "proposition": "one atomic proposition",
      "plane": "WORLD | IDENTITY | EVIDENCE | PERIPHERAL_OR_REDUNDANT",
      "primitive_family": "STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER | null",
      "rationale": "brief"
    }
  ]
}

Rules:
- Every NEW support key must appear in at least one proposition row.
- One support key may produce MULTIPLE proposition rows.
- Each proposition must be atomic: it should express one independently variable semantic claim.
- Split conjunctions across primitive axes. Example: "typed output and 300ms latency" -> FORM proposition + QUALITY proposition.
- Split World content from epistemic qualifiers. Example: "20x faster, no independent benchmark" -> WORLD/QUALITY + EVIDENCE.
- IDENTITY is about what referent/episode this is. WORLD is mutable truth about the already-identified Event/entity.
- EVIDENCE is provenance, support strength, corroboration, confidence, validation maturity, source completeness.
- PERIPHERAL_OR_REDUNDANT is source reaction, presentation mechanics, hype, or content with no material semantic proposition.
- WORLD primitive families:
  STATE=current condition/lifecycle/availability;
  STRUCTURE=composition/parts/organization/topology;
  PROCESS=internal mechanism/dynamics/transformation/procedure;
  FORM=manifestation/representation/interface/output-action form;
  DISPOSITION=capability/function/tendency/realizable behavior;
  QUALITY=performance/quantity/correctness/reliability/cost/rate/magnitude;
  RELATION=role/context/affordance/suitability/relation to other entities;
  OTHER=material World proposition that cannot coherently fit the above.
- Surface words like benefit/feature/advantage are not primitive axes. Decompose their underlying claims.
- A missing fact in one Source is not a negative World proposition.
- Be complete but minimal. Do not summarize the whole Source.
"""


_PROJECTOR_SYSTEM = """You are the RAOS keyed World-state projector.

Input WORLD propositions have ALREADY been atomized and assigned exactly one primitive family.
Do not re-parse source sentences. Do not change plane classification.
Your only job is to map each WORLD proposition to Current State.

Return JSON only:
{
  "contract": "event-state-key-projector-v0.1",
  "mutations": [
    {
      "target": "EXISTING | CREATE",
      "existing_slot_key": "S001 or null",
      "primitive_family": "required only for CREATE",
      "slot_label": "required only for CREATE",
      "state_question": "required only for CREATE",
      "value": "complete current sufficient answer after this update",
      "proposition_ids": ["Q001"],
      "support_mode": "MERGE | REPLACE",
      "contest": false,
      "rationale": "brief"
    }
  ],
  "no_change_proposition_ids": ["Q002"],
  "phase_change": "EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale": "brief"
}

Rules:
- Cover every WORLD proposition id exactly once: either in one mutation or in no_change_proposition_ids.
- Each atomic proposition maps to at most one semantic coordinate.
- EXISTING: use only when the proposition directly changes the answer to that exact state_question AND primitive_family matches.
- CREATE: use when a material proposition represents a genuinely new primitive-bounded coordinate.
- Same-family facets may share one coordinate when they answer the same general state question (e.g. latency/speed/cost -> operational performance).
- Different state questions remain separate even inside the same primitive family (e.g. performance quality vs output correctness quality).
- Generality is cross-domain reuse, not semantic breadth. Avoid umbrella questions like "How does it work?".
- Do not optimize for fewer keys.
- no_change is for a WORLD proposition already sufficiently represented and not materially changing the current answer.
- Existing key semantics are immutable. For EXISTING do not output a new label/question/family; they are derived from the slot.
- support_mode=MERGE normally. REPLACE only for explicit correction/supersession where previous support should no longer ground the current value.
- contest=true only for unresolved incompatible assertions on the same existing coordinate.
- Values contain World content, not provenance/support commentary.
"""


def _support_aliases(
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    previous_refs = {
        ref
        for slot in (previous.slots if previous is not None else ())
        for ref in slot.support_refs
    }
    new_refs = set(observation.audited_semantic_unit_refs)
    prev = {ref: f"P{i:03d}" for i, ref in enumerate(sorted(previous_refs), 1)}
    new = {ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), 1)}
    reverse = {**{v: k for k, v in prev.items()}, **{v: k for k, v in new.items()}}
    return reverse, prev, new


def _slot_aliases(previous: SemanticSlotStateV01 | None):
    if previous is None:
        return {}, {}
    ordered = sorted(previous.slots, key=lambda row: row.slot_id)
    key_by_id = {slot.slot_id: f"S{i:03d}" for i, slot in enumerate(ordered, 1)}
    id_by_key = {alias: slot_id for slot_id, alias in key_by_id.items()}
    return id_by_key, key_by_id


def _units_with_keys(rows: list[dict], key_by_ref: dict[str, str]):
    result = []
    for row in rows:
        ref = str(row.get("unit_id") or "").strip()
        if ref not in key_by_ref:
            raise ValueError(f"Semantic unit outside support map: {ref}")
        item = {k: v for k, v in row.items() if k != "unit_id"}
        item["support_key"] = key_by_ref[ref]
        result.append(item)
    return result


def normalize_new_propositions(
    *,
    event_identity: dict,
    observation: EventObservationV01,
    new_semantic_units: list[dict],
    chat_fn,
) -> tuple[AtomicPropositionV01, ...]:
    new_refs = set(observation.audited_semantic_unit_refs)
    new_key_by_ref = {
        ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), 1)
    }
    payload = {
        "event_identity": dict(event_identity),
        "new_semantic_units": _units_with_keys(new_semantic_units, new_key_by_ref),
        "allowed_new_support_keys": sorted(new_key_by_ref.values()),
    }
    obj, _meta, _events = chat_json_schema(
        [
            {"role": "system", "content": _NORMALIZER_SYSTEM},
            {
                "role": "user",
                "content": "Build the atomic proposition basis.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
            },
        ],
        PropositionBasisDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = PropositionBasisDraftV01.model_validate(obj)
    expected = set(new_key_by_ref.values())
    observed = {row.support_key for row in draft.propositions}
    if observed != expected:
        raise ValueError(
            "Proposition basis must cover every NEW support key; "
            f"missing={sorted(expected-observed)} unknown={sorted(observed-expected)}"
        )

    result = []
    for i, row in enumerate(draft.propositions, 1):
        result.append(
            AtomicPropositionV01(
                proposition_id=f"Q{i:03d}",
                support_key=row.support_key,
                proposition=row.proposition,
                plane=row.plane,
                primitive_family=row.primitive_family,
            )
        )
    return tuple(result)


def project_world_propositions(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    propositions: tuple[AtomicPropositionV01, ...],
    chat_fn,
) -> SlotDeltaV01 | None:
    world = tuple(row for row in propositions if row.plane == "WORLD")
    if not world:
        return None

    ref_by_key, prev_key_by_ref, new_key_by_ref = _support_aliases(
        previous, observation
    )
    slot_id_by_key, slot_key_by_id = _slot_aliases(previous)
    previous_slots = []
    if previous is not None:
        for slot in sorted(previous.slots, key=lambda row: row.slot_id):
            previous_slots.append(
                {
                    "slot_key": slot_key_by_id[slot.slot_id],
                    "primitive_family": slot.primitive_family,
                    "slot_label": slot.slot_label,
                    "state_question": slot.state_question,
                    "value": slot.value,
                }
            )

    payload = {
        "event_identity": dict(event_identity),
        "previous_status": previous.status if previous is not None else None,
        "previous_slots": previous_slots,
        "world_propositions": [row.model_dump(mode="json") for row in world],
        "allowed_existing_slot_keys": sorted(slot_id_by_key),
    }
    obj, _meta, _events = chat_json_schema(
        [
            {"role": "system", "content": _PROJECTOR_SYSTEM},
            {
                "role": "user",
                "content": "Project the atomic World propositions into keyed state.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
            },
        ],
        KeyProjectionDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = KeyProjectionDraftV01.model_validate(obj)

    world_by_id = {row.proposition_id: row for row in world}
    seen = []
    for mutation in draft.mutations:
        seen.extend(mutation.proposition_ids)
    seen.extend(draft.no_change_proposition_ids)
    if len(seen) != len(set(seen)):
        raise ValueError("Each WORLD proposition must be routed exactly once")
    if set(seen) != set(world_by_id):
        raise ValueError(
            "Projection must cover every WORLD proposition exactly once; "
            f"missing={sorted(set(world_by_id)-set(seen))} "
            f"unknown={sorted(set(seen)-set(world_by_id))}"
        )

    mutations = []
    for idx, row in enumerate(draft.mutations):
        props = [world_by_id[qid] for qid in row.proposition_ids]
        families = {prop.primitive_family for prop in props}
        if len(families) != 1:
            raise ValueError(
                "One Slot mutation may group only one primitive family; "
                f"families={sorted(str(x) for x in families)}"
            )
        family = next(iter(families))
        new_support_refs = {
            ref_by_key[prop.support_key]
            for prop in props
        }

        if row.target == "EXISTING":
            slot_id = slot_id_by_key.get(row.existing_slot_key or "")
            if slot_id is None:
                raise ValueError(
                    f"Unknown existing slot key: {row.existing_slot_key}"
                )
            previous_slot = next(
                slot for slot in previous.slots if slot.slot_id == slot_id
            )
            if family != previous_slot.primitive_family:
                raise ValueError(
                    "Primitive family mismatch for EXISTING projection; "
                    f"prop={family} slot={previous_slot.primitive_family}"
                )
            if row.support_mode == "MERGE":
                supports = set(previous_slot.support_refs) | new_support_refs
            else:
                supports = new_support_refs
            slot = CurrentSlotV01(
                slot_id=slot_id,
                primitive_family=previous_slot.primitive_family,
                slot_label=previous_slot.slot_label,
                state_question=previous_slot.state_question,
                value=row.value,
                support_refs=tuple(sorted(supports)),
            )
            mode: SlotMutationMode = "CONTEST" if row.contest else "UPSERT"
        else:
            if row.primitive_family != family:
                raise ValueError(
                    "CREATE primitive family must match assigned propositions; "
                    f"mutation={row.primitive_family} propositions={family}"
                )
            slot = CurrentSlotV01(
                slot_id=_new_slot_id(
                    event_id=observation.event_id,
                    observation_key=observation.observation_key,
                    ordinal=idx,
                    state_question=row.state_question or "",
                ),
                primitive_family=family,
                slot_label=row.slot_label or "",
                state_question=row.state_question or "",
                value=row.value,
                support_refs=tuple(sorted(new_support_refs)),
            )
            mode = "CREATE"
        mutations.append(
            SlotMutationV01(
                mode=mode,
                slot=slot,
                rationale=row.rationale,
            )
        )

    if not mutations:
        return None
    return SlotDeltaV01(
        mutations=tuple(mutations),
        phase_change=draft.phase_change,
        rationale=draft.rationale,
    )


def decide_slot_delta_two_stage_with_audit(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> TwoStageSlotDecisionV01:
    # previous_support_units stays in the compatible signature; Stage B uses the
    # already materialized slot values/support and does not need to re-read old text.
    del previous_support_units
    propositions = normalize_new_propositions(
        event_identity=event_identity,
        observation=observation,
        new_semantic_units=new_semantic_units,
        chat_fn=chat_fn,
    )
    delta = project_world_propositions(
        event_identity=event_identity,
        previous=previous,
        observation=observation,
        propositions=propositions,
        chat_fn=chat_fn,
    )
    return TwoStageSlotDecisionV01(
        delta=delta,
        proposition_basis=propositions,
    )


def decide_slot_delta_two_stage(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> SlotDeltaV01 | None:
    return decide_slot_delta_two_stage_with_audit(
        event_identity=event_identity,
        previous=previous,
        observation=observation,
        previous_support_units=previous_support_units,
        new_semantic_units=new_semantic_units,
        chat_fn=chat_fn,
    ).delta
