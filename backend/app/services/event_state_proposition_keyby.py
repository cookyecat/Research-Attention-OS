from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.cognitive.client import chat_json_schema
from app.services.event_observation import EventObservationV01
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    PrimitiveFamily,
    SemanticSlotStateV01,
    SlotDeltaV01,
    SlotMutationV01,
    _validate_slot_delta,
)


PROPOSITION_FLATMAP_CONTRACT = "event-world-proposition-flatmap-v0.7"
SEMANTIC_KEYBY_CONTRACT = "event-semantic-keyby-v0.6"
TWO_STAGE_DECIDER_CONTRACT = "event-slot-two-stage-decider-v0.9"

PlaneDisposition = Literal[
    "WORLD",
    "IDENTITY",
    "EVIDENCE",
    "PERIPHERAL_OR_REDUNDANT",
]
PropositionDisposition = Literal["WORLD_MUTATION", "NO_WORLD_VALUE_CHANGE"]
DraftTarget = Literal["CREATE", "EXISTING"]
ReferentScope = Literal["TARGET_INTRINSIC", "TARGET_RELATION"]


def _stable_digest(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    return " ".join(str(value).split())
class UnitPlaneRouteV01(BaseModel):
    support_key: str = Field(min_length=1)
    disposition: PlaneDisposition
    rationale: str | None = Field(default=None, max_length=2000)


class WorldPropositionDraftV01(BaseModel):
    statement: str = Field(min_length=1, max_length=6000)
    support_keys: tuple[str, ...] = Field(min_length=1)
    primitive_family: PrimitiveFamily
    referent_scope: ReferentScope
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def normalize(self):
        object.__setattr__(self, "statement", _normalize_text(self.statement))
        object.__setattr__(
            self,
            "support_keys",
            tuple(sorted({str(v).strip() for v in self.support_keys if str(v).strip()})),
        )
        if self.referent_scope == "TARGET_RELATION" and self.primitive_family != "RELATION":
            raise ValueError(
                "TARGET_RELATION proposition must use RELATION primitive_family"
            )
        if self.referent_scope == "TARGET_INTRINSIC" and self.primitive_family == "RELATION":
            raise ValueError(
                "RELATION proposition must use TARGET_RELATION referent_scope"
            )
        return self


class PropositionFlatMapDraftV01(BaseModel):
    contract: str = PROPOSITION_FLATMAP_CONTRACT
    unit_routes: tuple[UnitPlaneRouteV01, ...]
    world_propositions: tuple[WorldPropositionDraftV01, ...] = ()
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != PROPOSITION_FLATMAP_CONTRACT:
            raise ValueError(f"contract must be {PROPOSITION_FLATMAP_CONTRACT}")
        return self


class WorldPropositionV01(BaseModel):
    proposition_id: str = Field(min_length=16)
    statement: str = Field(min_length=1, max_length=6000)
    support_refs: tuple[str, ...] = Field(min_length=1)
    primitive_family: PrimitiveFamily
    referent_scope: ReferentScope
    rationale: str | None = Field(default=None, max_length=2000)


class PropositionFlatMapResultV01(BaseModel):
    contract: str = PROPOSITION_FLATMAP_CONTRACT
    unit_routes: tuple[UnitPlaneRouteV01, ...]
    world_propositions: tuple[WorldPropositionV01, ...]
class KeyByMutationDraftV01(BaseModel):
    target: DraftTarget
    existing_slot_key: str | None = None
    primitive_family: PrimitiveFamily
    slot_label: str = Field(min_length=1, max_length=200)
    state_question: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=6000)
    retain_previous_support_keys: tuple[str, ...] = ()
    contest: bool = False
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_target(self):
        if self.target == "EXISTING" and not self.existing_slot_key:
            raise ValueError("EXISTING mutation requires existing_slot_key")
        if self.target == "CREATE" and self.existing_slot_key is not None:
            raise ValueError("CREATE mutation may not set existing_slot_key")
        if self.target == "CREATE" and self.retain_previous_support_keys:
            raise ValueError("CREATE may not retain previous support keys")
        object.__setattr__(self, "state_question", _normalize_text(self.state_question))
        object.__setattr__(self, "value", _normalize_text(self.value))
        return self


