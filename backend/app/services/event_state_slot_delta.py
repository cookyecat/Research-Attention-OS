from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.cognitive.client import chat_json_schema
from app.services.event_observation import EventObservationV01
from app.services.semantic_primitives import PrimitiveFamily
from app.services.event_state import (
    EventStateV02,
    WorldStateV02,
    make_event_state_v02,
    structural_evidence_state_v02,
)


SLOT_STATE_CONTRACT = "event-semantic-slot-state-v0.2"
SLOT_DELTA_CONTRACT = "event-state-slot-delta-v0.2"
SLOT_DECIDER_CONTRACT = "event-state-slot-decider-v1.5"
SLOT_APPLIER_CONTRACT = "event-state-slot-applier-v0.2"

SlotMutationMode = Literal["CREATE", "UPSERT", "CONTEST"]
DraftTarget = Literal["CREATE", "EXISTING"]
EventPhase = Literal["EMERGING", "ACTIVE", "CONTESTED", "RESOLVED"]
EvidenceDisposition = Literal[
    "WORLD_MUTATION",
    "IDENTITY",
    "EVIDENCE",
    "PERIPHERAL_OR_REDUNDANT",
]


def _stable_digest(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
class CurrentSlotV01(BaseModel):
    slot_id: str = Field(min_length=8)
    primitive_family: PrimitiveFamily
    slot_label: str = Field(min_length=1, max_length=200)
    state_question: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=6000)
    support_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize(self):
        object.__setattr__(self, "slot_label", " ".join(self.slot_label.split()))
        object.__setattr__(self, "state_question", " ".join(self.state_question.split()))
        object.__setattr__(self, "value", " ".join(self.value.split()))
        refs = tuple(sorted({str(v).strip() for v in self.support_refs if str(v).strip()}))
        if not refs:
            raise ValueError("CurrentSlot requires support_refs")
        object.__setattr__(self, "support_refs", refs)
        return self


class SemanticSlotStateV01(BaseModel):
    contract: str = SLOT_STATE_CONTRACT
    event_id: UUID
    slots: tuple[CurrentSlotV01, ...]
    status: EventPhase
    effective_at: datetime | None = None
    state_digest: str

    @model_validator(mode="after")
    def validate_digest(self):
        expected = slot_state_digest(
            event_id=self.event_id,
            slots=self.slots,
            status=self.status,
            effective_at=self.effective_at,
        )
        if self.state_digest != expected:
            raise ValueError("event-semantic-slot-state-v0.1 digest mismatch")
        return self
def slot_state_digest(
    *,
    event_id: UUID,
    slots: tuple[CurrentSlotV01, ...],
    status: EventPhase,
    effective_at: datetime | None,
) -> str:
    ordered = tuple(sorted(slots, key=lambda row: row.slot_id))
    return _stable_digest(
        {
            "contract": SLOT_STATE_CONTRACT,
            "event_id": str(event_id),
            "slots": [row.model_dump(mode="json") for row in ordered],
            "status": status,
            "effective_at": effective_at,
        }
    )


def make_slot_state(
    *,
    event_id: UUID,
    slots: tuple[CurrentSlotV01, ...],
    status: EventPhase,
    effective_at: datetime | None,
) -> SemanticSlotStateV01:
    ordered = tuple(sorted(slots, key=lambda row: row.slot_id))
    return SemanticSlotStateV01(
        event_id=event_id,
        slots=ordered,
        status=status,
        effective_at=effective_at,
        state_digest=slot_state_digest(
            event_id=event_id,
            slots=ordered,
            status=status,
            effective_at=effective_at,
        ),
    )
class SlotMutationV01(BaseModel):
    mode: SlotMutationMode
    slot: CurrentSlotV01
    rationale: str | None = Field(default=None, max_length=2000)


class SlotDeltaV01(BaseModel):
    contract: str = SLOT_DELTA_CONTRACT
    mutations: tuple[SlotMutationV01, ...] = Field(min_length=1)
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_mutations(self):
        ids = [row.slot.slot_id for row in self.mutations]
        if len(ids) != len(set(ids)):
            raise ValueError("SlotDelta may mutate each slot_id at most once")
        return self


class DraftSlotMutationV01(BaseModel):
    target: DraftTarget
    existing_slot_key: str | None = None
    primitive_family: PrimitiveFamily
    slot_label: str = Field(min_length=1, max_length=200)
    state_question: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=6000)
    support_keys: tuple[str, ...] = ()
    contest: bool = False
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_target(self):
        if self.target == "EXISTING" and not self.existing_slot_key:
            raise ValueError("EXISTING mutation requires existing_slot_key")
        if self.target == "CREATE" and self.existing_slot_key is not None:
            raise ValueError("CREATE mutation may not set existing_slot_key")
        return self
