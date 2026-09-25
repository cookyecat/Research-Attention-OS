"""Phase17.3-KS-E address-locked semantic synthesis research path.

Semantic address is decided upstream by pairwise Direct-Answer adjudication.
This module removes address choice from the synthesis model's output schema.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.cognitive.client import chat_json_schema
from app.services.event_observation import EventObservationV01
from app.services.event_state_proposition_keyby import (
    KeyByAddressPolicyV01,
    KeyByMutationDraftV01,
    PropositionFlatMapResultV01,
    PropositionRouteV01,
    SemanticKeyByDraftV01,
    _address_policy_aliases,
    _address_policy_from_pairwise_plan,
    _new_slot_id,
    _normalize_keyby_draft,
    _previous_support_aliases,
    _slot_aliases,
    _validate_address_policy,
    _validate_keyby_draft,
)
from app.services.event_state_slot_delta import (
    CurrentSlotV01,
    SemanticSlotStateV01,
    SlotDeltaV01,
    SlotMutationV01,
    _validate_slot_delta,
)
from app.services.semantic_coordinate.adjudication import (
    CandidateAdjudicationPlan,
    build_candidate_adjudication_plan,
)
from app.services.semantic_coordinate.direct_answer import (
    PairwiseAuthorizationPlanV01,
    build_pairwise_authorization_plan,
    build_pairwise_authorization_plan_parallel,
    judge_direct_answer_parallel_consensus,
)

PairwiseTransport = Literal["SERIAL", "PARALLEL"]
class LockedExistingUpdateV01(BaseModel):
    slot_key: str = Field(min_length=1)
    proposition_keys: tuple[str, ...] = Field(min_length=1)
    value: str = Field(min_length=1, max_length=6000)
    retain_previous_support_keys: tuple[str, ...] = ()
    contest: bool = False
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def normalize_keys(self):
        object.__setattr__(
            self,
            "proposition_keys",
            tuple(sorted(set(self.proposition_keys))),
        )
        object.__setattr__(
            self,
            "retain_previous_support_keys",
            tuple(sorted(set(self.retain_previous_support_keys))),
        )
        return self


class LockedCreateGroupV01(BaseModel):
    proposition_keys: tuple[str, ...] = Field(min_length=1)
    primitive_family: str
    slot_label: str = Field(min_length=1, max_length=200)
    state_question: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=6000)
    rationale: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def normalize_props(self):
        object.__setattr__(
            self,
            "proposition_keys",
            tuple(sorted(set(self.proposition_keys))),
        )
        return self


class AddressLockedSynthesisDraftV01(BaseModel):
    existing_updates: tuple[LockedExistingUpdateV01, ...] = ()
    create_groups: tuple[LockedCreateGroupV01, ...] = ()
    no_change_proposition_keys: tuple[str, ...] = ()
    phase_change: Literal[
        "EMERGING",
        "ACTIVE",
        "CONTESTED",
        "RESOLVED",
    ] | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def normalize_no_change(self):
        object.__setattr__(
            self,
            "no_change_proposition_keys",
            tuple(sorted(set(self.no_change_proposition_keys))),
        )
        return self
class CreateGroupPairCheckV01(BaseModel):
    proposition_key: str
    group_key: str
    member: bool
    decision: Literal["DIRECT", "NOT_DIRECT", "UNCERTAIN"]
    rationale: str


class CreateGroupValidationV01(BaseModel):
    checks: tuple[CreateGroupPairCheckV01, ...] = ()
    membership_failures: tuple[str, ...] = ()
    cross_overlap_findings: tuple[str, ...] = ()
    uncertain_findings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not (
            self.membership_failures
            or self.cross_overlap_findings
            or self.uncertain_findings
        )


class CreateGroupSemanticValidationError(ValueError):
    def __init__(self, result: CreateGroupValidationV01):
        self.result = result
        super().__init__(
            "CREATE-group semantic validation failed; "
            f"membership={list(result.membership_failures)} "
            f"overlap={list(result.cross_overlap_findings)} "
            f"uncertain={list(result.uncertain_findings)}"
        )


class AddressLockedKeyByResultV01(BaseModel):
    delta: SlotDeltaV01 | None
    draft: SemanticKeyByDraftV01
    locked_draft: AddressLockedSynthesisDraftV01
    candidate_plan: CandidateAdjudicationPlan
    pairwise_plan: PairwiseAuthorizationPlanV01
    address_policy: KeyByAddressPolicyV01
    pairwise_transport: PairwiseTransport
    create_group_validation: CreateGroupValidationV01 | None = None


_ADDRESS_LOCKED_SYSTEM = """You are the RAOS address-locked semantic synthesis operator.