class PropositionRouteV01(BaseModel):
    proposition_key: str = Field(min_length=1)
    disposition: PropositionDisposition
    mutation_indices: tuple[int, ...] = ()
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_shape(self):
        indices = tuple(sorted(set(self.mutation_indices)))
        object.__setattr__(self, "mutation_indices", indices)
        if self.disposition == "WORLD_MUTATION":
            if not indices:
                raise ValueError("WORLD_MUTATION proposition requires mutation_indices")
            if any(index < 0 for index in indices):
                raise ValueError("mutation_indices must be non-negative")
        elif indices:
            raise ValueError("NO_WORLD_VALUE_CHANGE may not reference mutations")
        return self


class SemanticKeyByDraftV01(BaseModel):
    contract: str = SEMANTIC_KEYBY_CONTRACT
    mutations: tuple[KeyByMutationDraftV01, ...] = ()
    proposition_routes: tuple[PropositionRouteV01, ...]
    phase_change: Literal["EMERGING", "ACTIVE", "CONTESTED", "RESOLVED"] | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != SEMANTIC_KEYBY_CONTRACT:
            raise ValueError(f"contract must be {SEMANTIC_KEYBY_CONTRACT}")
        return self


class TwoStageSlotDecisionV01(BaseModel):
    contract: str = TWO_STAGE_DECIDER_CONTRACT
    delta: SlotDeltaV01 | None
    flatmap: PropositionFlatMapResultV01
    keyby_draft: SemanticKeyByDraftV01
