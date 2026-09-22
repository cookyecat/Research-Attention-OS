from __future__ import annotations

import json
from datetime import datetime
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


STATE_TRANSITION_ESTIMATOR_CONTRACT = "event-state-transition-estimator-v1.5"
STATE_REDUCER_CONTRACT = "event-state-reducer-v0.2"
PHI_SYNOPSIS_MAX_CHARS = 2000

TransitionKind = Literal[
    "INITIALIZE",
    "NO_MATERIAL_CHANGE",
    "ENRICH",
    "REPLACE_CURRENT",
    "CONTEST",
]

EventPhaseV01 = Literal[
    "EMERGING",
    "ACTIVE",
    "CONTESTED",
    "RESOLVED",
]
EVENT_PHASE_VALUES = {"EMERGING", "ACTIVE", "CONTESTED", "RESOLVED"}


class SupersessionPairV01(BaseModel):
    previous_ref: str = Field(min_length=1)
    new_ref: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class StateKeyPointV01(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    support_keys: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_support_keys(self):
        keys = tuple(sorted({str(key).strip() for key in self.support_keys if str(key).strip()}))
        if not keys:
            raise ValueError("State key point requires at least one support key")
        object.__setattr__(self, "support_keys", keys)
        return self


class DraftSupersessionPairV01(BaseModel):
    previous_key: str = Field(min_length=1)
    new_key: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class StateTransitionDraftV01(BaseModel):
    contract: str = STATE_TRANSITION_ESTIMATOR_CONTRACT
    transition_kind: TransitionKind
    key_points: tuple[StateKeyPointV01, ...] = Field(max_length=4)
    status: EventPhaseV01
    effective_at: datetime | None = None
    supersession_pairs: tuple[DraftSupersessionPairV01, ...] = ()
    rationale: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_draft_contract(self):
        if self.contract != STATE_TRANSITION_ESTIMATOR_CONTRACT:
            raise ValueError(f"contract must be {STATE_TRANSITION_ESTIMATOR_CONTRACT}")
        if self.transition_kind == "NO_MATERIAL_CHANGE":
            if self.supersession_pairs:
                raise ValueError("NO_MATERIAL_CHANGE may not carry supersession_pairs")
        elif not self.key_points:
            raise ValueError("Material state transition requires at least one key point")
        if self.transition_kind == "REPLACE_CURRENT":
            if not self.supersession_pairs:
                raise ValueError("REPLACE_CURRENT requires at least one explicit supersession pair")
        elif self.supersession_pairs:
            raise ValueError("supersession_pairs are only legal for REPLACE_CURRENT")
        return self


class StateTransitionProposalV03(BaseModel):
    contract: str = STATE_TRANSITION_ESTIMATOR_CONTRACT
    transition_kind: TransitionKind
    world_state: WorldStateV02
    supersession_pairs: tuple[SupersessionPairV01, ...] = ()
    rationale: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_estimator_contract(self):
        if self.contract != STATE_TRANSITION_ESTIMATOR_CONTRACT:
            raise ValueError(
                f"contract must be {STATE_TRANSITION_ESTIMATOR_CONTRACT}"
            )
        if len(self.world_state.synopsis) > PHI_SYNOPSIS_MAX_CHARS:
            raise ValueError(
                "Phi WorldState synopsis must stay within "
                f"{PHI_SYNOPSIS_MAX_CHARS} characters"
            )
        if self.world_state.status not in EVENT_PHASE_VALUES:
            raise ValueError(
                "Phi WorldState status must be one of "
                "EMERGING | ACTIVE | CONTESTED | RESOLVED"
            )
        if self.transition_kind == "REPLACE_CURRENT":
            if not self.supersession_pairs:
                raise ValueError(
                    "REPLACE_CURRENT requires at least one explicit supersession pair"
                )
        elif self.supersession_pairs:
            raise ValueError(
                "supersession_pairs are only legal for REPLACE_CURRENT"
            )
        return self


class StateReductionResultV02(BaseModel):
    contract: str = STATE_REDUCER_CONTRACT
    transition_kind: TransitionKind
    previous_state_digest: str | None
    observation_key: str
    next_state: EventStateV02


# Historical import aliases for existing eval runners.
StateTransitionProposalV02 = StateTransitionProposalV03
StateTransitionProposalV01 = StateTransitionProposalV03
StateReductionResultV01 = StateReductionResultV02


_PHI_SYSTEM = """You are the RAOS Semantic State Delta Estimator V1.5.

You update the CURRENT STATE of one already-identified coarse Event.

You are NOT resolving Event identity. Event identity is already fixed.
You are NOT summarizing all history. Use only:
- previous current WorldState,
- dereferenced audited semantic units for the previous active refs,
- newly admitted audited semantic units,
- observation timing/provenance metadata.

The dereferenced previous units are grounding for the CURRENT state only. They are not permission to restore historical facts that the previous WorldState has already dropped.

Return exactly one JSON object with this shape:
{
  "contract": "event-state-transition-estimator-v1.5",
  "transition_kind": "INITIALIZE | NO_MATERIAL_CHANGE | ENRICH | REPLACE_CURRENT | CONTEST",
  "key_points": [
    {
      "text": "one compact CURRENT-state point",
      "support_keys": ["P001 or N001", "..."]
    }
  ],
  "status": "EMERGING | ACTIVE | CONTESTED | RESOLVED",
  "effective_at": "ISO-8601 timestamp or null",
  "supersession_pairs": [
    {
      "previous_key": "P001",
      "new_key": "N001",
      "reason": "how the new evidence explicitly corrects or supersedes the previous assertion"
    }
  ],
  "rationale": "brief explanation of why this transition kind is correct"
}

Rules:
1. Return at most 4 key_points. They are the complete CURRENT sufficient-state projection, not a chronology and not a list of sources.
2. Each key point must be decision-relevant and compact. Merge related facts. Prefer one high-level point over many examples.
3. Every support_key MUST come from the allowed_support_keys set. Keys are short temporary aliases such as P001 (previous support) or N001 (new observation support). Never output raw semantic-unit refs.
4. Each support_key must directly support the key point it is attached to. Use the smallest sufficient support set for that key point. Do not attach a key merely because its evidence is historically true.
5. Use the dereferenced previous active semantic units to understand what P-keys support. If a previous fact is no longer represented by any current key point, drop all keys that only supported that old fact.
6. Historical evidence is never deleted; dropping a ref only means it is not needed to define CURRENT state. History remains append-only outside WorldState.
7. If new evidence only corroborates existing state without changing the current projection, use NO_MATERIAL_CHANGE. key_points may be empty; the caller will preserve the previous WorldState exactly.
8. ENRICH means materially new current information is added. It may also compact or refocus the current projection. At least one current key point must use at least one N-key.
9. REPLACE_CURRENT is ONLY for explicit correction or supersession. The new evidence must itself say or clearly entail that a previous CURRENT assertion was wrong, retracted, corrected, replaced, or no longer true. A later different occurrence, example, demo, object, use case, or timestamp does NOT supersede an earlier historical occurrence; both may remain true. Every REPLACE_CURRENT MUST include at least one supersession_pairs item mapping a P-key to an N-key.
10. For every non-REPLACE_CURRENT transition, supersession_pairs MUST be empty.
11. CONTEST means materially incompatible current assertions remain unresolved. Current key points must preserve supported live sides.
12. Exclude peripheral entity labels, generic uncertainty bookkeeping, quoted social reaction, and implementation metadata unless necessary to support a current key point.
13. status is ONLY the coarse Event lifecycle phase: EMERGING, ACTIVE, CONTESTED, or RESOLVED. Do not encode subtopics, evidence details, claims, or source titles in status. EMERGING is only for the initial appearance of an Event; once an existing Event receives a material update it is normally ACTIVE. Use CONTESTED only for unresolved incompatible current assertions and RESOLVED only for explicit closure/outcome.
14. Do not invent facts or confidence scores.
"""


def _world_payload(state: EventStateV02 | None) -> dict | None:
    if state is None:
        return None
    return state.world_state.model_dump(mode="json")


def _bounded_text(value: str | None, max_chars: int) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    if len(text) <= max_chars:
        return text
    window = text[: max_chars + 1]
    candidates = [
        window.rfind(". "),
        window.rfind("; "),
        window.rfind(", "),
        window.rfind(" "),
    ]
    cut = max(candidates)
    if cut < max_chars // 2:
        cut = max_chars
    bounded = window[:cut].rstrip(" ,;:-")
    if bounded and bounded[-1] not in ".!?":
        bounded += "."
    return bounded[:max_chars]


def _compose_bounded_synopsis(key_points: tuple[str, ...]) -> str:
    points = []
    for raw in key_points[:4]:
        bounded = _bounded_text(raw, 360)
        if bounded:
            points.append(bounded)
    synopsis = " ".join(points).strip()
    if not synopsis:
        raise ValueError("Compact repair produced no usable key points")
    final = _bounded_text(synopsis, PHI_SYNOPSIS_MAX_CHARS)
    if final is None or not final.strip():
        raise ValueError("Compact repair produced an empty synopsis")
    return final


def _canonical_event_phase(
    *,
    previous: EventStateV02 | None,
    transition_kind: TransitionKind,
    proposed_phase: EventPhaseV01,
) -> EventPhaseV01:
    if previous is None:
        return "EMERGING"

    previous_phase = previous.world_state.status
    if transition_kind == "NO_MATERIAL_CHANGE":
        return previous_phase
    if transition_kind == "CONTEST":
        return "CONTESTED"
    if proposed_phase == "RESOLVED":
        return "RESOLVED"
    if previous_phase == "RESOLVED":
        return "RESOLVED"
    if previous_phase == "CONTESTED":
        return "ACTIVE" if proposed_phase == "ACTIVE" else "CONTESTED"
    return "ACTIVE"


def _support_aliases(
    *,
    previous_refs: set[str],
    new_refs: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    previous_key_by_ref = {
        ref: f"P{i:03d}" for i, ref in enumerate(sorted(previous_refs), start=1)
    }
    new_key_by_ref = {
        ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), start=1)
    }
    ref_by_key = {
        **{key: ref for ref, key in previous_key_by_ref.items()},
        **{key: ref for ref, key in new_key_by_ref.items()},
    }
    return ref_by_key, previous_key_by_ref, new_key_by_ref