class NewEvidencePropositionV01(BaseModel):
    support_key: str = Field(min_length=1)
    proposition: str = Field(min_length=1, max_length=2000)
    disposition: EvidenceDisposition
    primitive_family: PrimitiveFamily | None = None
    mutation_indices: tuple[int, ...] = ()
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_shape(self):
        object.__setattr__(self, "proposition", " ".join(self.proposition.split()))
        indices = tuple(sorted(set(self.mutation_indices)))
        object.__setattr__(self, "mutation_indices", indices)
        if self.disposition == "WORLD_MUTATION":
            if self.primitive_family is None:
                raise ValueError(
                    "WORLD_MUTATION proposition requires primitive_family"
                )
            if not indices:
                raise ValueError("WORLD_MUTATION proposition requires mutation_indices")
            if any(index < 0 for index in indices):
                raise ValueError("mutation_indices must be non-negative")
        else:
            if self.primitive_family is not None:
                raise ValueError(
                    f"{self.disposition} proposition may not set primitive_family"
                )
            if indices:
                raise ValueError(
                    f"{self.disposition} proposition may not reference mutations"
                )
        return self


# Transitional import alias for focused tests/tools; v1.1 semantics are proposition-level.
NewEvidenceDispositionV01 = NewEvidencePropositionV01


class SlotDeltaDraftV01(BaseModel):
    contract: str = SLOT_DECIDER_CONTRACT
    mutations: tuple[DraftSlotMutationV01, ...] = ()
    evidence_projection: tuple[NewEvidencePropositionV01, ...]
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != SLOT_DECIDER_CONTRACT:
            raise ValueError(f"contract must be {SLOT_DECIDER_CONTRACT}")
        return self


class SlotDecisionV01(BaseModel):
    delta: SlotDeltaV01 | None
    evidence_projection: tuple[NewEvidencePropositionV01, ...]


class SlotApplyResultV01(BaseModel):
    contract: str = SLOT_APPLIER_CONTRACT
    previous_slot_state_digest: str | None
    observation_key: str
    slot_state: SemanticSlotStateV01
    event_state: EventStateV02