_FLATMAP_SYSTEM = """You are the RAOS Proposition FlatMap operator.

Your ONLY job is semantic normalization before keyed state resolution.

Input:
- coarse Event Identity,
- NEW audited semantic units Nxxx.

Output:
1. classify every N-key exactly once into WORLD / IDENTITY / EVIDENCE / PERIPHERAL_OR_REDUNDANT;
2. for WORLD units, emit zero-or-more normalized World propositions.

Return JSON:
{
  "contract": "event-world-proposition-flatmap-v0.7",
  "unit_routes": [
    {"support_key":"N001","disposition":"WORLD","rationale":"..."}
  ],
  "world_propositions": [
    {
      "statement":"one plane-pure World proposition",
      "support_keys":["N001"],
      "primitive_family":"STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER",
      "referent_scope":"TARGET_INTRINSIC | TARGET_RELATION",
      "rationale":"..."
    }
  ],
  "rationale":"..."
}

Rules:
- Every supplied N-key appears exactly once in unit_routes.
- WORLD means semantic content about what is currently true/proposed/claimed of the already-identified Event/entity.
- REFERENT ANCHOR TEST: every World proposition must be anchored on the Event referent itself OR on a material relation between the referent and something external. Do not promote facts that are merely about the source, author, visualization, host page, demo presentation, surrounding infrastructure, or a related component's own lifecycle.
- Every World proposition MUST declare referent_scope.
  * TARGET_INTRINSIC = a property/state/structure/process/form/disposition/quality of the Event referent itself.
  * TARGET_RELATION = a relation/context/integration/affordance involving the Event referent and something external.
- Hard semantic pairing: TARGET_RELATION must use primitive_family RELATION; RELATION must use TARGET_RELATION. All other primitive families use TARGET_INTRINSIC.
- Rewrite propositions into referent-normalized form before returning. Prefer "the target system is based on X" over "X was published by Y on platform Z"; prefer "the target system is integrated into application context Y" over copying Y's internal infrastructure details.
- If a unit is mostly about another entity, ask what it materially implies about the Event referent. If the answer is nothing beyond context/provenance/presentation, route it PERIPHERAL_OR_REDUNDANT or EVIDENCE rather than WORLD.
- Every World proposition must have exactly one primitive_family:
  STATE=current condition/lifecycle/availability;
  STRUCTURE=composition/parts/organization/topology;
  PROCESS=mechanism/dynamics/transformation/procedure;
  FORM=manifestation/representation/interface/output-action form;
  DISPOSITION=capability/function/tendency/realizable behavior;
  QUALITY=performance/quantity/reliability/correctness/cost/rate/magnitude;
  RELATION=role/context/affordance/suitability/relation to other entities;
  OTHER=material World proposition that cannot yet be typed coherently.
- Primitive family is an upper-level type, not a domain topic. Split across families; merge same-family facets when they answer one primitive coordinate.
- IDENTITY defines what referent/episode this is.
- EVIDENCE concerns provenance, corroboration, confidence, validation maturity, support quality, or source completeness.
- PERIPHERAL_OR_REDUNDANT is page/source reaction, hype, presentation mechanics, or content not material to this Event.
- A WORLD N-key must support at least one proposition.
- Non-WORLD N-keys must support no World proposition.
- One N-key MAY support multiple propositions.
- Multiple N-keys MAY support one proposition.
- FlatMap is NOT a clause atomizer. Normalize to ONE proposition cluster per primitive semantic family within this observation, not one proposition per sentence, metric, artifact, or implementation detail.
- MERGE same-family facets before returning. Examples:
  * speed + latency + throughput + call rate + cost/efficiency -> ONE Operational Performance proposition;
  * model architecture + decoder choice + KV-cache reuse + token-scoring procedure -> ONE Mechanism/Dynamics proposition;
  * release state + access/availability channel + closely related release availability plan -> ONE Lifecycle/Availability proposition when they describe the same episode-level availability state;
  * Mario + DOOM + Tetris demonstrations -> ONE Demonstrated Capability proposition;
  * multiple proposed roles/use cases -> ONE Affordance/Application proposition.
- Same-family facets may vary numerically or independently; that does NOT make them separate primitive coordinates. Primitive family cohesion takes precedence over scalar independence within the family.
- SPLIT only across different primitive families. Example: Form + Reliability must split; Capability + Performance must split; Mechanism + Performance must split.
- DEMONSTRATED ACTION RULE: when evidence establishes that the system actually performed or completed a task/action/behavior, emit a DISPOSITION proposition for the demonstrated capability even if the wording is an event/action verb.
- DISPOSITION takes precedence over PROCESS for the mere fact that the system DID something. PROCESS is reserved for how an operation unfolds internally: mechanism, transformation, procedure, recurring workflow, or causal/dynamic steps.
- "What the system did" and "how well/fast/cheaply it did it" are different primitive families. Example: "played Tetris, scored 9200, 300ms/move" -> DISPOSITION: demonstrated Tetris/game-playing capability + QUALITY: run/performance metrics.
- Example: "the system rebuilt a complex subsystem in one hour" -> DISPOSITION: demonstrated ability to rebuild that subsystem + QUALITY: completion time around one hour. Do NOT classify the achievement itself as PROCESS unless the source also describes the procedure/mechanism used.
- PRESENTATION METADATA RULE: author excitement, who made a visualization, which assistant generated an explanatory graphic, page/thread mechanics, video playback detail, or the fact that something was "shown in a demo" is not a World coordinate.
- INCIDENTAL HARDWARE RULE: "the demo is shown on an M4 MacBook" is normally peripheral presentation/deployment context. Emit a World proposition only when the source actually establishes a material compatibility/deployment/performance fact of the target system and that fact matters to the Event.
- NO PROPERTY INHERITANCE: properties of a component, base model, host platform, tool, application, or external system do NOT transfer to the target merely because the target uses/is based on/is integrated with it. Do not infer target speed, release status, price, compatibility, reliability, or availability from another entity's property unless the source explicitly predicates that property of the target.
- COMPONENT LINEAGE RULE: if the target is based on a component/model/artifact, emit only the target-anchored STRUCTURE proposition (e.g. "the target is based on Qwen2.5-RLCD"). Publisher identity, hosting platform, and the component's own release/open-source/performance state are provenance/background unless the source explicitly states the corresponding target property.
- TARGET LIFECYCLE RULE: STATE propositions describe lifecycle/availability of the Event referent itself. Strip identity type, creator biography, R&D duration, announcement prestige, provenance, and hype from the lifecycle proposition. Do not create a STATE proposition for a related component merely because that component was released/open-sourced.
- EXTERNAL APPLICATION RULE: surrounding application infrastructure is not target STRUCTURE. If material, normalize it to a RELATION proposition anchored on the target (e.g. "the target is integrated into an automated-trading workflow using Monad/Kuru"). Details such as another chain's block interval or another platform's data structure do not become target STRUCTURE by themselves.
- LOCAL ENTAILMENT RULE: a support unit used for a TARGET_INTRINSIC proposition must itself explicitly predicate that property/process of the Event referent. Do not borrow ownership from the source title or nearby context when the unit only describes an "agent", "bot", "workflow", component, or external system.
- COMPOSITE-SUBJECT RULE: a claim whose subject is a combination such as "browser-use + Jev", "Jev + chain X", or "the trading system using Jev" is relational/contextual, not an intrinsic PROCESS/QUALITY of Jev. Normalize material content to TARGET_RELATION / RELATION.
- COMPOSITE WORKFLOW RULE: a PROCESS proposition describes the target's own internal mechanism/dynamics. A workflow of a surrounding browser agent, trading bot, or host system is normally a RELATION/application-context proposition unless the Event referent itself is that composite workflow.
- Demonstration medium/context such as "shown in a live demo" is normally support/context for a capability proposition, not a separate World proposition, unless the Event itself materially concerns the demonstration medium.
- Reproduction/corroboration/source independence is EVIDENCE, not a World proposition, unless the reproduction contains a materially different World result. If it repeats the same numeric World value, the repeated value may be emitted only if needed for KeyBy to recognize NO_WORLD_VALUE_CHANGE; never emit a separate Reproducibility World proposition.
- CONFLICT DOES NOT ERASE WORLD CONTENT. If a new source reports a materially different measurement or incompatible World assertion, the conflicting value itself is WORLD and must be emitted as a proposition. The facts that it disputes earlier evidence or that the conflict is unresolved are Evidence/epistemic qualifiers. KeyBy will decide CONTEST on the existing coordinate.
- Example: existing 300ms result + new comparable 1.5s result -> emit the 1.5s performance proposition as WORLD; do not classify the whole unit as EVIDENCE merely because the measurements conflict.
- Absence of demonstration, absence of benchmark, or lack of independent support is EVIDENCE/open-world metadata, not a World proposition.
- Identity-defining assertions or conflicts about what the Event referent fundamentally is (e.g. AI model vs human-operated system when Event Identity already fixes the referent type) are IDENTITY, not a mutable World proposition.
- Generality means domain-independence, not semantic breadth.
- Do not emit wrapper propositions such as "has benefits", "has features", "is impressive". Decompose underlying World meanings, then MERGE facets that belong to the same primitive family.
- Example: "typed judgments rather than strings and structurally incapable of hallucination" -> TWO propositions: output form; reliability/correctness.
- Example: "benefits are lower latency and 100% valid JSON" -> TWO propositions: operational performance; output validity/correctness.
- Do not decide existing/new semantic keys here.
"""


