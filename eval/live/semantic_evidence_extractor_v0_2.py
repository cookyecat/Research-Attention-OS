"""Semantic Evidence Extractor v0.2 — development-only sensor front-end.

Revision after RS02/RS09 v0.1 attribution:
- supplies an explicit compact output contract on the first call;
- uses SemanticExtractionBatchV0_2 with multi-support non-event units;
- preserves schema errors/raw repaired output/model metadata on failure.

No D/S/P labels, Attention Actions, user relevance, or importance judgments.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import ValidationError

from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource

EXTRACTOR_VERSION = "semantic-evidence-extractor-v0.2"
PROMPT_VERSION = "semantic-evidence-extraction-v0.2"
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 90.0
TEMPERATURE = 0.1

COMPACT_OUTPUT_CONTRACT = r'''Required top-level shape:
{
  "interface_version": "semantic-evidence-batch-v0.2",
  "batch_id": "<source_id>-semantic-batch-v0.2",
  "source_ids": ["<source_id>"],
  "event_frames": [ ... max 8 SemanticEvidenceFrameV0_1 objects ... ],
  "non_event_units": [ ... max 20 objects ... ],
  "notes": []
}

Each non_event_units item MUST be exactly:
{
  "unit_id": "...",
  "statement": "source-grounded semantic statement",
  "epistemic_status": "SOURCE_CLAIM" | "DIRECT_OBSERVATION" | "EXTRACTOR_INFERENCE",
  "confidence": "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN",
  "supports": [
    {
      "source_id": "<source_id>",
      "support_pointer": "PARA 0001 or PAGE 0001",
      "support_excerpt": "short non-empty diagnostic excerpt from that location"
    }
  ],
  "note": ""
}
Use 1..8 supports per non-event unit. Aggregate several source passages into one semantic unit when they support the same higher-level source-grounded point.

Each event_frames item MUST match SemanticEvidenceFrameV0_1 exactly:
{
  "interface_version": "semantic-evidence-frame-v0.1",
  "event": {"event_id":"...", "as_of":"<measurement as_of>", "summary":"..."},
  "sources": [{"source_id":"<source_id>", "source_type":"<media_type>", "published_at":"unknown-or-supported", "locator":"<pinned path>"}],
  "evidence": [{"evidence_id":"...", "source_id":"<source_id>", "support_pointer":"PARA/PAGE ...", "support_excerpt":"short excerpt", "epistemic_status":"SOURCE_CLAIM|DIRECT_OBSERVATION|EXTRACTOR_INFERENCE", "confidence":"HIGH|MEDIUM|LOW|UNKNOWN"}],
  "substantive_actors_objects": [{"name":"...", "role":"...", "substantive_basis":"...", "support_ids":["evidence-id"]}],
  "actions_changes": [{"description":"...", "temporal_status":"PROPOSED|ANNOUNCED|ENACTED|EFFECTIVE|OBSERVED|HISTORICAL|UNKNOWN", "support_ids":["evidence-id"]}],
  "affected_systems_populations": [{"description":"...", "reference_scope":"...", "support_ids":["evidence-id"]}],
  "temporal_context": {"event_time":"unknown-or-supported", "effective_time":"unknown-or-supported", "as_of":"<measurement as_of>", "notes":""},
  "uncertainties": [{"field":"...", "kind":"UNKNOWN|CONFLICTING_SOURCES|UNCERTAIN_SCOPE|UNCERTAIN_ACTOR_ROLE|INSUFFICIENT_SUPPORT", "note":"...", "support_ids":[]}]
}
'''

SYSTEM_PROMPT = """You are the Semantic Sensor Front-End for Research Attention OS (RAOS).

Perform source-grounded semantic extraction only. Preserve provenance, attribution,
uncertainty, temporal status, and the distinction between concrete event/result/change
units and non-event epistemic content.

Hard boundaries:
- Never output D, S, P, AWARE, DROP, WATCH, ENGAGE, user relevance, or importance.
- Never use outside knowledge to fill gaps or correct the supplied source.
- Never turn missing information into absence/zero.
- Never turn a quote, prediction, marketing statement, interview opinion, or discussion
  comment into an unattributed world fact.

A raw source may yield zero, one, or multiple event frames. Tutorials, opinions,
preferences, methodological advice, and discussion patterns should normally be
non-event semantic units unless there is a concrete event/result/change to represent.

Epistemic status:
- SOURCE_CLAIM: asserted/reported/quoted by the source or a speaker/author.
- DIRECT_OBSERVATION: direct raw observation/measurement present in the supplied material.
- EXTRACTOR_INFERENCE: your semantic inference from supported content; use sparingly.

Confidence means confidence that the extraction/attribution is supported by the supplied
source. It does NOT mean confidence that the source's claim is true in the outside world.

Compression rules:
- Prefer a small set of high-value semantic units, not sentence/comment transcription.
- event_frames <= 8.
- non_event_units <= 20.
- One non-event unit may cite multiple source supports when several passages/comments
  support the same semantic point.

Provenance:
- Every support pointer must use a visible PARA/PAGE marker from the supplied source.
- Every non-event support excerpt must be short and non-empty.
- Event-frame semantic objects must reference valid event-frame evidence ids.

Return JSON only and obey the compact output contract supplied in the user message.
"""

USER_PROMPT_TEMPLATE = """Measurement as_of: {as_of}

Pinned source metadata:
source_id: {source_id}
locator: {locator}
media_type: {media_type}
git_blob_sha: {git_blob_sha}