_DECIDE_SYSTEM = """You are the RAOS ResolveKey + SlotDelta Decide function.

Commercial keyed materialized views keep one current live value per stable key. Your job is to project NEW audited evidence into the Event's existing semantic state dimensions.

The immutable evidence history is NOT the current state.
Current State is a keyed map of semantic state questions.

Return exactly one JSON object:
{
  "contract": "event-state-slot-decider-v1.5",
  "mutations": [
    {
      "target": "EXISTING | CREATE",
      "existing_slot_key": "S001 or null",
      "primitive_family": "STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER",
      "slot_label": "short human label",
      "state_question": "the broad current-state question answered by this slot",
      "value": "the complete new current value for this slot after applying this observation",
      "support_keys": ["P001", "N001"],
      "contest": false,
      "rationale": "brief reason"
    }
  ],
  "evidence_projection": [
    {
      "support_key": "N001",
      "proposition": "one atomic semantic proposition extracted from N001",
      "disposition": "WORLD_MUTATION | IDENTITY | EVIDENCE | PERIPHERAL_OR_REDUNDANT",
      "primitive_family": "STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER | null",
      "mutation_indices": [0],
      "rationale": "brief proposition-level routing reason"
    }
  ],
  "phase_change": "EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale": "brief overall explanation"
}
Rules:
- PROPOSITION BASIS GATE: before finalizing mutations, decompose EVERY NEW support key Nxxx into one or more atomic semantic propositions in evidence_projection.
- One N-key may appear in MULTIPLE evidence_projection rows when the semantic unit contains multiple independent propositions or mixes World content with Identity/Evidence qualifiers.
- Each evidence_projection row must contain exactly one proposition. Do not use the whole source sentence as one proposition when it contains conjunctions that can vary independently.
- Classify EACH proposition separately as WORLD_MUTATION, IDENTITY, EVIDENCE, or PERIPHERAL_OR_REDUNDANT.
- For WORLD_MUTATION, also assign exactly one primitive_family:
  STATE=current condition/lifecycle/availability;
  STRUCTURE=composition/parts/organization/topology;
  PROCESS=intrinsic/internal mechanism, dynamics, transformation, or control process of the focal entity itself;
  FORM=manifestation/representation/interface/output-action form;
  DISPOSITION=capability/function/tendency/realizable behavior;
  QUALITY=performance/quantity/correctness/reliability/cost/rate/magnitude;
  RELATION=role/context/affordance/suitability/relation to other entities;
  OTHER=material World proposition that cannot yet be typed coherently.
- For non-WORLD propositions, primitive_family MUST be null.
- Every mutation also has one primitive_family. A WORLD proposition may route to a mutation ONLY when their primitive_family values are identical.
- WORLD_MUTATION propositions must reference every mutation index that proposition materially supports. One atomic World proposition may support multiple mutations only when it genuinely directly answers multiple state questions within the same primitive family.
- IDENTITY / EVIDENCE / PERIPHERAL_OR_REDUNDANT propositions must use an empty mutation_indices list.
- NEW mutation grounding is derived deterministically from WORLD_MUTATION proposition rows. Do not rely on mutation.support_keys to duplicate NEW routing authority.
- Every proposed mutation must be referenced by at least one WORLD_MUTATION proposition.
- Multi-proposition observations must preserve ALL distinct material World dimensions. Do not drop an independent dimension merely because another proposition from the same N-key already updated a slot.
- Key existence must NOT depend on source count, independent corroboration, confidence, or benchmark maturity. Those affect the Evidence plane, not whether a material World coordinate exists.
- FINAL BASIS SELF-CHECK: for each N-key ask: "What are the independently variable propositions inside this unit? Which plane does each belong to? If World, which coordinate does each directly answer?" Do not return until every N-key has at least one proposition row and every material World proposition is represented.
- CURRENT SLOTS ARE WORLD-STATE COORDINATES. Event Identity is supplied separately. Evidence/provenance is supplied separately. Do not mix these planes.

CREATE GATE A — PLANE PURITY:
- IDENTITY asks what referent/episode this is: name, stable actor/object identity, identity-defining type, identity time/location boundary. Do NOT CREATE a mutable World slot for Identity. Identity changes belong to a separate Event identity/resolution path.
- EVIDENCE asks why RAOS believes a proposition: source independence, corroboration, confidence, validation maturity, source completeness, provenance, "not independently verified". Do NOT CREATE a World slot whose primary question is about evidence/validation/confidence.
- WORLD asks what is currently true of the already-identified Event/entity. Only WORLD questions may become slots.
- A reported but unverified WORLD proposition may still CREATE or UPSERT a World slot when the proposition itself is material. Low confidence, single-source support, or lack of independent reproduction does NOT by itself justify DROP. Preserve cautious wording such as "reported" or "claimed" when needed, while keeping confidence/provenance in the Evidence plane.
- Example: "the author reports 20x faster performance, with no independent benchmark" contains a material WORLD performance proposition plus an EVIDENCE qualifier. The performance proposition may create/update Performance; "no independent benchmark" must not create Validation and must not cause the performance proposition to disappear.
- HARD OUT-OF-PLANE RULE: if NEW evidence is exclusively IDENTITY and/or EVIDENCE information and does not directly change any WORLD answer, return an empty mutations list. Important out-of-plane evidence still belongs in History / its own pipeline; importance does not justify a placeholder World mutation.
- Never use an unchanged existing World slot as a carrier, placeholder, acknowledgement, or preservation record for Identity/Evidence-only information.

CREATE GATE B — GENERALITY WITHOUT SEMANTIC BREADTH:
- A new state_question should be reusable across domains, not tied to one proper noun, source, demo, or benchmark. Mentally replace the concrete subject with "this entity/event/system"; the question should remain coherent.
- GENERALITY is domain-independence, NOT semantic breadth. A key may be universal while still being tightly bounded to one primitive axis.
- Avoid umbrella questions such as "How does this system work?", "What is this system like?", or "What do we know about it?" because they can absorb multiple orthogonal primitives.
- Prefer primitive-bounded universal questions. Example: "What internal process or mechanism transforms inputs/state into outputs/actions?" is better than "How does it work?". "What capabilities or behaviors has this system demonstrated?" is better than "What games has Jev played?".
- Do not create keys named after one source, one demo, one benchmark, one application example, one vertical workflow, or one proper noun when a more general but still primitive-bounded coordinate captures the same dimension.
- If a proposed new question only makes sense after naming a specific application domain (trading, gaming, browser automation, driving, etc.), first test whether it is merely an instance/value of a general Capability, Affordance/Relation, Performance, or internal Mechanism coordinate. Domain-specific process instances should almost never become top-level keys.

CREATE GATE C — DIRECT ANSWER + PRIMITIVE FAMILY + COUNTERFACTUAL INDEPENDENCE:
- DIRECT ANSWER TEST is mandatory. A proposition may UPSERT an existing slot only if the proposition itself directly answers that exact state_question.
- Causal relevance, explanation, correlation, implementation cause, contextual relevance, or being mentioned in the same demo do NOT count as directly answering the question.
- Example: mechanism evidence may explain why performance is fast, but if it gives no new speed/cost/latency/throughput proposition it MUST NOT mutate Performance. Likewise performance evidence MUST NOT mutate Mechanism unless it directly states how the system works.
- If a material WORLD proposition fails the Direct Answer Test for every existing key, do not DROP it merely because it is topically related to an existing slot. Continue to the CREATE test.
- NO-EXISTING-KEY IS NOT A DROP REASON. If a concrete material WORLD proposition belongs to a coherent primitive family (for example mechanism/process, structure, form, capability/disposition, quality/performance, lifecycle/state, or relation/affordance) and no existing state_question directly represents that coordinate, CREATE a new primitive-bounded key. The absence of a matching slot is precisely the CREATE case, not evidence that the proposition is peripheral.
- PERIPHERAL_OR_REDUNDANT is reserved for genuinely peripheral/source-level content (reaction, hype, presentation mechanics, trivia) or a proposition whose current World meaning is already sufficiently represented. Never label a concrete new mechanism, structure, form, capability, quality, lifecycle, or affordance proposition peripheral solely because it is the first observation of that dimension.
- Before creating a narrower key, ask whether the proposition is merely another metric, facet, instance, example, or subtype of an existing primitive semantic family. If yes, UPSERT the broader existing coordinate.
- Same-primitive facets belong in one key even when their numeric values can vary independently. Example: latency, throughput, speed, and inference rate are facets of operational performance; Mario/DOOM/Tetris are instances of demonstrated capability.
- Different primitives must remain separate even when one Source states them together. Example: output/interface form is not internal mechanism; output/interface form is not reliability; mechanism is not performance; demonstrated capability is not proposed affordance.
- FORM / MANIFESTATION is a material World dimension when it describes a stable way the entity expresses or exposes its outputs/actions (e.g. typed structured judgments vs free-form strings, event stream vs batch result, API vs physical act). Do not DROP such a proposition merely because it does not alter the internal mechanism.
- CONJUNCTION DECOMPOSITION: decompose a semantic unit or observation into each independently meaningful WORLD proposition before routing. If one demo states what the system did, how fast it did it, and what role it may be suited for, these may require separate Capability, Performance, and Affordance mutations. Do not hide one primitive as a descriptive clause inside another primitive's value.
- ONE UNIT MAY PROJECT TO MULTIPLE AXES. If one N-key contains two independent World propositions, mark that same N-key as WORLD_MUTATION for every affected mutation index. Unit granularity does not limit state dimensionality.
- SURFACE-WRAPPER RULE: words such as "benefit", "advantage", "feature", "strength", "selling point", or "good thing" are not primitive state dimensions. Decompose the underlying propositions into their real axes (e.g. performance, reliability/correctness, form, mechanism, affordance). Never CREATE a generic "benefits" or "advantages" slot merely because a source groups claims rhetorically.
- A negative meta-clause such as "this source gives no new performance information" does not cancel an affirmative mechanism proposition in the same unit. Route the affirmative proposition by what it directly says.
- If no existing key fits, compare ALL proposed CREATE mutations with each other before returning. Two new CREATE questions must not overlap by subtype, metric, facet, or example containment. If one proposed question is a narrower facet of another, merge them into the more general coherent primitive key.
- After primitive-family normalization, use counterfactual independence across DIFFERENT primitives: a new key should represent a genuinely independently variable World dimension rather than a topical restatement.
- Do not optimize for fewer keys. Optimize for stable, plane-pure, general primitive coordinates with potentially multi-facet values.

UPPER-LEVEL INSPIRATIONS, NOT A FIXED ONTOLOGY:
- lifecycle / phase: what condition or availability state is it in now?
- structure / composition: what is it made of or organized as?
- mechanism / dynamics: what INTERNAL process of the focal entity transforms inputs/state into outputs/actions?
- form / manifestation / interface: in what form, structure, representation, or interface is the resulting state/output/action expressed?
- APPLICATION WORKFLOW IS NOT INTERNAL MECHANISM. A domain workflow in which the focal entity participates (for example observe → decide → act in one application) is normally an instance of demonstrated capability/behavior or a role/context relation. Do not CREATE a PROCESS key merely because a source describes an application as a sequence of steps.
- A PROCESS key is justified when the proposition describes the focal entity's own reusable INTERNAL implementation/control architecture, not a one-off vertical workflow.
- INTERNAL-vs-BEHAVIOR TEST: if the steps are expressed mainly as semantic actions in an external environment (observe/read X → decide Y → send/place/do Z → repeat), that is demonstrated behavior/capability, not internal PROCESS. The application/domain in which those actions occur may separately update a RELATION/context/affordance coordinate.
- PROCESS should describe implementation-level transformation that remains meaningful even if the application domain nouns are replaced (e.g. decoder pass, cache reuse, internal planner/controller architecture). Do not infer an internal mechanism merely from an externally visible action sequence.
- capability / behavior: what can or does it do?
- quality / quantity: how well, how much, at what cost?
- relation / context / affordance: where, with what, or for what can it participate?
These are examples for abstraction only. Do not force them when the evidence does not justify them.
- AFFORDANCE IS NOT DEMONSTRATED CAPABILITY. A material proposed/intended/suitable application may update a Relation/Affordance coordinate even before it has been demonstrated. Use cautious wording ("proposed", "intended", "claimed suitable") for the World proposition. Do not pretend it is a demonstrated Capability.
- Generic hype such as "this will change everything" remains peripheral; a concrete material application or role can be an Affordance World proposition.

EXISTING KEY RULES:
- SlotDelta is a DELTA, not a snapshot. Emit an EXISTING mutation only when NEW evidence materially changes the WORLD proposition represented by that slot.
- WORLD-VALUE CHANGE TEST: if new evidence changes only provenance, confidence, corroboration, validation maturity, or support strength while the current World answer remains semantically the same, emit NO World mutation for that slot. EvidenceState may still change.
- Do not append phrases such as "independently reproduced", "more strongly supported", "not independently verified", or source-count metadata merely to make an unchanged World value look updated.
- Do not re-emit, restate, preserve, refresh, or summarize an unchanged existing slot merely because it is relevant context.
- An existing slot's state_question is immutable key semantics. For EXISTING, copy it EXACTLY, character-for-character. Never broaden or narrow it during UPSERT.
- Repeated examples about the same semantic coordinate should UPSERT the existing slot only when the new example materially changes the current sufficient answer.
- Before emitting any EXISTING mutation, finish this sentence literally: "The new WORLD proposition directly changes the answer to <state_question> because ...". If that sentence cannot be completed without words like "explains", "relates to", "may cause", or "is relevant to", do NOT mutate that slot.
- A single observation may mutate multiple slots if it genuinely changes multiple independent dimensions.

OPEN-WORLD UPDATE RULE:
- Absence of a fact from the new Source is not evidence that the fact is false, unknown globally, or no longer current.
- Source-local wording such as "this source does not specify X", "X is not given here", or a missing field is normally NO CHANGE for X.
- Only affirmative new evidence, an explicit correction/retraction, or a materially incompatible assertion may change the affected slot.
- Do not CREATE a new uncertainty or duplicate identity slot merely because a later Source is less complete than accumulated Current State.

VALUE RULES:
- For EXISTING, output the full CURRENT SUFFICIENT answer after the update, not a patch fragment and not a chronology.
- Keep the WORLD proposition in the value. Remove source/presentation boilerplate, audience reactions, post/thread mechanics, playback speed, missing-author trivia, and generic speculation unless they change that exact World answer.
- Epistemic caveats may qualify a proposition when needed to avoid overstating uncertain evidence, but provenance/validation must not become the slot's semantic axis.
- Every mutation must use at least one N-key from the new observation.
- Support may use P-keys and N-keys. Use the smallest grounding that supports the complete updated value.
- contest=true only for unresolved incompatible WORLD assertions. Preserve support for both live sides.
- Explicit correction updates the same affected slot; do not CREATE a replacement slot.
- phase_change is normally null. RESOLVED means the whole Event episode explicitly closes.
- Do not invent evidence, support keys, state dimensions, confidence scores, or a fixed ontology.
"""