Semantic address has already been decided upstream. You MUST NOT choose or
change old-vs-new semantic address.

Input contains:
- Event Identity;
- normalized World propositions Pxxx;
- authorized_existing_groups: fixed existing slots, each with the ONLY
  propositions allowed to update it;
- create_eligible_proposition_keys: propositions proven not to directly answer
  any existing same-family coordinate.

Return JSON:
{
  "existing_updates": [
    {
      "slot_key": "S001",
      "proposition_keys": ["P001"],
      "value": "complete sufficient current value after update",
      "retain_previous_support_keys": ["R001"],
      "contest": false,
      "rationale": "..."
    }
  ],
  "create_groups": [
    {
      "proposition_keys": ["P002"],
      "primitive_family": "STATE | STRUCTURE | PROCESS | FORM | DISPOSITION | QUALITY | RELATION | OTHER",
      "slot_label": "short generic label",
      "state_question": "generic reusable current-state question",
      "value": "current sufficient value",
      "rationale": "..."
    }
  ],
  "no_change_proposition_keys": ["P003"],
  "phase_change": "EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale": "..."
}

Rules:
- Existing address is immutable. existing_updates.slot_key MUST be one of the
  supplied authorized_existing_groups.
- A proposition may appear in an existing update only when that exact
  proposition is authorized for that slot.
- For an authorized existing slot, synthesize the complete new current value
  from previous value + materially changing authorized propositions.
- If a REUSE-authorized proposition directly answers an existing coordinate but
  adds no semantic change to its already-sufficient current value, place it in
  no_change_proposition_keys.
- A proposition that changes at least one authorized existing slot must not also
  be placed in no_change_proposition_keys.
- CREATE-eligible propositions MUST appear in one-or-more create_groups and
  MUST NOT appear in existing_updates or no_change_proposition_keys.
- One proposition MAY appear in multiple CREATE groups only when it directly
  answers multiple orthogonal new state_questions, symmetric with the existing
  rule that one proposition may update multiple orthogonal existing slots.
- Group multiple CREATE-eligible propositions only when they define one
  primitive-bounded reusable current-state coordinate.
- Avoid redundant/overlapping CREATE groups. A later machine-checked
  Direct-Answer validation will reject missing memberships or cross-overlap.
- Every CREATE group contains propositions of exactly one frozen
  primitive_family and must use that family.
- CREATE state_question must be generic/domain-independent and must not contain
  Event-specific proper nouns, named tasks/products, source names, or concrete
  current values.
- Existing state_question/slot_label/family are NOT output fields because they
  are copied deterministically from CurrentState.
- retain_previous_support_keys may contain only aliases belonging to that fixed
  existing slot.
- contest=true only for unresolved incompatible assertions on the same existing
  coordinate.
- Account for every P-key at the route level: either it contributes to
  one-or-more authorized existing updates, belongs to one-or-more orthogonal
  CREATE groups, or is NO_CHANGE.