{output_contract}

Raw source snapshot with stable support markers:
--- SOURCE BEGIN ---
{source_text}
--- SOURCE END ---

Return one SemanticExtractionBatchV0_2. Use batch_id = "{source_id}-semantic-batch-v0.2" and source_ids = ["{source_id}"].
For event frames, event.as_of and temporal_context.as_of must equal "{as_of}" and the single source record must preserve the pinned source_id/media_type/locator exactly.
"""


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE + "\n---\n" + COMPACT_OUTPUT_CONTRACT
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_messages(source: LoadedSemanticSource, *, as_of: str) -> list[dict[str, str]]:
    if not str(as_of or "").strip():
        raise ValueError("as_of is required")
    user = USER_PROMPT_TEMPLATE.format(
        as_of=str(as_of).strip(),
        source_id=source.source_id,
        locator=source.path,
        media_type=source.media_type,
        git_blob_sha=source.git_blob_sha,
        output_contract=COMPACT_OUTPUT_CONTRACT,
        source_text=source.rendered_text,
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _validate_source_binding(batch: SemanticExtractionBatchV0_2, source: LoadedSemanticSource, *, as_of: str) -> None:
    if batch.source_ids != [source.source_id]:
        raise ValueError(f"batch source_ids must equal [{source.source_id!r}], got {batch.source_ids!r}")
    for frame in batch.event_frames:
        if frame.event.as_of != as_of or frame.temporal_context.as_of != as_of:
            raise ValueError("event/temporal as_of does not match measurement as_of")
        if len(frame.sources) != 1:
            raise ValueError("each single-source event frame must contain exactly one source record")
        bound = frame.sources[0]
        if bound.source_id != source.source_id or bound.source_type != source.media_type or bound.locator != source.path:
            raise ValueError("event frame source binding does not match pinned source")
    for unit in batch.non_event_units:
        for support in unit.supports:
            if support.source_id != source.source_id:
                raise ValueError("non-event support source_id does not match pinned source")


def estimate_semantic_evidence_v0_2(source: LoadedSemanticSource, *, as_of: str, chat_fn=None) -> dict[str, Any]:
    """Run one development extraction with one structural repair and full diagnostics."""
    from app.cognitive.client import LLMError, chat_json, merge_usage_meta

    fn = chat_fn or chat_json
    call_kw = {
        "model": None,
        "timeout": TIMEOUT_SECONDS,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
    }
    messages = build_messages(source, as_of=as_of)
    schema_events: list[dict[str, Any]] = []

    try:
        parsed, meta = fn(messages, **call_kw)
    except LLMError as exc:
        return {"scorable": False, "batch": None, "failure_kind": "model_call", "error": str(exc)[:2000], "repair_used": False, "schema_events": [], "invalid_raw": None, "model_meta": None}

    try:
        obj = SemanticExtractionBatchV0_2.model_validate(parsed)
        _validate_source_binding(obj, source, as_of=as_of)
        meta = dict(meta or {})
        meta["schema_repaired"] = False
        return {"scorable": True, "batch": obj.model_dump(mode="json"), "failure_kind": None, "error": None, "repair_used": False, "schema_events": [], "invalid_raw": None, "model_meta": meta}
    except (ValidationError, ValueError) as exc:
        errors = exc.errors(include_url=False) if isinstance(exc, ValidationError) else [{"type":"source_binding", "msg":str(exc)}]
        schema_events.append({"retry": 0, "status": "invalid", "errors": errors})

    repair_messages = list(messages) + [
        {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)[:16000]},
        {"role": "user", "content": "Your JSON failed the required contract. Correct structural/provenance errors only; do not invent unsupported evidence.\nErrors:\n" + json.dumps(schema_events[-1]["errors"], ensure_ascii=False) + "\nReturn corrected JSON only.\n\n" + COMPACT_OUTPUT_CONTRACT},
    ]
    try:
        parsed2, meta2 = fn(repair_messages, **call_kw)
        meta = merge_usage_meta(meta, meta2)
    except LLMError as exc:
        return {"scorable": False, "batch": None, "failure_kind": "model_call_after_schema_failure", "error": str(exc)[:2000], "repair_used": True, "schema_events": schema_events, "invalid_raw": parsed, "model_meta": dict(meta or {})}

    try:
        obj = SemanticExtractionBatchV0_2.model_validate(parsed2)
        _validate_source_binding(obj, source, as_of=as_of)
        schema_events.append({"retry": 1, "status": "repaired"})
        meta["schema_repaired"] = True
        return {"scorable": True, "batch": obj.model_dump(mode="json"), "failure_kind": None, "error": None, "repair_used": True, "schema_events": schema_events, "invalid_raw": None, "model_meta": meta}
    except (ValidationError, ValueError) as exc2:
        errors2 = exc2.errors(include_url=False) if isinstance(exc2, ValidationError) else [{"type":"source_binding", "msg":str(exc2)}]
        schema_events.append({"retry": 1, "status": "invalid", "errors": errors2})
        return {"scorable": False, "batch": None, "failure_kind": "schema_validation", "error": "SemanticExtractionBatchV0_2 invalid after repair", "repair_used": True, "schema_events": schema_events, "invalid_raw": parsed2, "model_meta": meta}


def invocation_record(*, requested_model: str | None, provider_base_url: str | None) -> dict[str, Any]:
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": TEMPERATURE,
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "response_format": "json_object",
        "structured_schema": "SemanticExtractionBatchV0_2",
    }
