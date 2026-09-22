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
from app.services.event_state import (
    EventStateV02,
    WorldStateV02,
    make_event_state_v02,
    structural_evidence_state_v02,
)


FACT_STATE_CONTRACT = "event-semantic-fact-state-v0.1"
FACT_DELTA_CONTRACT = "event-state-fact-delta-v0.1"
FACT_DECIDER_CONTRACT = "event-state-fact-decider-v0.4"
FACT_APPLIER_CONTRACT = "event-state-fact-applier-v0.2"

FactDeltaKind = Literal["ADD", "SUPERSEDE", "CONTEST"]
FactDraftKind = Literal["NONE", "ADD", "SUPERSEDE", "CONTEST"]
EventPhase = Literal["EMERGING", "ACTIVE", "CONTESTED", "RESOLVED"]
def _stable_digest(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CurrentFactV01(BaseModel):
    fact_id: str = Field(min_length=8)
    text: str = Field(min_length=1, max_length=4000)
    support_refs: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def normalize(self):
        refs = tuple(sorted({str(v).strip() for v in self.support_refs if str(v).strip()}))
        if not refs:
            raise ValueError("CurrentFact requires support_refs")
        object.__setattr__(self, "support_refs", refs)
        object.__setattr__(self, "text", " ".join(self.text.split()))
        return self


class SemanticFactStateV01(BaseModel):
    contract: str = FACT_STATE_CONTRACT
    event_id: UUID
    facts: tuple[CurrentFactV01, ...]
    status: EventPhase
    effective_at: datetime | None = None
    state_digest: str
    @model_validator(mode="after")
    def validate_digest(self):
        expected = fact_state_digest(
            event_id=self.event_id,
            facts=self.facts,
            status=self.status,
            effective_at=self.effective_at,
        )
        if self.state_digest != expected:
            raise ValueError("event-semantic-fact-state-v0.1 digest mismatch")
        return self


def fact_state_digest(
    *,
    event_id: UUID,
    facts: tuple[CurrentFactV01, ...],
    status: EventPhase,
    effective_at: datetime | None,
) -> str:
    return _stable_digest(
        {
            "contract": FACT_STATE_CONTRACT,
            "event_id": str(event_id),
            "facts": [row.model_dump(mode="json") for row in facts],
            "status": status,
            "effective_at": effective_at,
        }
    )


def make_fact_state(
    *,
    event_id: UUID,
    facts: tuple[CurrentFactV01, ...],
    status: EventPhase,
    effective_at: datetime | None,
) -> SemanticFactStateV01:
    ordered = tuple(sorted(facts, key=lambda row: row.fact_id))
    return SemanticFactStateV01(
        event_id=event_id,
        facts=ordered,
        status=status,
        effective_at=effective_at,
        state_digest=fact_state_digest(
            event_id=event_id,
            facts=ordered,
            status=status,
            effective_at=effective_at,
        ),
    )


class FactSupersessionV01(BaseModel):
    previous_fact_id: str
    new_fact_id: str
    reason: str = Field(min_length=1, max_length=1000)


class FactDeltaV01(BaseModel):
    contract: str = FACT_DELTA_CONTRACT
    kind: FactDeltaKind
    add_facts: tuple[CurrentFactV01, ...]
    retire_fact_ids: tuple[str, ...] = ()
    supersession_pairs: tuple[FactSupersessionV01, ...] = ()
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def normalize_and_validate(self):
        retire = tuple(sorted({str(v).strip() for v in self.retire_fact_ids if str(v).strip()}))
        object.__setattr__(self, "retire_fact_ids", retire)
        if not self.add_facts:
            raise ValueError(f"{self.kind} requires at least one add_fact")
        if self.kind == "SUPERSEDE":
            if not retire or not self.supersession_pairs:
                raise ValueError("SUPERSEDE requires retired fact(s) and supersession pair(s)")
        elif self.supersession_pairs:
            raise ValueError("supersession_pairs are only legal for SUPERSEDE")
        if self.kind == "CONTEST" and retire:
            raise ValueError("CONTEST may not retire previous live facts")
        return self


class DraftFactV01(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    support_keys: tuple[str, ...] = Field(min_length=1)


class DraftFactSupersessionV01(BaseModel):
    previous_fact_key: str
    new_fact_index: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)


class FactDeltaDraftV01(BaseModel):
    contract: str = FACT_DECIDER_CONTRACT
    kind: FactDraftKind
    add_facts: tuple[DraftFactV01, ...] = ()
    retire_fact_keys: tuple[str, ...] = ()
    supersession_pairs: tuple[DraftFactSupersessionV01, ...] = ()
    phase_change: EventPhase | None = None
    rationale: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_draft(self):
        if self.contract != FACT_DECIDER_CONTRACT:
            raise ValueError(f"contract must be {FACT_DECIDER_CONTRACT}")
        if self.kind == "NONE":
            if self.add_facts or self.retire_fact_keys or self.supersession_pairs or self.phase_change:
                raise ValueError("NONE may not carry state mutations")
            return self
        if not self.add_facts:
            raise ValueError(f"{self.kind} requires add_facts")
        if self.kind == "SUPERSEDE":
            if not self.retire_fact_keys or not self.supersession_pairs:
                raise ValueError("SUPERSEDE requires retire_fact_keys and supersession_pairs")
        elif self.supersession_pairs:
            raise ValueError("supersession_pairs are only legal for SUPERSEDE")
        if self.kind == "CONTEST" and self.retire_fact_keys:
            raise ValueError("CONTEST may not retire previous live facts")
        return self


class FactApplyResultV01(BaseModel):
    contract: str = FACT_APPLIER_CONTRACT
    delta_kind: FactDeltaKind | None
    previous_fact_state_digest: str | None
    observation_key: str
    fact_state: SemanticFactStateV01
    event_state: EventStateV02
_DECIDE_SYSTEM = """You are the RAOS Event Aggregate Decide function.

The immutable evidence history is NOT the current state.
The current state is a small set of derived CURRENT FACTS, each grounded by audited support.
The supplied Event Identity defines the coarse Event boundary. Judge materiality relative to that Event, not relative to the Source in isolation.

Given Event Identity, previous current facts, and NEW audited semantic units, return exactly one JSON object:
{
  "contract": "event-state-fact-decider-v0.4",
  "kind": "NONE | ADD | SUPERSEDE | CONTEST",
  "add_facts": [
    {
      "text": "one concise derived current fact",
      "support_keys": ["P001", "N001"]
    }
  ],
  "retire_fact_keys": ["F001"],
  "supersession_pairs": [
    {
      "previous_fact_key": "F001",
      "new_fact_index": 0,
      "reason": "explicit replacement reason"
    }
  ],
  "phase_change": "EMERGING | ACTIVE | CONTESTED | RESOLVED | null",
  "rationale": "brief explanation"
}

Rules:
- NONE: new evidence does not materially change the current semantic state.
- ADD: add compatible current information.
- SUPERSEDE: explicit correction/retraction/replacement of an existing current fact.
- CONTEST: unresolved incompatibility with an existing current fact.
- A later different demo/example/use case is not supersession.
- Current facts are NOT a chronology, NOT one fact per Source, and NOT a lossless summary of the latest Source.
- MATERIALITY GATE: add or update a current fact only when omitting that fact would materially change a competent observer's understanding of the supplied coarse Event's CURRENT state. "New and true" is not enough.
- Use Event Identity as the scope boundary. Details that are true of a Source but do not materially change this Event's launch/lifecycle, core claims/capabilities, validation state, major application/consequence, correction, or unresolved conflict normally stay in History. These are decision criteria, not a fixed fact schema.
- Prefer the minimum state-changing fact set. A single observation may contain many audited semantic units but produce zero, one, or only a few current-fact changes.
- add_facts contains ONLY facts created or materially updated because of the new observation. Unchanged previous current facts are implicitly retained by Apply and MUST NOT be re-emitted in add_facts.
- Peripheral source reactions, author excitement, popularity/viral commentary, link/video existence, presentation mechanics, generic speculation, incidental hardware/context, and promised future content normally remain in immutable History rather than Current State, unless they themselves materially change what the Event currently is.
- Lower-level elaboration of an already represented material fact should not become a separate current fact unless it materially changes the current interpretation; otherwise use NONE or merge into the existing fact.
- When new evidence broadens or subsumes one or more narrow current facts, prefer one broader derived fact and retire the narrower fact(s).
- When previous and new evidence are additional instances of the same capability, property, behavior, or semantic dimension, do NOT keep one current fact per instance unless those individual instances are independently decision-relevant. Replace the narrow current fact with one broader fact grounded by the minimal prior + new support needed to justify the broader statement.
- Under ADD, retiring a narrower fact because a broader fact subsumes it is projection compaction, NOT supersession. Put the narrow F-key in retire_fact_keys and keep supersession_pairs empty.
- ADD retirement is lossless with respect to current meaning: at least one added broader fact must carry ALL support_keys of each retired fact plus at least one N-key from the new observation. Never retire a broader fact and replace it with a narrower new example.
- Example pattern: current fact "system has one live game demo" + new evidence "another live game demo" -> ADD one broader fact "system has multiple live game demos", use old+new support, retire the narrow old fact.
- Mere suggested/possible future applications normally remain in History; an actually demonstrated/deployed application may change Current State.
- Incidental demo hardware or presentation medium normally remains in History and should not become a standalone Current Fact unless the Event scope is specifically about hardware compatibility/performance or that detail materially changes the Event.
- Every new derived fact must use at least one N-key from the new observation.
- support_keys must be the minimal audited grounding needed for that current fact; P-keys may be reused when merging prior meaning with new evidence.
- F-keys identify previous current facts. Retiring a fact removes it only from Current State, never from immutable History.
- CONTEST keeps the existing live fact and adds the incompatible new fact.
- phase_change is normally null. RESOLVED means the Event episode itself is explicitly concluded/closed or reaches a terminal outcome; correcting or replacing one ordinary fact does NOT resolve the Event.
- Do not invent facts, support keys, confidence scores, or extra relation types.
"""


def _support_aliases(
    previous_support_refs: set[str],
    new_refs: set[str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    prev = {ref: f"P{i:03d}" for i, ref in enumerate(sorted(previous_support_refs), 1)}
    new = {ref: f"N{i:03d}" for i, ref in enumerate(sorted(new_refs), 1)}
    reverse = {**{v: k for k, v in prev.items()}, **{v: k for k, v in new.items()}}
    return reverse, prev, new
def _fact_aliases(
    previous: SemanticFactStateV01 | None,
) -> tuple[dict[str, str], dict[str, str]]:
    if previous is None:
        return {}, {}
    fact_key_by_id = {
        row.fact_id: f"F{i:03d}"
        for i, row in enumerate(sorted(previous.facts, key=lambda fact: fact.fact_id), 1)
    }
    fact_id_by_key = {key: fact_id for fact_id, key in fact_key_by_id.items()}
    return fact_id_by_key, fact_key_by_id


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


def _new_fact_id(
    *,
    event_id: UUID,
    observation_key: str,
    ordinal: int,
    text: str,
    support_refs: tuple[str, ...],
) -> str:
    return _stable_digest(
        {
            "event_id": str(event_id),
            "observation_key": observation_key,
            "ordinal": ordinal,
            "text": " ".join(text.split()),
            "support_refs": list(sorted(support_refs)),
        }
    )


def decide_fact_delta(
    *,
    event_identity: dict,
    previous: SemanticFactStateV01 | None,
    observation: EventObservationV01,
    previous_support_units: list[dict],
    new_semantic_units: list[dict],
    chat_fn,
) -> FactDeltaV01 | None:
    previous_support_refs = {
        ref
        for fact in (previous.facts if previous is not None else ())
        for ref in fact.support_refs
    }
    hydrated = {
        str(row.get("unit_id") or "").strip()
        for row in previous_support_units
        if str(row.get("unit_id") or "").strip()
    }
    if hydrated != previous_support_refs:
        raise ValueError("Fact Decide previous support hydration must exactly match current fact support")

    new_refs = set(observation.audited_semantic_unit_refs)
    ref_by_key, prev_key_by_ref, new_key_by_ref = _support_aliases(
        previous_support_refs, new_refs
    )
    fact_id_by_key, fact_key_by_id = _fact_aliases(previous)
    previous_facts_payload = []
    if previous is not None:
        for fact in sorted(previous.facts, key=lambda row: row.fact_id):
            previous_facts_payload.append(
                {
                    "fact_key": fact_key_by_id[fact.fact_id],
                    "text": fact.text,
                    "support_keys": [prev_key_by_ref[ref] for ref in fact.support_refs],
                }
            )

    payload = {
        "contract": FACT_DECIDER_CONTRACT,
        "event_identity": dict(event_identity),
        "previous_status": previous.status if previous is not None else None,
        "previous_facts": previous_facts_payload,
        "previous_support_units": _units_with_keys(previous_support_units, prev_key_by_ref),
        "new_semantic_units": _units_with_keys(new_semantic_units, new_key_by_ref),
        "allowed_support_keys": sorted(ref_by_key),
        "allowed_previous_fact_keys": sorted(fact_id_by_key),
    }
    messages = [
        {"role": "system", "content": _DECIDE_SYSTEM},
        {
            "role": "user",
            "content": "Decide the minimal current-fact delta.\n\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
        },
    ]
    obj, _meta, _validation_events = chat_json_schema(
        messages,
        FactDeltaDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = FactDeltaDraftV01.model_validate(obj)
    if draft.kind == "NONE":
        if previous is None:
            raise ValueError("First Event observation cannot produce NONE")
        return None

    def resolve_support(key: str) -> str:
        ref = ref_by_key.get(key)
        if ref is None:
            raise ValueError(f"Fact Decide proposed unknown support key: {key}")
        return ref

    def resolve_fact(key: str) -> str:
        fact_id = fact_id_by_key.get(key)
        if fact_id is None:
            raise ValueError(f"Fact Decide proposed unknown previous fact key: {key}")
        return fact_id

    add_facts = []
    for idx, row in enumerate(draft.add_facts):
        supports = tuple(sorted({resolve_support(key) for key in row.support_keys}))
        if not (set(supports) & new_refs):
            raise ValueError(
                "Every added current fact must use new-observation support; "
                f"offending_text={row.text!r} support_keys={list(row.support_keys)!r}"
            )
        add_facts.append(
            CurrentFactV01(
                fact_id=_new_fact_id(
                    event_id=observation.event_id,
                    observation_key=observation.observation_key,
                    ordinal=idx,
                    text=row.text,
                    support_refs=supports,
                ),
                text=row.text,
                support_refs=supports,
            )
        )
    retire_ids = tuple(resolve_fact(key) for key in draft.retire_fact_keys)
    supersession_pairs = []
    for pair in draft.supersession_pairs:
        if pair.new_fact_index >= len(add_facts):
            raise ValueError("Fact supersession new_fact_index is out of range")
        supersession_pairs.append(
            FactSupersessionV01(
                previous_fact_id=resolve_fact(pair.previous_fact_key),
                new_fact_id=add_facts[pair.new_fact_index].fact_id,
                reason=pair.reason,
            )
        )

    delta = FactDeltaV01(
        kind=draft.kind,
        add_facts=tuple(add_facts),
        retire_fact_ids=retire_ids,
        supersession_pairs=tuple(supersession_pairs),
        phase_change=draft.phase_change,
        rationale=draft.rationale,
    )
    _validate_fact_delta(
        previous=previous,
        observation=observation,
        delta=delta,
    )
    return delta


def _validate_fact_delta(
    *,
    previous: SemanticFactStateV01 | None,
    observation: EventObservationV01,
    delta: FactDeltaV01,
) -> None:
    previous_by_id = {
        row.fact_id: row for row in (previous.facts if previous is not None else ())
    }
    previous_ids = set(previous_by_id)
    previous_support_refs = {
        ref
        for fact in (previous.facts if previous is not None else ())
        for ref in fact.support_refs
    }
    new_refs = set(observation.audited_semantic_unit_refs)
    allowed_support = previous_support_refs | new_refs
    retire = set(delta.retire_fact_ids)
    if not retire <= previous_ids:
        raise ValueError("FactDelta retire_fact_ids must refer to current facts")
    if previous is None and delta.kind != "ADD":
        raise ValueError("First semantic fact transition must be ADD")
    for fact in delta.add_facts:
        support = set(fact.support_refs)
        if not support <= allowed_support:
            raise ValueError("FactDelta added fact contains unsupported semantic refs")
        if not (support & new_refs):
            raise ValueError("Every added current fact must use new-observation support")
    if delta.kind == "ADD" and retire:
        added_support_sets = [set(row.support_refs) for row in delta.add_facts]
        for retired_id in sorted(retire):
            retired_support = set(previous_by_id[retired_id].support_refs)
            if not any(retired_support <= support for support in added_support_sets):
                retired_fact = previous_by_id[retired_id]
                raise ValueError(
                    "ADD retirement must preserve all support of each retired fact "
                    "inside at least one added broader fact; "
                    f"retired_fact={retired_fact.model_dump(mode='json')!r} "
                    f"added_facts={[row.model_dump(mode='json') for row in delta.add_facts]!r} "
                    f"rationale={delta.rationale!r}"
                )

    if delta.kind == "SUPERSEDE":
        new_ids = {row.fact_id for row in delta.add_facts}
        for pair in delta.supersession_pairs:
            if pair.previous_fact_id not in retire:
                raise ValueError("SUPERSEDE previous fact must be retired")
            if pair.new_fact_id not in new_ids:
                raise ValueError("SUPERSEDE new fact must be added")
    if delta.kind == "CONTEST":
        if not previous_ids:
            raise ValueError("CONTEST requires a previous current fact")
        if delta.phase_change not in {None, "CONTESTED"}:
            raise ValueError("CONTEST phase_change must be CONTESTED or null")
    elif delta.phase_change == "CONTESTED":
        raise ValueError("Only CONTEST may enter CONTESTED phase")


def _next_phase(
    previous: SemanticFactStateV01 | None,
    delta: FactDeltaV01 | None,
) -> EventPhase:
    if delta is None:
        if previous is None:
            raise ValueError("NONE requires previous fact state")
        return previous.status
    if previous is None:
        return "EMERGING"
    if delta.kind == "CONTEST":
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
    fact_state: SemanticFactStateV01,
    observation: EventObservationV01,
    supporting_source_ids,
) -> EventStateV02:
    facts = tuple(sorted(fact_state.facts, key=lambda row: row.fact_id))
    active_refs = tuple(
        sorted({ref for fact in facts for ref in fact.support_refs})
    )
    synopsis = _bounded(" ".join(fact.text for fact in facts))
    evidence_state = structural_evidence_state_v02(
        db,
        fact_state.event_id,
        active_semantic_unit_refs=active_refs,
        supporting_source_ids=supporting_source_ids,
    )
    return make_event_state_v02(
        event_id=fact_state.event_id,
        world_state=WorldStateV02(
            synopsis=synopsis,
            status=fact_state.status,
            effective_at=fact_state.effective_at,
            active_semantic_unit_refs=active_refs,
        ),
        evidence_state=evidence_state,
    )
def apply_fact_delta(
    db: Session,
    *,
    event_id: UUID,
    previous: SemanticFactStateV01 | None,
    observation: EventObservationV01,
    delta: FactDeltaV01 | None,
    supporting_source_ids,
) -> FactApplyResultV01:
    if observation.event_id != event_id:
        raise ValueError("Observation Event id does not match Fact Apply Event id")
    if previous is not None and previous.event_id != event_id:
        raise ValueError("Previous semantic fact state belongs to another Event")

    if delta is None:
        if previous is None:
            raise ValueError("First observation requires a material fact delta")
        next_fact_state = previous
    else:
        _validate_fact_delta(
            previous=previous,
            observation=observation,
            delta=delta,
        )
        previous_by_id = {
            row.fact_id: row for row in (previous.facts if previous is not None else ())
        }
        for fact_id in delta.retire_fact_ids:
            previous_by_id.pop(fact_id, None)
        for fact in delta.add_facts:
            previous_by_id[fact.fact_id] = fact
        facts = tuple(sorted(previous_by_id.values(), key=lambda row: row.fact_id))
        if not facts:
            raise ValueError("Fact Apply may not materialize an empty current fact set")
        next_fact_state = make_fact_state(
            event_id=event_id,
            facts=facts,
            status=_next_phase(previous, delta),
            effective_at=observation.world_time or observation.evidence_time,
        )
    event_state = _materialize_event_state(
        db,
        fact_state=next_fact_state,
        observation=observation,
        supporting_source_ids=supporting_source_ids,
    )
    return FactApplyResultV01(
        delta_kind=(delta.kind if delta is not None else None),
        previous_fact_state_digest=(
            previous.state_digest if previous is not None else None
        ),
        observation_key=observation.observation_key,
        fact_state=next_fact_state,
        event_state=event_state,
    )