def _support_aliases(
    previous_support_refs: set[str],
    new_refs: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    prev = {ref: f"P{i:03d}" for i, ref in enumerate(sorted(previous_support_refs), 1)}
    new = {ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), 1)}
    reverse = {**{v: k for k, v in prev.items()}, **{v: k for k, v in new.items()}}
    return reverse, prev, new
def _slot_aliases(
    previous: SemanticSlotStateV01 | None,
) -> tuple[dict[str, str], dict[str, str]]:
    if previous is None:
        return {}, {}
    ordered = sorted(previous.slots, key=lambda row: row.slot_id)
    key_by_id = {row.slot_id: f"S{i:03d}" for i, row in enumerate(ordered, 1)}
    id_by_key = {key: slot_id for slot_id, key in key_by_id.items()}
    return id_by_key, key_by_id


def _units_with_keys(rows: list[dict], key_by_ref: dict[str, str]) -> list[dict]:
    result = []
    for row in rows:
        ref = str(row.get("unit_id") or "").strip()
        if ref not in key_by_ref:
            raise ValueError(f"Semantic unit outside support-key map: {ref}")
        item = {k: v for k, v in row.items() if k != "unit_id"}
        item["support_key"] = key_by_ref[ref]
        result.append(item)
    return result


def _new_slot_id(
    *,
    event_id: UUID,
    observation_key: str,
    ordinal: int,
    state_question: str,
) -> str:
    return _stable_digest(
        {
            "event_id": str(event_id),
            "observation_key": observation_key,
            "ordinal": ordinal,
            "state_question": " ".join(state_question.split()),
        }
    )
