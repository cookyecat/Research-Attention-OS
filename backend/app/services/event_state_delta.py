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


STATE_DELTA_CONTRACT = "event-state-delta-v0.1"
STATE_DECIDER_CONTRACT = "event-state-decider-v0.1"
STATE_APPLIER_CONTRACT = "event-state-applier-v0.1"

DeltaKind = Literal["ADD", "SUPERSEDE", "CONTEST"]
DraftKind = Literal["NONE", "ADD", "SUPERSEDE", "CONTEST"]
EventPhase = Literal["EMERGING", "ACTIVE", "CONTESTED", "RESOLVED"]
class SupersessionPairV01(BaseModel):
    previous_ref: str = Field(min_length=1)
    new_ref: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class StateDeltaV01(BaseModel):
    contract: str = STATE_DELTA_CONTRACT
    kind: DeltaKind
    activate_refs: tuple[str, ...] = ()
    retire_refs: tuple[str, ...] = ()
    supersession_pairs: tuple[SupersessionPairV01, ...] = ()
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def normalize_and_validate(self):
        activate = tuple(sorted({str(v).strip() for v in self.activate_refs if str(v).strip()}))
        retire = tuple(sorted({str(v).strip() for v in self.retire_refs if str(v).strip()}))
        object.__setattr__(self, "activate_refs", activate)
        object.__setattr__(self, "retire_refs", retire)

        if not activate:
            raise ValueError(f"{self.kind} requires at least one activate_ref")
        if set(activate) & set(retire):
            raise ValueError("activate_refs and retire_refs must be disjoint")
        if self.kind == "SUPERSEDE":
            if not retire:
                raise ValueError("SUPERSEDE requires at least one retire_ref")
            if not self.supersession_pairs:
                raise ValueError("SUPERSEDE requires explicit supersession_pairs")
        elif self.supersession_pairs:
            raise ValueError("supersession_pairs are only legal for SUPERSEDE")
        return self


class DraftSupersessionPairV01(BaseModel):
    previous_key: str = Field(min_length=1)
    new_key: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class StateDeltaDraftV01(BaseModel):
    contract: str = STATE_DECIDER_CONTRACT
    kind: DraftKind
    activate_keys: tuple[str, ...] = ()
    retire_keys: tuple[str, ...] = ()
    supersession_pairs: tuple[DraftSupersessionPairV01, ...] = ()
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_draft(self):
        if self.contract != STATE_DECIDER_CONTRACT:
            raise ValueError(f"contract must be {STATE_DECIDER_CONTRACT}")
        if self.kind == "NONE":
            if self.activate_keys or self.retire_keys or self.supersession_pairs or self.phase_change:
                raise ValueError("NONE may not carry state mutations")
            return self
        if not self.activate_keys:
            raise ValueError(f"{self.kind} requires at least one activate_key")
        if self.kind == "SUPERSEDE":
            if not self.retire_keys or not self.supersession_pairs:
                raise ValueError("SUPERSEDE requires retire_keys and supersession_pairs")
        elif self.supersession_pairs:
            raise ValueError("supersession_pairs are only legal for SUPERSEDE")
        return self


class StateApplyResultV01(BaseModel):
    contract: str = STATE_APPLIER_CONTRACT
    delta_kind: DeltaKind | None
    previous_state_digest: str | None
    observation_key: str
    next_state: EventStateV02


_DECIDE_SYSTEM = """You are the RAOS Event State Decide function.

Your task is narrow: classify how NEW audited semantic evidence changes the CURRENT Event state.
Do not rewrite the next EventState. Do not write a synopsis.
Return exactly one JSON object. Use these exact field names and no substitutes:
{
  "contract": "event-state-decider-v0.1",
  "kind": "NONE | ADD | SUPERSEDE | CONTEST",
  "activate_keys": ["N001", "..."],
  "retire_keys": ["P001", "..."],
  "supersession_pairs": [
    {
      "previous_key": "P001",
      "new_key": "N001",
      "reason": "brief explicit correction/replacement reason"
    }
  ],
  "phase_change": "EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale": "brief semantic relation explanation"
}

For NONE, use empty activate_keys, retire_keys, supersession_pairs, and null phase_change.
Use only these relations:
- NONE: no material current WorldState change; duplicate/corroborating evidence only.
- ADD: new compatible current information.
- SUPERSEDE: new evidence explicitly or necessarily makes a currently active assertion wrong, corrected, retracted, replaced, or no longer true.
- CONTEST: materially incompatible current assertions remain unresolved.

Important:
- A later different demo, example, occurrence, object, timestamp, or use case is NOT supersession by itself.
- ADD may retire previous support only when it becomes redundant in the CURRENT projection; retirement never deletes History.
- SUPERSEDE must map previous P-keys to correcting N-keys.
- CONTEST must add at least one N-key and preserve at least one live previous side.
- Use only supplied Pxxx/Nxxx support keys.
- Prefer NONE over inventing a change.
- Do not invent facts, refs, confidence scores, or extra relation types.
"""


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