- RESOLVED refers to the Event episode, not one corrected slot.
"""
def _prop_key_maps(flatmap: PropositionFlatMapResultV01):
    propositions = flatmap.world_propositions
    key_by_id = {
        row.proposition_id: f"P{i:03d}"
        for i, row in enumerate(propositions, 1)
    }
    by_key = {
        key_by_id[row.proposition_id]: row
        for row in propositions
    }
    return key_by_id, by_key


def _slot_payload(previous: SemanticSlotStateV01 | None):
    slot_key_by_id, slot_id_by_key = _slot_aliases(previous)
    prev_key_by_ref, prev_ref_by_key = _previous_support_aliases(previous)
    payload_by_key = {}
    support_keys_by_slot_key = {}
    if previous is not None:
        for slot in sorted(previous.slots, key=lambda row: row.slot_id):
            key = slot_key_by_id[slot.slot_id]
            support_keys = tuple(
                prev_key_by_ref[ref]
                for ref in slot.support_refs
            )
            support_keys_by_slot_key[key] = set(support_keys)
            payload_by_key[key] = {
                "slot_key": key,
                "primitive_family": slot.primitive_family,
                "slot_label": slot.slot_label,
                "state_question": slot.state_question,
                "value": slot.value,
                "previous_support_keys": list(support_keys),
            }
    return (
        slot_key_by_id,
        slot_id_by_key,
        prev_ref_by_key,
        payload_by_key,
        support_keys_by_slot_key,
    )
def _validate_locked_draft(
    *,
    locked: AddressLockedSynthesisDraftV01,
    prop_by_key,
    existing_by_prop_key: dict[str, tuple[str, ...]],
    create_prop_keys: set[str],
    support_keys_by_slot_key: dict[str, set[str]],
) -> None:
    expected = set(prop_by_key)
    reuse_props = set(existing_by_prop_key)
    mutation_props = set()
    seen_existing_slots = set()

    for update in locked.existing_updates:
        if update.slot_key in seen_existing_slots:
            raise ValueError(
                f"address-locked synthesis duplicated existing slot {update.slot_key}"
            )
        seen_existing_slots.add(update.slot_key)
        if update.slot_key not in support_keys_by_slot_key:
            raise ValueError(
                f"address-locked synthesis referenced unknown slot {update.slot_key}"
            )
        if not set(update.retain_previous_support_keys) <= (
            support_keys_by_slot_key[update.slot_key]
        ):
            raise ValueError(
                "address-locked synthesis retained support outside fixed slot"
            )
        for prop_key in update.proposition_keys:
            allowed = set(existing_by_prop_key.get(prop_key, ()))
            if update.slot_key not in allowed:
                raise ValueError(
                    "address-locked synthesis used unauthorized existing slot; "
                    f"proposition_key={prop_key} slot_key={update.slot_key}"
                )
            mutation_props.add(prop_key)

    create_seen = set()
    for group in locked.create_groups:
        group_props = set(group.proposition_keys)
        if not group_props:
            raise ValueError("CREATE group may not be empty")
        if not group_props <= create_prop_keys:
            raise ValueError(
                "address-locked CREATE group contains non-CREATE proposition"
            )
        families = {
            prop_by_key[key].primitive_family
            for key in group_props
        }
        if len(families) != 1 or group.primitive_family not in families:
            raise ValueError(
                "address-locked CREATE group primitive_family mismatch"
            )
        create_seen.update(group_props)
        mutation_props.update(group_props)

    no_change = set(locked.no_change_proposition_keys)
    if not no_change <= reuse_props:
        raise ValueError(
            "only REUSE-authorized propositions may be NO_CHANGE"
        )
    overlap = mutation_props & no_change
    if overlap:
        raise ValueError(
            "proposition cannot both mutate and be NO_CHANGE; "
            f"overlap={sorted(overlap)}"
        )
    if create_seen != create_prop_keys:
        raise ValueError(
            "every CREATE-eligible proposition must appear in at least one "
            "CREATE group; "
            f"missing={sorted(create_prop_keys-create_seen)}"
        )
    covered = mutation_props | no_change
    if covered != expected:
        raise ValueError(
            "address-locked synthesis must cover every proposition; "
            f"missing={sorted(expected-covered)} "
            f"unknown={sorted(covered-expected)}"
        )
def validate_create_groups_semantically(
    *,
    event_identity: dict,
    flatmap: PropositionFlatMapResultV01,
    locked: AddressLockedSynthesisDraftV01,
    chat_fn,
    repeats: int = 2,
    max_workers: int = 8,
) -> CreateGroupValidationV01:
    """Verify CREATE grouping with the same one-proposition/one-question gate."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if not locked.create_groups:
        return CreateGroupValidationV01()

    _prop_key_by_id, prop_by_key = _prop_key_maps(flatmap)
    group_slots = []
    for index, group in enumerate(locked.create_groups, 1):
        group_key = f"C{index:03d}"
        group_slots.append((
            group_key,
            group,
            {
                "slot_id": group_key,
                "primitive_family": group.primitive_family,
                "slot_label": group.slot_label,
                "state_question": group.state_question,
                "value": group.value,
            },
        ))

    create_prop_keys = sorted({
        prop_key
        for group in locked.create_groups
        for prop_key in group.proposition_keys
    })
    pairs = []
    meta = []
    for prop_key in create_prop_keys:
        proposition = prop_by_key.get(prop_key)
        if proposition is None:
            raise ValueError(
                f"CREATE validation references unknown proposition {prop_key}"
            )
        for group_key, group, slot in group_slots:
            if group.primitive_family != proposition.primitive_family:
                continue
            member = prop_key in set(group.proposition_keys)
            pairs.append((proposition, slot))
            meta.append((prop_key, group_key, member))

    judgments = judge_direct_answer_parallel_consensus(
        event_identity=event_identity,
        pairs=pairs,
        chat_fn=chat_fn,
        repeats=repeats,
        max_workers=max_workers,
    )

    checks = []
    membership_failures = []
    cross_overlap = []
    uncertain = []
    for (prop_key, group_key, member), judgment in zip(meta, judgments):
        checks.append(CreateGroupPairCheckV01(
            proposition_key=prop_key,
            group_key=group_key,
            member=member,
            decision=judgment.decision,
            rationale=judgment.rationale,
        ))
        label = f"{prop_key}->{group_key}"
        if judgment.decision == "UNCERTAIN":
            uncertain.append(label)
        if member and judgment.decision != "DIRECT":
            membership_failures.append(label)
        if not member and judgment.decision == "DIRECT":
            cross_overlap.append(label)

    return CreateGroupValidationV01(
        checks=tuple(checks),
        membership_failures=tuple(sorted(set(membership_failures))),
        cross_overlap_findings=tuple(sorted(set(cross_overlap))),
        uncertain_findings=tuple(sorted(set(uncertain))),
    )