_KEYBY_SYSTEM = """You are the RAOS semantic KeyBy operator.

You receive:
- Event Identity,
- previous persistent CurrentSlots,
- normalized plane-pure World propositions Pxxx.

Your ONLY job is to project each proposition onto the current semantic key-space.

Return JSON:
{
  "contract":"event-semantic-keyby-v0.6",
  "mutations":[
    {
      "target":"EXISTING | CREATE",
      "existing_slot_key":"S001 or null",
      "primitive_family":"STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER",
      "slot_label":"short label",
      "state_question":"one primitive-bounded universal current-state question",
      "value":"complete current sufficient answer after update",
      "retain_previous_support_keys":["R001"],
      "contest":false,
      "rationale":"..."
    }
  ],
  "proposition_routes":[
    {
      "proposition_key":"P001",
      "disposition":"WORLD_MUTATION | NO_WORLD_VALUE_CHANGE",
      "mutation_indices":[0],
      "rationale":"..."
    }
  ],
  "phase_change":"EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale":"..."
}

Rules:
- Account for every P-key exactly once.
- primitive_family is a hard semantic type. A proposition may route only to a mutation with the SAME primitive_family.
- referent_scope and primitive_family are FROZEN upstream by FlatMap. Do NOT reclassify them based on surface words in the proposition.
- TARGET_RELATION propositions already use RELATION primitive_family and therefore may only route to RELATION slots. TARGET_INTRINSIC propositions may not route to RELATION slots.
- CONTEXTUAL-PROPERTY RULE: if a proposition says a combination/integration/context is fast, cheap, reliable, etc. but FlatMap normalized it as TARGET_RELATION / RELATION, keep it RELATION. Words like speed/cost/latency do NOT authorize changing the family to QUALITY.
- If a RELATION proposition directly changes no existing RELATION slot, CREATE a new RELATION coordinate rather than forcing it into an intrinsic QUALITY/PROCESS/STRUCTURE slot.
- For EXISTING, copy the previous slot primitive_family exactly; family is immutable.
- For CREATE, use the proposition's primitive_family. Do not invent a broader/different family merely to reuse a nearby slot.
- Apply the DIRECT ANSWER TEST. A proposition may mutate an existing slot only when it directly changes the answer to that exact state_question.
- Causal relevance, topical relation, or being in the same source does not count.
- If a proposition directly changes no existing slot but defines a new independently variable material World dimension, CREATE.
- If the current sufficient World value is semantically unchanged, use NO_WORLD_VALUE_CHANGE.
- Generality is domain-independence, NOT semantic breadth. Avoid umbrella questions.
- CREATE state_question must describe a reusable primitive coordinate, not this particular Event instance. Use generic referents such as "this system", "this model", or "this entity".
- CREATE state_question must NOT contain Event-specific proper nouns, named products, named games/tasks, named benchmarks, source names, concrete metric values, or current example instances. Those belong in value, not in key semantics.
- Example: use "What capabilities or behaviors has this system demonstrated?" rather than "What real-time game-playing capability does Jev demonstrate?".
- Example: use "What are this system's operational performance characteristics?" rather than "What is Jev's latency?".
- Primitive families should remain orthogonal: mechanism != output form != reliability; mechanism != performance; capability != affordance.
- Same-primitive facets/examples should share one key.
- Do not create wrapper keys such as Benefits / Features / Strengths.
- Existing state_question is immutable: copy it EXACTLY for EXISTING.
- For EXISTING, retain only previous support aliases needed for the complete current value. New support is derived from routed propositions.
- One proposition may update multiple existing slots only if it truly directly answers multiple orthogonal questions.
- Multiple propositions may route to one mutation when they belong to the same primitive coordinate.
- contest=true only for unresolved incompatible World assertions on the same coordinate.
- RESOLVED refers to the Event episode, not one corrected slot.
"""
def _support_aliases(new_refs: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    by_ref = {ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), 1)}
    by_key = {key: ref for ref, key in by_ref.items()}
    return by_ref, by_key