def _prune_unreferenced_mutations(
    draft: SlotDeltaDraftV01,
) -> SlotDeltaDraftV01:
    """Drop snapshot-like mutations with no NEW World proposition cause.

    SlotDelta is a delta, not a materialized snapshot. If no WORLD_MUTATION
    proposition references a proposed mutation, that mutation has no admitted
    semantic cause in the new observation and is deterministically removed.
    Proposition mutation indices are then remapped to the compacted mutation list.
    """
    referenced = sorted({
        index
        for row in draft.evidence_projection
        if row.disposition == "WORLD_MUTATION"
        for index in row.mutation_indices
    })
    if any(index >= len(draft.mutations) for index in referenced):
        # Preserve the original fail-closed behavior for invalid references.
        return draft
    if referenced == list(range(len(draft.mutations))):
        return draft

    old_to_new = {old: new for new, old in enumerate(referenced)}
    mutations = tuple(draft.mutations[old] for old in referenced)
    projection = []
    for row in draft.evidence_projection:
        if row.disposition != "WORLD_MUTATION":
            projection.append(row)
            continue
        remapped = tuple(
            old_to_new[index]
            for index in row.mutation_indices
            if index in old_to_new
        )
        projection.append(
            row.model_copy(update={"mutation_indices": remapped})
        )
    return draft.model_copy(
        update={
            "mutations": mutations,
            "evidence_projection": tuple(projection),
        }
    )


