from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.cognitive.client import chat_json_schema
from app.services.event_observation import EventObservationV01
from app.services.event_state import (
    EventStateV02,
    WorldStateV02,
    make_event_state_v02,
    structural_evidence_state_v02,
)


STATE_TRANSITION_ESTIMATOR_CONTRACT = "event-state-transition-estimator-v0.1"
STATE_REDUCER_CONTRACT = "event-state-reducer-v0.1"

TransitionKind = Literal[
    "INITIALIZE",
    "NO_MATERIAL_CHANGE",
    "ENRICH",
    "REPLACE_CURRENT",
    "CONTEST",
]


class StateTransitionProposalV01(BaseModel):
    contract: str = STATE_TRANSITION_ESTIMATOR_CONTRACT
    transition_kind: TransitionKind
    world_state: WorldStateV02
    rationale: str = Field(min_length=1, max_length=4000)


class StateReductionResultV01(BaseModel):
    contract: str = STATE_REDUCER_CONTRACT
    transition_kind: TransitionKind
    previous_state_digest: str | None
    observation_key: str
    next_state: EventStateV02


_PHI_SYSTEM = """You are the RAOS Semantic State Delta Estimator V0.1.

You update the CURRENT STATE of one already-identified coarse Event.

You are NOT resolving Event identity. Event identity is already fixed.
You are NOT summarizing all history. Use only:
- previous current WorldState,
- newly admitted audited semantic units,
- observation timing/provenance metadata.

Return exactly one JSON object with this shape:
{
  "contract": "event-state-transition-estimator-v0.1",
  "transition_kind": "INITIALIZE | NO_MATERIAL_CHANGE | ENRICH | REPLACE_CURRENT | CONTEST",
  "world_state": {
    "synopsis": "concise current-state text",
    "status": "short current phase/status or null",
    "effective_at": "ISO-8601 timestamp or null",
    "active_semantic_unit_refs": ["allowed-ref", "..."]
  },
  "rationale": "brief explanation of why this transition kind is correct"
}

Rules:
1. Every active semantic-unit ref MUST come from the allowed ref set supplied by the caller.
2. Preserve previous active refs unless the new evidence makes them obsolete for the current projection.
3. Historical evidence is never deleted; dropping an old ref only means it is no longer active in CURRENT state.
4. If the new evidence only corroborates existing state, use NO_MATERIAL_CHANGE and preserve WorldState exactly.
5. ENRICH means new current information is added while prior current information remains valid.
6. REPLACE_CURRENT means new evidence corrects/supersedes a previous current assertion.
7. CONTEST means materially incompatible current assertions remain unresolved; keep refs for both supported sides.
8. Do not invent facts or confidence scores.
"""


def _world_payload(state: EventStateV02 | None) -> dict | None:
    if state is None:
        return None
    return state.world_state.model_dump(mode="json")


def estimate_state_transition(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    new_semantic_units: list[dict],
    chat_fn,
) -> StateTransitionProposalV01:
    """LLM Phi: propose a small supported next WorldState.

    Authority remains with reduce_state_transition(), which validates all refs
    and transition semantics deterministically.
    """

    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    new_refs = set(observation.audited_semantic_unit_refs)
    allowed_refs = sorted(previous_refs | new_refs)

    payload = {
        "contract": STATE_TRANSITION_ESTIMATOR_CONTRACT,
        "event_id": str(observation.event_id),
        "previous_world_state": _world_payload(previous),
        "new_observation": observation.model_dump(mode="json"),
        "new_audited_semantic_units": new_semantic_units,
        "allowed_active_semantic_unit_refs": allowed_refs,
    }

    obj, _meta, _validation_events = chat_json_schema(
        [
            {"role": "system", "content": _PHI_SYSTEM},
            {
                "role": "user",
                "content": "Propose the next supported current WorldState.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        StateTransitionProposalV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    return StateTransitionProposalV01.model_validate(obj)


def _validate_transition_semantics(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    proposal: StateTransitionProposalV01,
) -> None:
    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    new_refs = set(observation.audited_semantic_unit_refs)
    proposed_refs = set(proposal.world_state.active_semantic_unit_refs)
    allowed = previous_refs | new_refs

    unsupported = proposed_refs - allowed
    if unsupported:
        raise ValueError(
            "State transition proposed unsupported semantic refs: "
            + ", ".join(sorted(unsupported))
        )

    kind = proposal.transition_kind

    if previous is None:
        if kind != "INITIALIZE":
            raise ValueError("First EventState transition must be INITIALIZE")
        if not proposed_refs:
            raise ValueError("INITIALIZE requires at least one supported active ref")
        if not proposed_refs <= new_refs:
            raise ValueError("INITIALIZE may only activate new observation refs")
        return

    if kind == "INITIALIZE":
        raise ValueError("INITIALIZE is invalid when previous EventState exists")

    if kind == "NO_MATERIAL_CHANGE":
        if proposal.world_state != previous.world_state:
            raise ValueError(
                "NO_MATERIAL_CHANGE must preserve WorldState exactly"
            )
        return

    if kind == "ENRICH":
        if not previous_refs <= proposed_refs:
            raise ValueError("ENRICH may not drop previous active refs")
        if not (proposed_refs & new_refs):
            raise ValueError("ENRICH must activate at least one new observation ref")
        return

    if kind == "REPLACE_CURRENT":
        if not (proposed_refs & new_refs):
            raise ValueError(
                "REPLACE_CURRENT must activate at least one new observation ref"
            )
        if proposed_refs == previous_refs:
            raise ValueError(
                "REPLACE_CURRENT must materially change active refs"
            )
        return

    if kind == "CONTEST":
        if not (proposed_refs & previous_refs):
            raise ValueError("CONTEST must retain at least one previous active ref")
        if not (proposed_refs & new_refs):
            raise ValueError("CONTEST must activate at least one new observation ref")
        return

    raise AssertionError(f"Unhandled transition kind {kind}")


def reduce_state_transition(
    db: Session,
    *,
    event_id: UUID,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    proposal: StateTransitionProposalV01,
    supporting_source_ids: tuple[UUID, ...] | list[UUID] | set[UUID],
) -> StateReductionResultV01:
    """Deterministic R: validate proposal and materialize next EventState V0.2."""

    if observation.event_id != event_id:
        raise ValueError("Observation Event id does not match reducer Event id")
    if previous is not None and previous.event_id != event_id:
        raise ValueError("Previous EventState belongs to another Event")

    _validate_transition_semantics(
        previous=previous,
        observation=observation,
        proposal=proposal,
    )

    source_ids = sorted(set(supporting_source_ids), key=str)
    if observation.source_id not in source_ids:
        raise ValueError("Reducer source prefix must include the current observation source")

    next_evidence_state = structural_evidence_state_v02(
        db,
        event_id,
        active_semantic_unit_refs=proposal.world_state.active_semantic_unit_refs,
        supporting_source_ids=source_ids,
    )
    next_state = make_event_state_v02(
        event_id=event_id,
        world_state=proposal.world_state,
        evidence_state=next_evidence_state,
    )
    return StateReductionResultV01(
        transition_kind=proposal.transition_kind,
        previous_state_digest=(previous.state_digest if previous is not None else None),
        observation_key=observation.observation_key,
        next_state=next_state,
    )
