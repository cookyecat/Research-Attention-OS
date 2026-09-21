from __future__ import annotations

import json
from typing import Literal
from pydantic import BaseModel, Field, model_validator

from app.cognitive.client import chat_json_schema


BENCHMARK_EVENT_GOLD_PROJECTOR_CONTRACT = "benchmark-event-gold-semantic-projector-v0.2"

Decision = Literal["IN_EVENT", "OUT_OF_EVENT"]


class BenchmarkUnitSelectionV01(BaseModel):
    unit_id: str = Field(min_length=1)
    decision: Decision
    reason: str = Field(min_length=1, max_length=1200)


class BenchmarkEventGoldProjectionV01(BaseModel):
    contract: str = BENCHMARK_EVENT_GOLD_PROJECTOR_CONTRACT
    selections: tuple[BenchmarkUnitSelectionV01, ...]

    @property
    def projected_unit_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                row.unit_id
                for row in self.selections
                if row.decision == "IN_EVENT"
            )
        )


_SYSTEM = """You are an eval-only RAOS benchmark Event-Gold semantic projector.

The coarse Event identity is already frozen by benchmark gold. You are NOT resolving
Event identity and you are NOT creating facts.

Your only job is to classify EACH supplied audited semantic unit as:
- IN_EVENT: the unit materially describes, explains, evaluates, demonstrates, tests,
  validates, criticizes, or characterizes the frozen coarse Event/story.
- OUT_OF_EVENT: the unit is incidental metadata, generic tags, unrelated side-topic,
  channel/self-description, or another product/topic not materially part of the frozen Event.

Rules:
1. Every input unit_id must appear exactly once in selections.
2. You may only reference supplied unit_ids.
3. Do not invent or rewrite semantic content.
4. Because the Event is intentionally coarse, discussion, technical explanation,
   demonstrations, evaluations, and early validation of the same model/story may all be IN_EVENT.
5. Generic metadata or unrelated side products remain OUT_OF_EVENT even when the Source is about Jev.
6. Return JSON only and follow the schema exactly.
The output has only two top-level fields: contract and selections.
Do NOT add a projected_unit_ids summary; the deterministic caller derives it.
"""


def project_audited_units_to_benchmark_event(
    *,
    event_identity: dict,
    audited_semantic_units: list[dict],
    chat_fn,
) -> BenchmarkEventGoldProjectionV01:
    normalized = []
    ids = []
    for row in audited_semantic_units:
        if not isinstance(row, dict):
            continue
        unit_id = str(row.get("unit_id") or "").strip()
        statement = str(row.get("statement") or "").strip()
        if not unit_id or not statement:
            continue
        ids.append(unit_id)
        normalized.append(
            {
                "unit_id": unit_id,
                "statement": statement,
                "epistemic_status": row.get("epistemic_status"),
                "confidence": row.get("confidence"),
            }
        )

    if not normalized:
        return BenchmarkEventGoldProjectionV01(
            selections=(),
        )

    payload = {
        "contract": BENCHMARK_EVENT_GOLD_PROJECTOR_CONTRACT,
        "frozen_event_identity": event_identity,
        "audited_semantic_units": normalized,
        "required_unit_ids": sorted(ids),
    }

    obj, _meta, _events = chat_json_schema(
        [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": "Project the audited semantic units onto the frozen benchmark Event.\n\n"
                + json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        BenchmarkEventGoldProjectionV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    result = BenchmarkEventGoldProjectionV01.model_validate(obj)

    supplied = set(ids)
    selection_ids = [row.unit_id for row in result.selections]
    if len(selection_ids) != len(set(selection_ids)):
        raise ValueError("benchmark projector returned duplicate unit selections")
    if set(selection_ids) != supplied:
        missing = supplied - set(selection_ids)
        extra = set(selection_ids) - supplied
        raise ValueError(
            f"benchmark projector must classify every supplied unit exactly once; "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    return result