def _units_with_keys(rows: list[dict], key_by_ref: dict[str, str]) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        ref = str(row.get("unit_id") or "").strip()
        if ref not in key_by_ref:
            raise ValueError(f"Semantic unit is outside support-key map: {ref}")
        item = {k: v for k, v in row.items() if k != "unit_id"}
        item["support_key"] = key_by_ref[ref]
        result.append(item)
    return result


def decide_state_delta(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    previous_active_semantic_units: list[dict] | None,
    new_semantic_units: list[dict],
    chat_fn,
) -> StateDeltaV01 | None:
    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    previous_units = list(previous_active_semantic_units or [])
    hydrated_previous_refs = {
        str(row.get("unit_id") or "").strip()
        for row in previous_units
        if str(row.get("unit_id") or "").strip()
    }
    if hydrated_previous_refs != previous_refs:
        raise ValueError(
            "Decide previous active support hydration must exactly match previous active refs"
        )

    new_refs = set(observation.audited_semantic_unit_refs)
    ref_by_key, previous_key_by_ref, new_key_by_ref = _support_aliases(
        previous_refs=previous_refs,
        new_refs=new_refs,
    )

    previous_state = None
    if previous is not None:
        previous_state = {
            "status": previous.world_state.status,
            "effective_at": previous.world_state.effective_at,
            "active_support_keys": [
                previous_key_by_ref[ref]
                for ref in previous.world_state.active_semantic_unit_refs
            ],
        }

    observation_payload = {
        "observation_key": observation.observation_key,
        "evidence_time": observation.evidence_time,
        "world_time": observation.world_time,
        "provenance_digest": observation.provenance_digest,
        "audited_support_keys": [
            new_key_by_ref[ref] for ref in observation.audited_semantic_unit_refs
        ],
    }
    payload = {
        "contract": STATE_DECIDER_CONTRACT,
        "previous_state": previous_state,
        "previous_active_semantic_units": _units_with_keys(
            previous_units, previous_key_by_ref
        ),
        "new_observation": observation_payload,
        "new_audited_semantic_units": _units_with_keys(
            new_semantic_units, new_key_by_ref
        ),
        "allowed_support_keys": sorted(ref_by_key),
    }
    messages = [
        {"role": "system", "content": _DECIDE_SYSTEM},
        {
            "role": "user",
            "content": "Decide the minimal semantic state delta.\n\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        },
    ]
    obj, _meta, _validation_events = chat_json_schema(
        messages,
        StateDeltaDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = StateDeltaDraftV01.model_validate(obj)
    if draft.kind == "NONE":
        if previous is None:
            raise ValueError("First Event observation cannot produce NONE")
        return None

    def resolve(key: str) -> str:
        ref = ref_by_key.get(key)
        if ref is None:
            raise ValueError(f"Decide proposed unknown support key: {key}")
        return ref

    delta = StateDeltaV01(
        kind=draft.kind,
        activate_refs=tuple(resolve(k) for k in draft.activate_keys),
        retire_refs=tuple(resolve(k) for k in draft.retire_keys),
        supersession_pairs=tuple(
            SupersessionPairV01(
                previous_ref=resolve(pair.previous_key),
                new_ref=resolve(pair.new_key),
                reason=pair.reason,
            )
            for pair in draft.supersession_pairs
        ),
        phase_change=draft.phase_change,
        rationale=draft.rationale,
    )
    _validate_delta_against_observation(
        previous=previous,
        observation=observation,
        delta=delta,
    )
    return delta


def _validate_delta_against_observation(
    *,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    delta: StateDeltaV01,
) -> None:
    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    new_refs = set(observation.audited_semantic_unit_refs)
    activate = set(delta.activate_refs)
    retire = set(delta.retire_refs)

    if not activate <= new_refs:
        raise ValueError("StateDelta activate_refs must come from the new observation")
    if not retire <= previous_refs:
        raise ValueError("StateDelta retire_refs must come from previous active refs")

    if delta.kind == "SUPERSEDE":
        for pair in delta.supersession_pairs:
            if pair.previous_ref not in retire:
                raise ValueError("SUPERSEDE previous_ref must be retired")
            if pair.new_ref not in activate:
                raise ValueError("SUPERSEDE new_ref must be activated")
    elif delta.kind == "CONTEST":
        remaining_previous = previous_refs - retire
        if not remaining_previous:
            raise ValueError("CONTEST must preserve at least one previous active side")


def _next_phase(
    previous: EventStateV02 | None,
    delta: StateDeltaV01 | None,
) -> EventPhase:
    if delta is None:
        if previous is None:
            raise ValueError("No previous phase exists for an empty delta")
        return previous.world_state.status  # type: ignore[return-value]
    if delta.kind == "CONTEST":
        return "CONTESTED"
    if delta.phase_change is not None:
        return delta.phase_change
    if previous is None:
        return "EMERGING"
    previous_phase = previous.world_state.status
    if previous_phase == "EMERGING":
        return "ACTIVE"
    if previous_phase in {"ACTIVE", "RESOLVED"}:
        return previous_phase  # type: ignore[return-value]
    return "CONTESTED"


def _bounded(text: str, max_chars: int = 2000) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    window = text[: max_chars + 1]
    cut = window.rfind(" ")
    if cut < max_chars // 2:
        cut = max_chars
    return window[:cut].rstrip(" ,;:-") + "."


def _render_synopsis(
    active_refs: tuple[str, ...],
    semantic_units_by_ref: dict[str, dict],
) -> str:
    statements: list[str] = []
    seen: set[str] = set()
    for ref in active_refs:
        row = semantic_units_by_ref.get(ref)
        if row is None:
            raise ValueError(f"Missing semantic unit for active ref: {ref}")
        statement = " ".join(str(row.get("statement") or "").split())
        if statement and statement not in seen:
            seen.add(statement)
            statements.append(statement)
    if not statements:
        raise ValueError("Current state requires at least one renderable active statement")
    return _bounded(" ".join(statements))


def apply_state_delta(
    db: Session,
    *,
    event_id: UUID,
    previous: EventStateV02 | None,
    observation: EventObservationV01,
    delta: StateDeltaV01 | None,
    supporting_source_ids: tuple[UUID, ...] | list[UUID] | set[UUID],
    semantic_units_by_ref: dict[str, dict],
) -> StateApplyResultV01:
    if observation.event_id != event_id:
        raise ValueError("Observation Event id does not match Apply Event id")
    if previous is not None and previous.event_id != event_id:
        raise ValueError("Previous EventState belongs to another Event")
    previous_refs = (
        set(previous.world_state.active_semantic_unit_refs) if previous is not None else set()
    )
    if delta is None:
        if previous is None:
            raise ValueError("First Event observation requires a material StateDelta")
        next_refs = set(previous_refs)
        synopsis = previous.world_state.synopsis
        effective_at = previous.world_state.effective_at
    else:
        _validate_delta_against_observation(
            previous=previous,
            observation=observation,
            delta=delta,
        )
        next_refs = (previous_refs - set(delta.retire_refs)) | set(delta.activate_refs)
        if not next_refs:
            raise ValueError("Apply may not materialize an empty current support set")
        ordered_refs = tuple(sorted(next_refs))
        synopsis = _render_synopsis(ordered_refs, semantic_units_by_ref)
        effective_at = observation.world_time or observation.evidence_time

    ordered_refs = tuple(sorted(next_refs))
    world_state = WorldStateV02(
        synopsis=synopsis,
        status=_next_phase(previous, delta),
        effective_at=effective_at,
        active_semantic_unit_refs=ordered_refs,
    )
    source_ids = sorted(set(supporting_source_ids), key=str)
    if observation.source_id not in source_ids:
        raise ValueError("Apply source prefix must include the current observation source")

    evidence_state = structural_evidence_state_v02(
        db,
        event_id,
        active_semantic_unit_refs=ordered_refs,
        supporting_source_ids=source_ids,
    )
    next_state = make_event_state_v02(
        event_id=event_id,
        world_state=world_state,
        evidence_state=evidence_state,
    )
    return StateApplyResultV01(
        delta_kind=(delta.kind if delta is not None else None),
        previous_state_digest=(previous.state_digest if previous is not None else None),
        observation_key=observation.observation_key,
        next_state=next_state,
    )