def _slot_aliases(
    previous: SemanticSlotStateV01 | None,
) -> tuple[dict[str, str], dict[str, str]]:
    if previous is None:
        return {}, {}
    ordered = sorted(previous.slots, key=lambda row: row.slot_id)
    key_by_id = {slot.slot_id: f"S{i:03d}" for i, slot in enumerate(ordered, 1)}
    id_by_key = {key: slot_id for slot_id, key in key_by_id.items()}
    return key_by_id, id_by_key


def _previous_support_aliases(
    previous: SemanticSlotStateV01 | None,
) -> tuple[dict[str, str], dict[str, str]]:
    refs = sorted(
        {
            ref
            for slot in (previous.slots if previous is not None else ())
            for ref in slot.support_refs
        }
    )
    key_by_ref = {ref: f"R{i:03d}" for i, ref in enumerate(refs, 1)}
    ref_by_key = {key: ref for ref, key in key_by_ref.items()}
    return key_by_ref, ref_by_key


def _units_with_keys(rows: list[dict], key_by_ref: dict[str, str]) -> list[dict]:
    result = []
    for row in rows:
        ref = str(row.get("unit_id") or "").strip()
        key = key_by_ref.get(ref)
        if key is None:
            raise ValueError(f"Semantic unit outside new support map: {ref}")
        item = {k: v for k, v in row.items() if k != "unit_id"}
        item["support_key"] = key
        result.append(item)
    return result


def _new_proposition_id(
    *,
    observation: EventObservationV01,
    ordinal: int,
    statement: str,
    support_refs: tuple[str, ...],
) -> str:
    return _stable_digest(
        {
            "event_id": str(observation.event_id),
            "observation_key": observation.observation_key,
            "ordinal": ordinal,
            "statement": _normalize_text(statement),
            "support_refs": list(sorted(support_refs)),
        }
    )


def _new_slot_id(
    *,
    observation: EventObservationV01,
    ordinal: int,
    state_question: str,
) -> str:
    return _stable_digest(
        {
            "event_id": str(observation.event_id),
            "observation_key": observation.observation_key,
            "ordinal": ordinal,
            "state_question": _normalize_text(state_question),
        }
    )
