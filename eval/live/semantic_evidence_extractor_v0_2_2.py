"""Semantic Evidence Extractor v0.2.2 — audit-discipline development revision.

Controlled revision over v0.2.1:
- keeps SemanticExtractionBatchV0_2 and all semantic structures unchanged;
- keeps the v0.2.1 temporal-anchor policy unchanged;
- strengthens evidence sufficiency, epistemic attribution, locator filtering,
  and event/non-event deduplication in the prompt contract.

No D/S/P labels, Attention Actions, user relevance, or importance judgments.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import ValidationError

from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
from eval.live.semantic_evidence_extractor_v0_2 import COMPACT_OUTPUT_CONTRACT
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource

EXTRACTOR_VERSION = "semantic-evidence-extractor-v0.2.2"
PROMPT_VERSION = "semantic-evidence-extraction-v0.2.2"
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 90.0
TEMPERATURE = 0.1

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
- Do not label your own inference as SOURCE_CLAIM. If wording such as 'presumably',
  'likely', 'apparently', or an unstated implication comes from you rather than the
  supplied source, either omit it or mark it EXTRACTOR_INFERENCE with adequate support.
- Unsupported speculation must be omitted.

Confidence means confidence that the extraction/attribution is supported by the supplied
source. It does NOT mean confidence that the source's claim is true in the outside world.

Compression rules:
- Prefer a small set of high-value semantic units, not sentence/comment transcription.
- event_frames <= 8.
- non_event_units <= 20.
- One non-event unit may cite multiple source supports when several passages/comments
  support the same semantic point.
- Avoid duplicating the same semantic payload across an Event Frame and a non-event unit.
  A non-event unit may coexist with an event only when it captures a genuinely distinct
  source-grounded principle, interpretation, method, belief, or abstraction rather than
  merely restating the event action/result.

Provenance and auditability — HARD INVARIANT:
- Every support pointer must use a visible PARA/PAGE marker from the supplied source.
- Every non-event support excerpt must be short and non-empty.
- Event-frame semantic objects must reference valid event-frame evidence ids.
- Traceability is not enough: each cited evidence item must actually be sufficient to
  support the specific semantic object that cites it.
- Do not rely on an uncited nearby paragraph merely because it appears in the same event.
- If a semantic object requires facts from multiple passages, create/cite all necessary
  evidence items. Example: if PARA 0004 supports a PR count but PARA 0005 is what supports
  that those PRs belong to the Cursor codebase, an affected-system object claiming
  'Cursor codebase' must cite evidence from PARA 0005, not only PARA 0004.
- Prefer the smallest sufficient evidence set; do not attach irrelevant evidence.

Locator / page-chrome filtering — HARD INVARIANT:
- Bare URLs, navigation labels, advertisements, share controls, reaction counts, page
  furniture, and source locators are metadata/page chrome, not epistemic units by default.
- A bare URL may be preserved as a locator/support location when useful, but do not create
  a non-event semantic unit merely because a URL appears.
- Never infer what a linked page/video 'presumably contains' from the URL alone.
- Only extract a claim about a linked resource when the supplied source text explicitly
  makes that claim.

Temporal anchoring — HARD INVARIANT:
- measurement_as_of is the time RAOS performs this extraction. It is NOT the source publication time and MUST NOT be used to resolve source-relative phrases such as today, yesterday, this month, last month, last week, recently, or just now.
- Use pinned source_published_at as a hard temporal anchor when it is known and applicable.
- source_updated_at and source_captured_at are distinct metadata. Do not silently substitute either one for publication/authoring time.
- An explicit date stated inside the supplied source may also anchor nearby source-relative language when the relation is supported by the source.
- If source_published_at is unknown and the source itself provides no valid temporal anchor, preserve the source-relative expression (for example, 'previous month relative to the source') and mark the absolute calendar time as unresolved/UNKNOWN in temporal context or uncertainties.
- Never invent an absolute date merely because measurement_as_of is known.

Return JSON only and obey the compact output contract supplied in the user message.
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

Audit reminders:
- measurement_as_of is NOT a source-time anchor.
- Every semantic object must cite evidence that is sufficient for that exact object.
- Do not treat bare URLs/page chrome as epistemic content.
- Do not label extractor inference as SOURCE_CLAIM.
- Do not duplicate the same payload in Event Frames and non-event units.

{output_contract}

Raw source snapshot with stable support markers:
--- SOURCE BEGIN ---
{source_text}
--- SOURCE END ---

Return one SemanticExtractionBatchV0_2. Use batch_id = "{source_id}-semantic-batch-v0.2" and source_ids = ["{source_id}"].
For event frames:
- event.as_of and temporal_context.as_of must equal measurement_as_of "{as_of}" because those fields record extraction state, not source publication time;
- the single source record must preserve the pinned source_id/media_type/locator exactly;
- source.published_at must equal pinned source_published_at "{published_at}" exactly;
- temporal_context.event_time must describe event/source-relative time faithfully and must not use measurement_as_of as a hidden anchor;
- each actor/object, action/change, affected-system/population, and uncertainty must cite the evidence ids that actually support that specific semantic object.
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
        published_at=source.published_at,
        updated_at=source.updated_at,
        captured_at=source.captured_at,
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
        if bound.published_at != source.published_at:
            raise ValueError("event frame published_at does not match pinned source metadata")
    for unit in batch.non_event_units:
        for support in unit.supports:
            if support.source_id != source.source_id:
                raise ValueError("non-event support source_id does not match pinned source")


def estimate_semantic_evidence_v0_2_2(source: LoadedSemanticSource, *, as_of: str, chat_fn=None) -> dict[str, Any]:
    """Run one v0.2.2 development extraction with one structural repair and diagnostics."""
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
        errors = exc.errors(include_url=False) if isinstance(exc, ValidationError) else [{"type": "source_binding", "msg": str(exc)}]
        schema_events.append({"retry": 0, "status": "invalid", "errors": errors})

    repair_messages = list(messages) + [
        {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)[:16000]},
        {"role": "user", "content": "Your JSON failed the required contract. Correct structural/provenance/temporal-binding errors only; do not invent unsupported evidence. Preserve the audit rules on evidence sufficiency, attribution, locator filtering, and deduplication.\nErrors:\n" + json.dumps(schema_events[-1]["errors"], ensure_ascii=False) + "\nReturn corrected JSON only.\n\n" + COMPACT_OUTPUT_CONTRACT},
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
        errors2 = exc2.errors(include_url=False) if isinstance(exc2, ValidationError) else [{"type": "source_binding", "msg": str(exc2)}]
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
        "temporal_anchor_policy": "measurement-time-never-substitutes-source-time-v0.2.1",
        "audit_policy": "sufficient-provenance-attribution-locator-dedup-v0.2.2",
    }