def _normalize_mutation_support_by_projection(
    *,
    draft: SlotDeltaDraftV01,
    expected_new_keys: set[str],
) -> SlotDeltaDraftV01:
    """Deterministically enforce the model's own plane ledger on World grounding.

    Previous P-keys remain eligible. A NEW N-key may ground a World mutation only
    when the same draft classifies it as WORLD_MUTATION for that mutation.
    Contradictory non-World N-key support is pruned rather than sent back to the
    LLM. If no legitimate NEW World support remains, downstream validation fails
    closed.
    """
    disposition_by_key = {
        row.support_key: row
        for row in draft.evidence_projection
    }
    normalized = []
    for index, mutation in enumerate(draft.mutations):
        # Previous P-keys may be selected by the model for sufficient old grounding.
        # NEW N-key grounding has exactly one authority source: evidence_projection.
        # This removes duplicated model authority between support_keys and the ledger.
        previous_keys = [
            key for key in mutation.support_keys
            if key not in expected_new_keys
        ]
        routed_new_keys = [
            row.support_key
            for row in draft.evidence_projection
            if (
                row.disposition == "WORLD_MUTATION"
                and index in row.mutation_indices
            )
        ]
        support_keys = tuple(dict.fromkeys(previous_keys + routed_new_keys))
        normalized.append(
            mutation.model_copy(update={"support_keys": support_keys})
        )
    return draft.model_copy(update={"mutations": tuple(normalized)})


def _validate_evidence_projection(
    *,
    draft: SlotDeltaDraftV01,
    expected_new_keys: set[str],
) -> None:
    """Validate proposition-level basis coverage and World routing.

    A single NEW semantic unit may contain multiple propositions, so support_key
    repetition is legal and expected. The union of WORLD_MUTATION proposition
    routes for a support_key must match the mutations deterministically grounded
    by that key after normalization.
    """
    rows = list(draft.evidence_projection)
    observed = {row.support_key for row in rows}
    if observed != expected_new_keys:
        missing = sorted(expected_new_keys - observed)
        unknown = sorted(observed - expected_new_keys)
        raise ValueError(
            "Evidence proposition basis must cover every NEW support key; "
            f"missing={missing} unknown={unknown}"
        )

    seen_rows: set[tuple] = set()
    for row in rows:
        signature = (
            row.support_key,
            row.proposition,
            row.disposition,
            tuple(row.mutation_indices),
        )
        if signature in seen_rows:
            raise ValueError(
                "Evidence proposition basis contains an exact duplicate row; "
                f"support_key={row.support_key} proposition={row.proposition!r}"
            )
        seen_rows.add(signature)

    used_by: dict[str, set[int]] = {key: set() for key in expected_new_keys}
    for index, mutation in enumerate(draft.mutations):
        new_support = set(mutation.support_keys) & expected_new_keys
        if not new_support:
            raise ValueError(
                "Every draft Slot mutation must use at least one NEW support key; "
                f"mutation_index={index}"
            )
        for key in new_support:
            used_by[key].add(index)

    routed_by_key: dict[str, set[int]] = {key: set() for key in expected_new_keys}
    referenced_mutations: set[int] = set()
    for row in rows:
        indices = set(row.mutation_indices)
        if row.disposition != "WORLD_MUTATION":
            continue
        if any(index >= len(draft.mutations) for index in indices):
            raise ValueError(
                "Evidence proposition references unknown mutation index; "
                f"support_key={row.support_key} indices={sorted(indices)}"
            )
        for index in indices:
            mutation_family = draft.mutations[index].primitive_family
            if row.primitive_family != mutation_family:
                raise ValueError(
                    "WORLD proposition primitive_family must match routed mutation; "
                    f"support_key={row.support_key} "
                    f"proposition_family={row.primitive_family} "
                    f"mutation_index={index} "
                    f"mutation_family={mutation_family}"
                )
        routed_by_key[row.support_key].update(indices)
        referenced_mutations.update(indices)

    for key in expected_new_keys:
        if routed_by_key[key] != used_by[key]:
            raise ValueError(
                "WORLD proposition routing union must exactly match mutations "
                "grounded by its NEW support key; "
                f"support_key={key} "
                f"ledger={sorted(routed_by_key[key])} "
                f"used_by={sorted(used_by[key])}"
            )

    expected_mutations = set(range(len(draft.mutations)))
    if referenced_mutations != expected_mutations:
        raise ValueError(
            "Every proposed mutation must be referenced by at least one "
            "WORLD_MUTATION proposition; "
            f"missing_mutations={sorted(expected_mutations - referenced_mutations)}"
        )