def _locked_to_semantic_draft(
    *,
    locked: AddressLockedSynthesisDraftV01,
    previous: SemanticSlotStateV01 | None,
    flatmap: PropositionFlatMapResultV01,
    address_policy: KeyByAddressPolicyV01,
) -> SemanticKeyByDraftV01:
    prop_key_by_id, prop_by_key = _prop_key_maps(flatmap)
    (
        slot_key_by_id,
        _slot_id_by_key,
        _prev_ref_by_key,
        payload_by_key,
        support_keys_by_slot_key,
    ) = _slot_payload(previous)
    existing_by_prop_key, create_prop_keys = _address_policy_aliases(
        policy=address_policy,
        proposition_key_by_id=prop_key_by_id,
        slot_key_by_id=slot_key_by_id,
    )
    _validate_locked_draft(
        locked=locked,
        prop_by_key=prop_by_key,
        existing_by_prop_key=existing_by_prop_key,
        create_prop_keys=create_prop_keys,
        support_keys_by_slot_key=support_keys_by_slot_key,
    )

    mutations = []
    indices_by_prop: dict[str, list[int]] = {
        key: [] for key in prop_by_key
    }
    for update in locked.existing_updates:
        slot = payload_by_key[update.slot_key]
        index = len(mutations)
        mutations.append(KeyByMutationDraftV01(
            target="EXISTING",
            existing_slot_key=update.slot_key,
            primitive_family=slot["primitive_family"],
            slot_label=slot["slot_label"],
            state_question=slot["state_question"],
            value=update.value,
            retain_previous_support_keys=(
                update.retain_previous_support_keys
            ),
            contest=update.contest,
            rationale=update.rationale,
        ))
        for prop_key in update.proposition_keys:
            indices_by_prop[prop_key].append(index)

    for group in locked.create_groups:
        index = len(mutations)
        mutations.append(KeyByMutationDraftV01(
            target="CREATE",
            existing_slot_key=None,
            primitive_family=group.primitive_family,
            slot_label=group.slot_label,
            state_question=group.state_question,
            value=group.value,
            retain_previous_support_keys=(),
            contest=False,
            rationale=group.rationale,
        ))
        for prop_key in group.proposition_keys:
            indices_by_prop[prop_key].append(index)

    no_change = set(locked.no_change_proposition_keys)
    routes = []
    for prop_key in sorted(prop_by_key):
        indices = tuple(sorted(set(indices_by_prop[prop_key])))
        routes.append(PropositionRouteV01(
            proposition_key=prop_key,
            disposition=(
                "NO_WORLD_VALUE_CHANGE"
                if prop_key in no_change
                else "WORLD_MUTATION"
            ),
            mutation_indices=indices,
            rationale=None,
        ))

    draft = SemanticKeyByDraftV01(
        mutations=tuple(mutations),
        proposition_routes=tuple(routes),
        phase_change=locked.phase_change,
        rationale=locked.rationale,
    )
    draft = _normalize_keyby_draft(draft)
    _validate_keyby_draft(
        draft=draft,
        expected_prop_keys=set(prop_by_key),
        proposition_family_by_key={
            key: proposition.primitive_family
            for key, proposition in prop_by_key.items()
        },
    )
    _validate_address_policy(
        draft=draft,
        authorized_existing_slot_keys_by_proposition=(
            existing_by_prop_key
        ),
        create_eligible_proposition_keys=create_prop_keys,
    )
    return draft