def _normalize_flatmap_draft(
    draft: PropositionFlatMapDraftV01,
) -> PropositionFlatMapDraftV01:
    """Make World proposition support authoritative for WORLD unit routing.

    If the model emits a World proposition supported by Nxxx, that support key
    semantically participates in the World plane regardless of an inconsistent
    duplicate unit_routes label. We normalize only this contradiction.
    A unit labeled WORLD but supporting no proposition is still rejected later
    as a basis-completeness failure.
    """
    world_support_keys = {
        key
        for proposition in draft.world_propositions
        for key in proposition.support_keys
    }
    routes = tuple(
        (
            route
            if route.support_key not in world_support_keys
            or route.disposition == "WORLD"
            else route.model_copy(update={"disposition": "WORLD"})
        )
        for route in draft.unit_routes
    )
    return draft.model_copy(update={"unit_routes": routes})


def _validate_flatmap_draft(
    *,
    draft: PropositionFlatMapDraftV01,
    expected_new_keys: set[str],
) -> None:
    route_keys = [row.support_key for row in draft.unit_routes]
    if len(route_keys) != len(set(route_keys)):
        raise ValueError("FlatMap unit_routes may contain each N-key exactly once")
    if set(route_keys) != expected_new_keys:
        raise ValueError(
            "FlatMap unit_routes must exactly cover all N-keys; "
            f"missing={sorted(expected_new_keys-set(route_keys))} "
            f"unknown={sorted(set(route_keys)-expected_new_keys)}"
        )
    route_by_key = {row.support_key: row for row in draft.unit_routes}
    used_by: dict[str, int] = {key: 0 for key in expected_new_keys}
    for proposition in draft.world_propositions:
        support = set(proposition.support_keys)
        if not support <= expected_new_keys:
            raise ValueError("World proposition references unknown N-key")
        for key in support:
            if route_by_key[key].disposition != "WORLD":
                raise ValueError(
                    "Non-WORLD N-key may not support World proposition; "
                    f"key={key} disposition={route_by_key[key].disposition}"
                )
            used_by[key] += 1
    for key, route in route_by_key.items():
        if route.disposition == "WORLD" and used_by[key] == 0:
            raise ValueError(f"WORLD N-key must support >=1 proposition: {key}")
        if route.disposition != "WORLD" and used_by[key] != 0:
            raise ValueError(f"Non-WORLD N-key supports World proposition: {key}")