def decide_slot_delta_with_audit(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> SlotDecisionV01:
    previous_support_refs = {
        ref
        for slot in (previous.slots if previous is not None else ())
        for ref in slot.support_refs
    }
    hydrated = {
        str(row.get("unit_id") or "").strip()
        for row in previous_support_units
        if str(row.get("unit_id") or "").strip()
    }
    if hydrated != previous_support_refs:
        raise ValueError(
            "Slot Decide previous support hydration must exactly match current slot support"
        )

    new_refs = set(observation.audited_semantic_unit_refs)
    ref_by_key, prev_key_by_ref, new_key_by_ref = _support_aliases(
        previous_support_refs, new_refs
    )
    slot_id_by_key, slot_key_by_id = _slot_aliases(previous)

    previous_slots_payload = []
    if previous is not None:
        for slot in sorted(previous.slots, key=lambda row: row.slot_id):
            previous_slots_payload.append(
                {
                    "slot_key": slot_key_by_id[slot.slot_id],
                    "primitive_family": slot.primitive_family,
                    "slot_label": slot.slot_label,
                    "state_question": slot.state_question,
                    "value": slot.value,
                    "support_keys": [
                        prev_key_by_ref[ref] for ref in slot.support_refs
                    ],
                }
            )

    payload = {
        "contract": SLOT_DECIDER_CONTRACT,
        "event_identity": dict(event_identity),
        "previous_status": previous.status if previous is not None else None,
        "previous_slots": previous_slots_payload,
        "previous_support_units": _units_with_keys(
            previous_support_units, prev_key_by_ref
        ),
        "new_semantic_units": _units_with_keys(
            new_semantic_units, new_key_by_ref
        ),
        "allowed_support_keys": sorted(ref_by_key),
        "allowed_new_support_keys": sorted(new_key_by_ref.values()),
        "allowed_existing_slot_keys": sorted(slot_id_by_key),
    }
    obj, _meta, _validation_events = chat_json_schema(
        [
            {"role": "system", "content": _DECIDE_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Resolve semantic keys, account for every NEW support key in "
                    "evidence_projection, and return the complete SlotDelta draft.\n\n"
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                ),
            },
        ],
        SlotDeltaDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = SlotDeltaDraftV01.model_validate(obj)
    expected_new_keys = set(new_key_by_ref.values())
    draft = _prune_unreferenced_mutations(draft)
    draft = _normalize_mutation_support_by_projection(
        draft=draft,
        expected_new_keys=expected_new_keys,
    )
    _validate_evidence_projection(
        draft=draft,
        expected_new_keys=expected_new_keys,
    )

    if not draft.mutations:
        if previous is None:
            raise ValueError("First Event observation cannot produce an empty SlotDelta")
        return SlotDecisionV01(
            delta=None,
            evidence_projection=draft.evidence_projection,
        )

    def resolve_support(key: str) -> str:
        ref = ref_by_key.get(key)
        if ref is None:
            raise ValueError(f"Slot Decide proposed unknown support key: {key}")
        return ref

    mutations = []
    for idx, row in enumerate(draft.mutations):
        supports = tuple(sorted({resolve_support(k) for k in row.support_keys}))
        if not (set(supports) & new_refs):
            raise ValueError(
                "Every Slot mutation must use new-observation support; "
                f"label={row.slot_label!r}"
            )
        if row.target == "EXISTING":
            slot_id = slot_id_by_key.get(row.existing_slot_key or "")
            if slot_id is None:
                raise ValueError(
                    "Slot Decide proposed unknown existing slot key: "
                    f"{row.existing_slot_key}"
                )
            mode: SlotMutationMode = "CONTEST" if row.contest else "UPSERT"
        else:
            slot_id = _new_slot_id(
                event_id=observation.event_id,
                observation_key=observation.observation_key,
                ordinal=idx,
                state_question=row.state_question,
            )
            mode = "CREATE"
        mutations.append(
            SlotMutationV01(
                mode=mode,
                slot=CurrentSlotV01(
                    slot_id=slot_id,
                    primitive_family=row.primitive_family,
                    slot_label=row.slot_label,
                    state_question=row.state_question,
                    value=row.value,
                    support_refs=supports,
                ),
                rationale=row.rationale,
            )
        )

    delta = SlotDeltaV01(
        mutations=tuple(mutations),
        phase_change=draft.phase_change,
        rationale=draft.rationale,
    )
    _validate_slot_delta(
        previous=previous,
        observation=observation,
        delta=delta,
    )
    return SlotDecisionV01(
        delta=delta,
        evidence_projection=draft.evidence_projection,
    )


def decide_slot_delta(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> SlotDeltaV01 | None:
    return decide_slot_delta_with_audit(
        event_identity=event_identity,
        previous=previous,
        observation=observation,
        previous_support_units=previous_support_units,
        new_semantic_units=new_semantic_units,
        chat_fn=chat_fn,
    ).delta


def _validate_slot_delta(
    *,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    delta: SlotDeltaV01,
) -> None:
    previous_by_id = {
        row.slot_id: row for row in (previous.slots if previous is not None else ())
    }
    previous_support = {
        ref for row in previous_by_id.values() for ref in row.support_refs
    }
    new_refs = set(observation.audited_semantic_unit_refs)
    allowed_support = previous_support | new_refs

    if previous is None and any(row.mode != "CREATE" for row in delta.mutations):
        raise ValueError("First slot transition may contain only CREATE mutations")

    for mutation in delta.mutations:
        slot = mutation.slot
        support = set(slot.support_refs)
        if not support <= allowed_support:
            raise ValueError("SlotDelta contains unsupported semantic refs")
        if not (support & new_refs):
            raise ValueError("Every Slot mutation must use new-observation support")
        exists = slot.slot_id in previous_by_id
        if mutation.mode == "CREATE" and exists:
            raise ValueError("CREATE may not reuse an existing slot_id")
        if mutation.mode in {"UPSERT", "CONTEST"} and not exists:
            raise ValueError(f"{mutation.mode} requires an existing slot_id")
        if mutation.mode in {"UPSERT", "CONTEST"}:
            previous_slot = previous_by_id[slot.slot_id]
            if slot.primitive_family != previous_slot.primitive_family:
                raise ValueError(
                    "Existing slot primitive_family is immutable; "
                    f"expected={previous_slot.primitive_family!r} "
                    f"observed={slot.primitive_family!r}"
                )
            if slot.state_question != previous_slot.state_question:
                raise ValueError(
                    "Existing slot state_question is immutable; "
                    f"expected={previous_slot.state_question!r} "
                    f"observed={slot.state_question!r}"
                )
        if mutation.mode == "CONTEST":
            old_support = set(previous_by_id[slot.slot_id].support_refs)
            if not (support & old_support):
                raise ValueError("CONTEST must preserve support for the previous live side")
    if any(row.mode == "CONTEST" for row in delta.mutations):
        if delta.phase_change not in {None, "CONTESTED"}:
            raise ValueError("CONTEST phase_change must be CONTESTED or null")
    elif delta.phase_change == "CONTESTED":
        raise ValueError("Only CONTEST may enter CONTESTED phase")
def _next_phase(
    previous: SemanticSlotStateV01 | None,
    delta: SlotDeltaV01 | None,
) -> EventPhase:
    if delta is None:
        if previous is None:
            raise ValueError("Empty SlotDelta requires previous state")
        return previous.status
    if previous is None:
        return "EMERGING"
    if any(row.mode == "CONTEST" for row in delta.mutations):
        return "CONTESTED"
    if delta.phase_change is not None:
        return delta.phase_change
    if previous.status == "EMERGING":
        return "ACTIVE"
    if previous.status in {"ACTIVE", "RESOLVED"}:
        return previous.status
    return "CONTESTED"


def _bounded(text: str, max_chars: int = 2000) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    window = text[: max_chars + 1]
    cut = window.rfind(" ")
    if cut < max_chars // 2:
        cut = max_chars
    bounded = window[:cut].rstrip(" ,;:-")
    if bounded and bounded[-1] not in ".!?":
        bounded += "."
    return bounded[:max_chars]


def _materialize_event_state(
    db: Session,
    *,
    slot_state: SemanticSlotStateV01,
    supporting_source_ids,
) -> EventStateV02:
    slots = tuple(sorted(slot_state.slots, key=lambda row: row.slot_id))
    active_refs = tuple(sorted({ref for slot in slots for ref in slot.support_refs}))
    synopsis = _bounded(
        " ".join(f"{slot.slot_label}: {slot.value}" for slot in slots)
    )
    evidence_state = structural_evidence_state_v02(
        db,
        slot_state.event_id,
        active_semantic_unit_refs=active_refs,
        supporting_source_ids=supporting_source_ids,
    )
    return make_event_state_v02(
        event_id=slot_state.event_id,
        world_state=WorldStateV02(
            synopsis=synopsis,
            status=slot_state.status,
            effective_at=slot_state.effective_at,
            active_semantic_unit_refs=active_refs,
        ),
        evidence_state=evidence_state,
    )
def apply_slot_delta(
    db: Session,
    *,
    event_id: UUID,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    delta: SlotDeltaV01 | None,
    supporting_source_ids,
) -> SlotApplyResultV01:
    if observation.event_id != event_id:
        raise ValueError("Observation Event id does not match Slot Apply Event id")
    if previous is not None and previous.event_id != event_id:
        raise ValueError("Previous semantic slot state belongs to another Event")

    if delta is None:
        if previous is None:
            raise ValueError("First observation requires a material SlotDelta")
        next_slot_state = previous
    else:
        _validate_slot_delta(previous=previous, observation=observation, delta=delta)
        by_id = {
            row.slot_id: row for row in (previous.slots if previous is not None else ())
        }
        for mutation in delta.mutations:
            by_id[mutation.slot.slot_id] = mutation.slot
        slots = tuple(sorted(by_id.values(), key=lambda row: row.slot_id))
        if not slots:
            raise ValueError("Slot Apply may not materialize an empty slot state")
        next_slot_state = make_slot_state(
            event_id=event_id,
            slots=slots,
            status=_next_phase(previous, delta),
            effective_at=observation.world_time or observation.evidence_time,
        )

    event_state = _materialize_event_state(
        db,
        slot_state=next_slot_state,
        supporting_source_ids=supporting_source_ids,
    )
    return SlotApplyResultV01(
        previous_slot_state_digest=(
            previous.state_digest if previous is not None else None
        ),
        observation_key=observation.observation_key,
        slot_state=next_slot_state,
        event_state=event_state,
    )