def _materialize_draft(
    *,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    flatmap: PropositionFlatMapResultV01,
    draft: SemanticKeyByDraftV01,
) -> SlotDeltaV01 | None:
    propositions = flatmap.world_propositions
    prop_key_by_id, prop_by_key = _prop_key_maps(flatmap)
    slot_key_by_id, slot_id_by_key = _slot_aliases(previous)
    prev_key_by_ref, prev_ref_by_key = _previous_support_aliases(previous)

    support_keys_by_slot_key: dict[str, set[str]] = {}
    if previous is not None:
        for slot in previous.slots:
            slot_key = slot_key_by_id[slot.slot_id]
            support_keys_by_slot_key[slot_key] = {
                prev_key_by_ref[ref]
                for ref in slot.support_refs
            }

    new_support_by_mutation = {
        index: set()
        for index in range(len(draft.mutations))
    }
    for route in draft.proposition_routes:
        if route.disposition != "WORLD_MUTATION":
            continue
        proposition = prop_by_key[route.proposition_key]
        for index in route.mutation_indices:
            new_support_by_mutation[index].update(
                proposition.support_refs
            )

    mutations = []
    for index, row in enumerate(draft.mutations):
        new_refs = new_support_by_mutation[index]
        if not new_refs:
            raise ValueError(
                "Every KeyBy mutation requires routed new proposition support"
            )

        if row.target == "EXISTING":
            slot_id = slot_id_by_key.get(row.existing_slot_key or "")
            if slot_id is None or previous is None:
                raise ValueError(
                    "address-locked synthesis referenced unknown existing slot"
                )
            previous_slot = next(
                slot
                for slot in previous.slots
                if slot.slot_id == slot_id
            )
            if row.primitive_family != previous_slot.primitive_family:
                raise ValueError(
                    "Existing slot primitive_family is immutable"
                )
            if row.state_question != previous_slot.state_question:
                raise ValueError(
                    "Existing slot state_question is immutable"
                )
            allowed_old = support_keys_by_slot_key[
                row.existing_slot_key or ""
            ]
            selected_old = set(row.retain_previous_support_keys)
            if not selected_old <= allowed_old:
                raise ValueError(
                    "selected previous support outside fixed existing slot"
                )
            if row.contest:
                old_refs = set(previous_slot.support_refs)
                mode = "CONTEST"
            else:
                old_refs = {
                    prev_ref_by_key[key]
                    for key in selected_old
                }
                mode = "UPSERT"
        else:
            slot_id = _new_slot_id(
                observation=observation,
                ordinal=index,
                state_question=row.state_question,
            )
            old_refs = set()
            mode = "CREATE"

        mutations.append(SlotMutationV01(
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
        ))

    if not mutations:
        if previous is None:
            raise ValueError(
                "First Event observation cannot produce empty SlotDelta"
            )
        return None

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
    return delta
