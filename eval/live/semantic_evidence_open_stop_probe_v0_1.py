"""Semantic Sensor open-stop upper-bound probe v0.1.

Development-only diagnostic derived from v0.2.3. It removes the numeric semantic
unit stopping target/cap while preserving source grounding, temporal anchoring,
epistemic discipline, provenance rules, and the v0.2 batch field family.

This is NOT a production Sensor version and NOT fresh validation evidence.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from eval.live.semantic_evidence_batch_v0_2 import NonEventSemanticUnitV0_2
from eval.live.semantic_evidence_frame_v0_1 import SemanticEvidenceFrameV0_1
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource
from eval.live.semantic_evidence_extractor_v0_2_2 import (
    _json_safe,
    _validation_errors,
    _validate_source_binding,
)

PROBE_VERSION = "semantic-evidence-open-stop-probe-v0.1"
PROMPT_VERSION = "semantic-evidence-open-stop-v0.1"
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 120.0
MAX_TOKENS = 16384
MAX_SUPPORTS_PER_NON_EVENT_UNIT = 4


class SemanticExtractionOpenStopBatchV0_1(BaseModel):
    """Same semantic batch family as v0.2, but no non-event unit-count ceiling."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interface_version: Literal["semantic-evidence-batch-v0.2"] = "semantic-evidence-batch-v0.2"
    batch_id: str = Field(min_length=1, max_length=300)
    source_ids: list[str] = Field(min_length=1, max_length=100)
    event_frames: list[SemanticEvidenceFrameV0_1] = Field(default_factory=list, max_length=8)
    non_event_units: list[NonEventSemanticUnitV0_2] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_batch(self):
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("duplicate source_id in batch")
        event_ids = [frame.event.event_id for frame in self.event_frames]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate event_id across event_frames")
        unit_ids = [unit.unit_id for unit in self.non_event_units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("duplicate unit_id across non_event_units")
        allowed = set(self.source_ids)
        for frame in self.event_frames:
            for source in frame.sources:
                if source.source_id not in allowed:
                    raise ValueError("event frame references source outside batch")
        for unit in self.non_event_units:
            for support in unit.supports:
                if support.source_id not in allowed:
                    raise ValueError("non-event support references source outside batch")
                if len(unit.supports) > MAX_SUPPORTS_PER_NON_EVENT_UNIT:
                    raise ValueError(
                        f"open-stop probe keeps provenance cap {MAX_SUPPORTS_PER_NON_EVENT_UNIT}; "
                        f"{unit.unit_id} has {len(unit.supports)} supports"
                    )
        return self


OPEN_STOP_OUTPUT_CONTRACT = r'''Return the same SemanticExtractionBatchV0_2 field family:
{
  "interface_version": "semantic-evidence-batch-v0.2",
  "batch_id": "<source_id>-semantic-batch-v0.2",
  "source_ids": ["<source_id>"],
  "event_frames": [...],
  "non_event_units": [...],
  "notes": []
}

Each non_event_units item:
{
  "unit_id": "...",
  "statement": "one compact independent source-grounded semantic claim/cluster",
  "epistemic_status": "SOURCE_CLAIM" | "DIRECT_OBSERVATION" | "EXTRACTOR_INFERENCE",
  "confidence": "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN",
  "supports": [
    {
      "source_id": "<source_id>",
      "support_pointer": "PARA 0001 or PAGE 0001",
      "support_excerpt": "smallest source excerpt sufficient to audit this semantic unit"
    }
  ],
  "note": ""
}
Use at most 4 supports per non-event unit; normally 1-2 should suffice.

Each event_frames item must match SemanticEvidenceFrameV0_1 exactly, including event,
sources, evidence, substantive_actors_objects, actions_changes,
affected_systems_populations, temporal_context, and uncertainties.

OPEN SEMANTIC STOPPING RULE:
- There is NO target number of semantic units.
- Create as many independent semantic units as necessary, but no more.
- Do not stop because you have produced a convenient round number.
- Before stopping, scan the whole source conceptually and ask whether any remaining
  passage contains an independent event, claim, method, mechanism, causal relation,
  quantitative conclusion, condition/caveat, attribution, temporal state, or uncertainty
  not already represented.
- Stop only when every remaining substantive passage is either:
  (1) already subsumed by an existing semantic unit,
  (2) evidence/example/measurement for an existing unit, or
  (3) metadata/page chrome/background without independent semantic meaning.
- Merge multiple observations into one higher-level semantic unit when they jointly
  establish one general principle. Keep the observations as provenance.
- Do not create one unit per paragraph, benchmark value, example, implementation detail,
  or repeated explanation.
'''

SYSTEM_PROMPT = """You are the Semantic Sensor Front-End for Research Attention OS (RAOS).

Perform source-grounded semantic extraction using MINIMAL SUFFICIENT REPRESENTATION.
Your goal is the smallest complete semantic basis of the source, not a structured rewrite.

Hard boundaries:
- Never output D, S, P, Delta, AWARE, DROP, WATCH, ENGAGE, user relevance, or importance.
- Never use outside knowledge to fill gaps or correct the source.
- Never turn missing information into absence/zero.
- Never turn a quote, prediction, opinion, marketing statement, or interview claim into
  an unattributed world fact.

Semantic Independence Test:
Create a separate unit only if removing it would lose an independent meaning that cannot
be reconstructed from the remaining units without changing truth-conditional meaning,
actor attribution, causal relation, method/mechanism, quantitative conclusion, temporal
status, scope/condition, or uncertainty.
If deleting a candidate unit does not remove an independent meaning, merge it.

Hierarchical abstraction:
Prefer a higher-level source-grounded principle when several observations/examples are
instances or measurements of the same principle. Preserve the examples as provenance;
do not spend separate semantic units on them unless they carry genuinely independent
meaning.

Open stopping:
There is no desired unit count. Continue until semantic coverage is complete, then stop.
Do not fill an implicit budget and do not optimize for brevity at the cost of omission.

Provenance:
- Every support pointer must use a visible PARA/PAGE marker.
- Every semantic object must be supported by the evidence it cites.
- Use the fewest supports necessary; at most 4 per non-event unit.
- Quote the smallest excerpt sufficient for audit.
- Evidence preservation is not source duplication.

Epistemic status and confidence retain the v0.2.3 meanings. Confidence is support/
attribution confidence, not outside-world truth probability.

Temporal anchoring is unchanged: measurement_as_of is not publication time; preserve
source-relative time unless the source itself or pinned metadata supports an absolute time.

Return JSON only.
"""

USER_PROMPT_TEMPLATE = """Measurement metadata:
measurement_as_of: {as_of}

Pinned source metadata:
source_id: {source_id}
locator: {locator}
media_type: {media_type}
git_blob_sha: {git_blob_sha}
source_published_at: {published_at}
source_updated_at: {updated_at}
source_captured_at: {captured_at}

{output_contract}

Raw source snapshot with stable support markers:
--- SOURCE BEGIN ---
{source_text}
--- SOURCE END ---

Return one batch. Use batch_id = "{source_id}-semantic-batch-v0.2" and source_ids = ["{source_id}"].
For event frames, event.as_of and temporal_context.as_of must equal "{as_of}"; preserve
pinned source identity exactly. Do not output your internal coverage/stopping check.
"""


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE + "\n---\n" + OPEN_STOP_OUTPUT_CONTRACT
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_messages(source: LoadedSemanticSource, *, as_of: str) -> list[dict[str, str]]:
    user = USER_PROMPT_TEMPLATE.format(
        as_of=str(as_of).strip(),
        source_id=source.source_id,
        locator=source.path,
        media_type=source.media_type,
        git_blob_sha=source.git_blob_sha,
        published_at=source.published_at,
        updated_at=source.updated_at,
        captured_at=source.captured_at,
        output_contract=OPEN_STOP_OUTPUT_CONTRACT,
        source_text=source.rendered_text,
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _validate_candidate(batch: SemanticExtractionOpenStopBatchV0_1, source: LoadedSemanticSource, *, as_of: str) -> None:
    # Reuse v0.2 source-binding semantics via a shape-compatible validated batch dump.
    from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
    if len(batch.non_event_units) <= 20:
        compat = SemanticExtractionBatchV0_2.model_validate(batch.model_dump(mode="json"))
        _validate_source_binding(compat, source, as_of=as_of)
    else:
        if batch.source_ids != [source.source_id]:
            raise ValueError("batch source binding mismatch")
        for frame in batch.event_frames:
            if frame.event.as_of != as_of or frame.temporal_context.as_of != as_of:
                raise ValueError("event/temporal as_of mismatch")
            if len(frame.sources) != 1:
                raise ValueError("single-source probe requires one source record per event frame")
            bound = frame.sources[0]
            if bound.source_id != source.source_id or bound.source_type != source.media_type or bound.locator != source.path:
                raise ValueError("event source binding mismatch")
        for unit in batch.non_event_units:
            for support in unit.supports:
                if support.source_id != source.source_id:
                    raise ValueError("non-event support source binding mismatch")


def estimate_open_stop(source: LoadedSemanticSource, *, as_of: str, chat_fn) -> dict[str, Any]:
    from app.cognitive.client import LLMError

    messages = build_messages(source, as_of=as_of)
    schema_events: list[dict[str, Any]] = []
    call_kw = {
        "model": None,
        "timeout": TIMEOUT_SECONDS,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "max_tokens": MAX_TOKENS,
    }
    try:
        parsed, meta = chat_fn(messages, **call_kw)
    except LLMError as exc:
        return {"scorable": False, "batch": None, "failure_kind": "model_call", "error": str(exc)[:2000], "repair_used": False, "schema_events": [], "invalid_raw": None, "model_meta": None}

    try:
        obj = SemanticExtractionOpenStopBatchV0_1.model_validate(parsed)
        _validate_candidate(obj, source, as_of=as_of)
        meta = dict(meta or {})
        meta["schema_repaired"] = False
        return {"scorable": True, "batch": obj.model_dump(mode="json"), "failure_kind": None, "error": None, "repair_used": False, "schema_events": [], "invalid_raw": None, "model_meta": meta}
    except (ValidationError, ValueError) as exc:
        schema_events.append({"retry": 0, "status": "invalid", "errors": _validation_errors(exc)})

    return {"scorable": False, "batch": None, "failure_kind": "schema_validation", "error": "open-stop probe invalid on first pass; no repair to preserve diagnostic purity", "repair_used": False, "schema_events": schema_events, "invalid_raw": _json_safe(parsed), "model_meta": meta}


def invocation_record(*, requested_model: str | None, provider_base_url: str | None) -> dict[str, Any]:
    return {
        "probe_version": PROBE_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": 0.1,
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "response_format": "json_object",
        "structured_schema": "SemanticExtractionOpenStopBatchV0_1",
        "semantic_stopping": "coverage-complete-open-stop",
        "max_tokens": MAX_TOKENS,
        "max_supports_per_non_event_unit": MAX_SUPPORTS_PER_NON_EVENT_UNIT,
    }