def _semantic_units_with_support_keys(
    rows: list[dict],
    *,
    key_by_ref: dict[str, str],
) -> list[dict]:
    result = []
    for row in rows:
        ref = str(row.get("unit_id") or "").strip()
        if ref not in key_by_ref:
            raise ValueError(f"Semantic unit is outside support-key map: {ref}")
        item = {key: value for key, value in row.items() if key != "unit_id"}
        item["support_key"] = key_by_ref[ref]
        result.append(item)
    return result


def estimate_state_transition(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    previous_active_semantic_units: list[dict] | None,
    new_semantic_units: list[dict],
    chat_fn,
) -> StateTransitionProposalV02:
    """LLM Phi: propose a small supported next WorldState.

    Authority remains with reduce_state_transition(), which validates all refs
    and transition semantics deterministically.
    """

    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    previous_active_semantic_units = list(previous_active_semantic_units or [])
    hydrated_previous_refs = {
        str(row.get("unit_id") or "").strip()
        for row in previous_active_semantic_units
        if str(row.get("unit_id") or "").strip()
    }
    if previous_refs != hydrated_previous_refs:
        missing = sorted(previous_refs - hydrated_previous_refs)
        extra = sorted(hydrated_previous_refs - previous_refs)
        raise ValueError(
            "Phi previous active support hydration must exactly match previous "
            f"active refs; missing={missing} extra={extra}"
        )

    new_refs = set(observation.audited_semantic_unit_refs)
    ref_by_key, previous_key_by_ref, new_key_by_ref = _support_aliases(
        previous_refs=previous_refs,
        new_refs=new_refs,
    )

    previous_world_state = _world_payload(previous)
    if previous_world_state is not None:
        previous_world_state = dict(previous_world_state)
        previous_world_state.pop("active_semantic_unit_refs", None)
        previous_world_state["active_support_keys"] = [
            previous_key_by_ref[ref]
            for ref in previous.world_state.active_semantic_unit_refs
        ]

    observation_payload = observation.model_dump(mode="json")
    observation_payload.pop("audited_semantic_unit_refs", None)
    observation_payload["audited_support_keys"] = [
        new_key_by_ref[ref]
        for ref in observation.audited_semantic_unit_refs
    ]

    payload = {
        "contract": STATE_TRANSITION_ESTIMATOR_CONTRACT,
        "event_id": str(observation.event_id),
        "previous_world_state": previous_world_state,
        "previous_active_semantic_units": _semantic_units_with_support_keys(
            previous_active_semantic_units,
            key_by_ref=previous_key_by_ref,
        ),
        "new_observation": observation_payload,
        "new_audited_semantic_units": _semantic_units_with_support_keys(
            new_semantic_units,
            key_by_ref=new_key_by_ref,
        ),
        "allowed_support_keys": sorted(ref_by_key),
    }
    messages = [
        {"role": "system", "content": _PHI_SYSTEM},
        {
            "role": "user",
            "content": "Propose the next supported current WorldState.\n\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]

    obj, _meta, _validation_events = chat_json_schema(
        messages,
        StateTransitionDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = StateTransitionDraftV01.model_validate(obj)

    def resolve_support_key(key: str) -> str:
        ref = ref_by_key.get(key)
        if ref is None:
            raise ValueError(f"Phi proposed unknown support key: {key}")
        return ref

    used_support_keys = {
        key
        for point in draft.key_points
        for key in point.support_keys
    }
    normalized_kind = draft.transition_kind
    normalized_rationale = draft.rationale
    if (
        normalized_kind == "ENRICH"
        and not any(key in set(new_key_by_ref.values()) for key in used_support_keys)
    ):
        normalized_kind = "NO_MATERIAL_CHANGE"
        normalized_rationale = (
            "Deterministic normalization: Phi labeled ENRICH but selected no "
            "new-observation support; preserve previous WorldState. "
            + draft.rationale
        )

    if normalized_kind == "NO_MATERIAL_CHANGE":
        if previous is None:
            raise ValueError("NO_MATERIAL_CHANGE is invalid without previous EventState")
        world_state = previous.world_state
    else:
        synopsis = _compose_bounded_synopsis(
            tuple(point.text for point in draft.key_points)
        )
        support_refs = tuple(
            sorted(
                {
                    resolve_support_key(key)
                    for point in draft.key_points
                    for key in point.support_keys
                }
            )
        )
        world_state = WorldStateV02(
            synopsis=synopsis,
            status=_canonical_event_phase(
                previous=previous,
                transition_kind=normalized_kind,
                proposed_phase=draft.status,
            ),
            effective_at=draft.effective_at,
            active_semantic_unit_refs=support_refs,
        )

    supersession_pairs = tuple(
        SupersessionPairV01(
            previous_ref=resolve_support_key(pair.previous_key),
            new_ref=resolve_support_key(pair.new_key),
            reason=pair.reason,
        )
        for pair in draft.supersession_pairs
    )

    proposal = StateTransitionProposalV02(
        transition_kind=normalized_kind,
        world_state=world_state,
        supersession_pairs=supersession_pairs,
        rationale=normalized_rationale,
    )

    return proposal


def _validate_phase_semantics(
    *,
    previous: EventStateV02 | None,
    proposal: StateTransitionProposalV02,
) -> None:
    phase = proposal.world_state.status
    if phase not in EVENT_PHASE_VALUES:
        raise ValueError(f"Unsupported Event phase: {phase}")

    if previous is None:
        return

    previous_phase = previous.world_state.status
    if previous_phase not in EVENT_PHASE_VALUES:
        raise ValueError(
            "Previous EventState phase is outside event-phase-v0.1 vocabulary: "
            f"{previous_phase}"
        )

    kind = proposal.transition_kind
    if kind == "NO_MATERIAL_CHANGE":
        return
    if kind == "CONTEST":
        if phase != "CONTESTED":
            raise ValueError("CONTEST transition requires status=CONTESTED")
        return

    allowed = {
        "EMERGING": {"EMERGING", "ACTIVE", "RESOLVED"},
        "ACTIVE": {"ACTIVE", "RESOLVED"},
        "CONTESTED": {"CONTESTED", "ACTIVE", "RESOLVED"},
        "RESOLVED": {"RESOLVED"},
    }
    if phase not in allowed[previous_phase]:
        raise ValueError(
            "Illegal Event phase transition: "
            f"{previous_phase} -> {phase} under {kind}"
        )


def _validate_transition_semantics(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    proposal: StateTransitionProposalV02,
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
    _validate_phase_semantics(previous=previous, proposal=proposal)

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
        # Current WorldState is a compact projection, not an evidence ledger.
        # Phi may retire redundant prior support refs when new evidence restates,
        # subsumes, or strengthens the same current meaning. History remains
        # append-only outside WorldState, so support compaction is not deletion.
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
        if not proposal.supersession_pairs:
            raise ValueError(
                "REPLACE_CURRENT requires explicit supersession pairs"
            )
        seen_pairs: set[tuple[str, str]] = set()
        for pair in proposal.supersession_pairs:
            identity = (pair.previous_ref, pair.new_ref)
            if identity in seen_pairs:
                raise ValueError(
                    "REPLACE_CURRENT supersession pairs must be unique"
                )
            seen_pairs.add(identity)
            if pair.previous_ref not in previous_refs:
                raise ValueError(
                    "REPLACE_CURRENT supersession previous_ref must be active "
                    f"in previous state: {pair.previous_ref}"
                )
            if pair.new_ref not in new_refs:
                raise ValueError(
                    "REPLACE_CURRENT supersession new_ref must come from the "
                    f"new observation: {pair.new_ref}"
                )
            if pair.previous_ref in proposed_refs:
                raise ValueError(
                    "REPLACE_CURRENT corrected previous_ref must be retired "
                    f"from current state: {pair.previous_ref}"
                )
            if pair.new_ref not in proposed_refs:
                raise ValueError(
                    "REPLACE_CURRENT correcting new_ref must be active in "
                    f"current state: {pair.new_ref}"
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
    proposal: StateTransitionProposalV02,
    supporting_source_ids: tuple[UUID, ...] | list[UUID] | set[UUID],
) -> StateReductionResultV02:
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
    return StateReductionResultV02(
        transition_kind=proposal.transition_kind,
        previous_state_digest=(previous.state_digest if previous is not None else None),
        observation_key=observation.observation_key,
        next_state=next_state,
    )