def semantic_keyby_address_locked(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    flatmap: PropositionFlatMapResultV01,
    address_policy: KeyByAddressPolicyV01,
    chat_fn,
) -> tuple[
    SlotDeltaV01 | None,
    SemanticKeyByDraftV01,
    AddressLockedSynthesisDraftV01,
]:
    propositions = flatmap.world_propositions
    if not propositions:
        raise ValueError(
            "address-locked synthesis requires at least one World proposition"
        )

    prop_key_by_id, prop_by_key = _prop_key_maps(flatmap)
    (
        slot_key_by_id,
        _slot_id_by_key,
        _prev_ref_by_key,
        payload_by_key,
        _support_keys_by_slot_key,
    ) = _slot_payload(previous)
    existing_by_prop_key, create_prop_keys = _address_policy_aliases(
        policy=address_policy,
        proposition_key_by_id=prop_key_by_id,
        slot_key_by_id=slot_key_by_id,
    )

    authorized_by_slot: dict[str, list[str]] = {}
    for prop_key, slot_keys in existing_by_prop_key.items():
        for slot_key in slot_keys:
            authorized_by_slot.setdefault(slot_key, []).append(prop_key)

    payload = {
        "event_identity": dict(event_identity),
        "previous_status": previous.status if previous is not None else None,
        "world_propositions": [
            {
                "proposition_key": key,
                "statement": proposition.statement,
                "primitive_family": proposition.primitive_family,
                "referent_scope": proposition.referent_scope,
            }
            for key, proposition in prop_by_key.items()
        ],
        "authorized_existing_groups": [
            {
                **payload_by_key[slot_key],
                "authorized_proposition_keys": sorted(prop_keys),
            }
            for slot_key, prop_keys in sorted(
                authorized_by_slot.items()
            )
        ],
        "create_eligible_proposition_keys": sorted(create_prop_keys),
    }

    obj, _meta, _validation = chat_json_schema(
        [
            {"role": "system", "content": _ADDRESS_LOCKED_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Synthesize values under the fixed semantic address policy.\n\n"
                    + json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                ),
            },
        ],
        AddressLockedSynthesisDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    locked = AddressLockedSynthesisDraftV01.model_validate(obj)
    draft = _locked_to_semantic_draft(
        locked=locked,
        previous=previous,
        flatmap=flatmap,
        address_policy=address_policy,
    )
    delta = _materialize_draft(
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        draft=draft,
    )
    return delta, draft, locked
def semantic_keyby_pairwise_address_locked(
    *,
    event_identity: dict,
    previous: SemanticSlotStateV01 | None,
    observation: EventObservationV01,
    flatmap: PropositionFlatMapResultV01,
    chat_fn,
    candidate_top_k: int = 2,
    candidate_retriever=None,
    pairwise_chat_fn=None,
    pairwise_repeats: int = 2,
    pairwise_transport: PairwiseTransport = "PARALLEL",
    pairwise_max_workers: int = 8,
    verify_full_family_on_reuse: bool = False,
    validate_create_groups: bool = True,
    create_group_validation_repeats: int = 2,
    create_group_validation_max_workers: int = 8,
) -> AddressLockedKeyByResultV01:
    propositions = flatmap.world_propositions
    current_slots = list(previous.slots) if previous is not None else []

    candidate_plan = build_candidate_adjudication_plan(
        propositions=propositions,
        current_slots=current_slots,
        top_k=candidate_top_k,
        retriever=candidate_retriever,
    )
    builder = (
        build_pairwise_authorization_plan_parallel
        if pairwise_transport == "PARALLEL"
        else build_pairwise_authorization_plan
    )
    kwargs = {
        "event_identity": event_identity,
        "propositions": propositions,
        "current_slots": current_slots,
        "candidate_plan": candidate_plan,
        "chat_fn": pairwise_chat_fn or chat_fn,
        "repeats": pairwise_repeats,
        "verify_full_family_on_reuse": verify_full_family_on_reuse,
    }
    if pairwise_transport == "PARALLEL":
        kwargs["max_workers"] = pairwise_max_workers
    pairwise_plan = builder(**kwargs)
    address_policy = _address_policy_from_pairwise_plan(pairwise_plan)

    delta, draft, locked = semantic_keyby_address_locked(
        event_identity=event_identity,
        previous=previous,
        observation=observation,
        flatmap=flatmap,
        address_policy=address_policy,
        chat_fn=chat_fn,
    )
    create_validation = None
    if validate_create_groups:
        create_validation = validate_create_groups_semantically(
            event_identity=event_identity,
            flatmap=flatmap,
            locked=locked,
            chat_fn=pairwise_chat_fn or chat_fn,
            repeats=create_group_validation_repeats,
            max_workers=create_group_validation_max_workers,
        )
        if not create_validation.valid:
            raise CreateGroupSemanticValidationError(create_validation)

    return AddressLockedKeyByResultV01(
        delta=delta,
        draft=draft,
        locked_draft=locked,
        candidate_plan=candidate_plan,
        pairwise_plan=pairwise_plan,
        address_policy=address_policy,
        pairwise_transport=pairwise_transport,
        create_group_validation=create_validation,
    )