def proposition_flatmap(
    *,
    event_identity: dict,
    observation: EventObservationV01,
    new_semantic_units: list[dict],
    chat_fn,
) -> PropositionFlatMapResultV01:
    new_refs = set(observation.audited_semantic_unit_refs)
    key_by_ref, ref_by_key = _support_aliases(new_refs)
    payload = {
        "contract": PROPOSITION_FLATMAP_CONTRACT,
        "event_identity": dict(event_identity),
        "new_semantic_units": _units_with_keys(new_semantic_units, key_by_ref),
        "allowed_new_support_keys": sorted(ref_by_key),
    }
    obj, _meta, _validation = chat_json_schema(
        [
            {"role": "system", "content": _FLATMAP_SYSTEM},
            {
                "role": "user",
                "content": "FlatMap the new audited evidence into plane-pure World propositions.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
            },
        ],
        PropositionFlatMapDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = PropositionFlatMapDraftV01.model_validate(obj)
    draft = _normalize_flatmap_draft(draft)
    _validate_flatmap_draft(draft=draft, expected_new_keys=set(ref_by_key))
    propositions = []
    for ordinal, row in enumerate(draft.world_propositions):
        refs = tuple(sorted({ref_by_key[key] for key in row.support_keys}))
        propositions.append(
            WorldPropositionV01(
                proposition_id=_new_proposition_id(
                    observation=observation,
                    ordinal=ordinal,
                    statement=row.statement,
                    support_refs=refs,
                ),
                statement=row.statement,
                support_refs=refs,
                primitive_family=row.primitive_family,
                referent_scope=row.referent_scope,
                rationale=row.rationale,
            )
        )
    return PropositionFlatMapResultV01(
        unit_routes=draft.unit_routes,
        world_propositions=tuple(propositions),
    )
def _normalize_keyby_draft(
    draft: SemanticKeyByDraftV01,
) -> SemanticKeyByDraftV01:
    """Make proposition routing the sole authority for mutation existence.

    LLMs occasionally emit an extra mutation but route no proposition to it.
    Such a mutation has no semantic grounding and is deterministically pruned.
    Referenced mutation indices are compacted and proposition routes remapped.
    """
    referenced = sorted(
        {
            index
            for route in draft.proposition_routes
            if route.disposition == "WORLD_MUTATION"
            for index in route.mutation_indices
        }
    )
    if any(index < 0 or index >= len(draft.mutations) for index in referenced):
        raise ValueError("KeyBy proposition route references unknown mutation")
    if referenced == list(range(len(draft.mutations))):
        return draft

    index_map = {old: new for new, old in enumerate(referenced)}
    mutations = tuple(draft.mutations[index] for index in referenced)
    routes = []
    for route in draft.proposition_routes:
        if route.disposition != "WORLD_MUTATION":
            routes.append(route)
            continue
        routes.append(
            route.model_copy(
                update={
                    "mutation_indices": tuple(
                        index_map[index] for index in route.mutation_indices
                    )
                }
            )
        )
    return draft.model_copy(
        update={
            "mutations": mutations,
            "proposition_routes": tuple(routes),
        }
    )


def _validate_keyby_draft(
    *,
    draft: SemanticKeyByDraftV01,
    expected_prop_keys: set[str],
    proposition_family_by_key: dict[str, PrimitiveFamily],
) -> None:
    keys = [row.proposition_key for row in draft.proposition_routes]
    if len(keys) != len(set(keys)):
        raise ValueError("KeyBy proposition_routes may contain each P-key exactly once")
    if set(keys) != expected_prop_keys:
        raise ValueError(
            "KeyBy proposition_routes must exactly cover all P-keys; "
            f"missing={sorted(expected_prop_keys-set(keys))} "
            f"unknown={sorted(set(keys)-expected_prop_keys)}"
        )
    referenced = set()
    for route in draft.proposition_routes:
        indices = set(route.mutation_indices)
        if route.disposition == "WORLD_MUTATION":
            if any(index >= len(draft.mutations) for index in indices):
                raise ValueError("KeyBy proposition route references unknown mutation")
            proposition_family = proposition_family_by_key[route.proposition_key]
            for index in indices:
                mutation_family = draft.mutations[index].primitive_family
                if mutation_family != proposition_family:
                    raise ValueError(
                        "KeyBy primitive_family mismatch; "
                        f"proposition_key={route.proposition_key} "
                        f"proposition_family={proposition_family} "
                        f"mutation_index={index} "
                        f"mutation_family={mutation_family}"
                    )
            referenced.update(indices)
    if referenced != set(range(len(draft.mutations))):
        raise ValueError(
            "Every KeyBy mutation must be referenced by propositions; "
            f"missing={sorted(set(range(len(draft.mutations)))-referenced)}"
        )


def semantic_keyby(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    flatmap: PropositionFlatMapResultV01,
    chat_fn,
) -> tuple[SlotDeltaV01 | None, SemanticKeyByDraftV01]:
    propositions = flatmap.world_propositions
    if not propositions:
        empty = SemanticKeyByDraftV01(
            mutations=(),
            proposition_routes=(),
            phase_change=None,
            rationale="No World propositions from FlatMap.",
        )
        if previous is None:
            raise ValueError("First Event observation cannot have zero World propositions")
        return None, empty

    slot_key_by_id, slot_id_by_key = _slot_aliases(previous)
    prev_key_by_ref, prev_ref_by_key = _previous_support_aliases(previous)

    previous_slots_payload = []
    support_keys_by_slot_key: dict[str, set[str]] = {}
    if previous is not None:
        for slot in sorted(previous.slots, key=lambda row: row.slot_id):
            slot_key = slot_key_by_id[slot.slot_id]
            support_keys = [prev_key_by_ref[ref] for ref in slot.support_refs]
            support_keys_by_slot_key[slot_key] = set(support_keys)
            previous_slots_payload.append(
                {
                    "slot_key": slot_key,
                    "primitive_family": slot.primitive_family,
                    "slot_label": slot.slot_label,
                    "state_question": slot.state_question,
                    "value": slot.value,
                    "previous_support_keys": support_keys,
                }
            )

    prop_key_by_id = {
        row.proposition_id: f"P{i:03d}"
        for i, row in enumerate(propositions, 1)
    }
    prop_by_key = {
        prop_key_by_id[row.proposition_id]: row
        for row in propositions
    }
    payload = {
        "contract": SEMANTIC_KEYBY_CONTRACT,
        "event_identity": dict(event_identity),
        "previous_status": previous.status if previous is not None else None,
        "previous_slots": previous_slots_payload,
        "world_propositions": [
            {
                "proposition_key": prop_key_by_id[row.proposition_id],
                "statement": row.statement,
                "primitive_family": row.primitive_family,
                "referent_scope": row.referent_scope,
            }
            for row in propositions
        ],
        "allowed_existing_slot_keys": sorted(slot_id_by_key),
        "allowed_previous_support_keys": sorted(prev_ref_by_key),
    }
    obj, _meta, _validation = chat_json_schema(
        [
            {"role": "system", "content": _KEYBY_SYSTEM},
            {
                "role": "user",
                "content": "Key the normalized World propositions into the current semantic state basis.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
            },
        ],
        SemanticKeyByDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = SemanticKeyByDraftV01.model_validate(obj)
    draft = _normalize_keyby_draft(draft)
    _validate_keyby_draft(
        draft=draft,
        expected_prop_keys=set(prop_by_key),
        proposition_family_by_key={
            key: proposition.primitive_family
            for key, proposition in prop_by_key.items()
        },
    )
    prop_routes = {row.proposition_key: row for row in draft.proposition_routes}
    new_support_by_mutation: dict[int, set[str]] = {
        index: set() for index in range(len(draft.mutations))
    }
    for prop_key, route in prop_routes.items():
        if route.disposition != "WORLD_MUTATION":
            continue
        proposition = prop_by_key[prop_key]
        for index in route.mutation_indices:
            new_support_by_mutation[index].update(proposition.support_refs)

    mutations = []
    for index, row in enumerate(draft.mutations):
        new_refs = new_support_by_mutation[index]
        if not new_refs:
            raise ValueError("Every KeyBy mutation requires routed new proposition support")

        if row.target == "EXISTING":
            slot_id = slot_id_by_key.get(row.existing_slot_key or "")
            if slot_id is None:
                raise ValueError(
                    f"KeyBy proposed unknown existing slot key: {row.existing_slot_key}"
                )
            previous_slot = next(
                slot for slot in previous.slots if slot.slot_id == slot_id
            )
            if row.primitive_family != previous_slot.primitive_family:
                raise ValueError(
                    "Existing slot primitive_family is immutable; "
                    f"expected={previous_slot.primitive_family!r} "
                    f"observed={row.primitive_family!r}"
                )
            if row.state_question != previous_slot.state_question:
                raise ValueError(
                    "Existing slot state_question is immutable; "
                    f"expected={previous_slot.state_question!r} "
                    f"observed={row.state_question!r}"
                )
            allowed_old = support_keys_by_slot_key[row.existing_slot_key or ""]
            selected_old = set(row.retain_previous_support_keys)
            if not selected_old <= allowed_old:
                raise ValueError(
                    "KeyBy selected previous support outside target existing slot"
                )
            # CONTEST semantically keeps both live sides. Preserve the entire
            # previous live side deterministically rather than relying on the
            # model to remember which old support aliases must be retained.
            if row.contest:
                old_refs = set(previous_slot.support_refs)
                mode = "CONTEST"
            else:
                old_refs = {prev_ref_by_key[key] for key in selected_old}
                mode = "UPSERT"
        else:
            if row.retain_previous_support_keys:
                raise ValueError("CREATE may not retain previous support")
            slot_id = _new_slot_id(
                observation=observation,
                ordinal=index,
                state_question=row.state_question,
            )
            old_refs = set()
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
                    support_refs=tuple(sorted(old_refs | new_refs)),
                ),
                rationale=row.rationale,
            )
        )

    if not mutations:
        if previous is None:
            raise ValueError("First Event observation cannot produce empty SlotDelta")
        return None, draft

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
    return delta, draft


def decide_slot_delta_two_stage(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> TwoStageSlotDecisionV01:
    # previous_support_units is intentionally accepted for call-site parity and
    # replay/debug hydration, but KeyBy uses the already-materialized slot values
    # rather than asking the LLM to reconstruct them from evidence again.
    del previous_support_units
    flatmap = proposition_flatmap(
        event_identity=event_identity,
        observation=observation,
        new_semantic_units=new_semantic_units,
        chat_fn=chat_fn,
    )
    delta, keyby_draft = semantic_keyby(
        event_identity=event_identity,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        chat_fn=chat_fn,
    )
    return TwoStageSlotDecisionV01(
        delta=delta,
        flatmap=flatmap,
        keyby_draft=keyby_draft,
    )
