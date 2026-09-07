"""Semantic Evidence Extractor v0.1 — development-only sensor front-end.

Transforms one pinned raw source snapshot into a source-level
SemanticExtractionBatchV0_1. The extractor is evidence-oriented and must not
predict D/S/P, Attention Actions, user relevance, or intrinsic importance.

A source may yield zero, one, or multiple event frames plus non-event epistemic
units. This is development instrumentation, not a frozen/final extractor.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import ValidationError

from eval.live.semantic_evidence_batch_v0_1 import SemanticExtractionBatchV0_1
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource

EXTRACTOR_VERSION = "semantic-evidence-extractor-v0.1"
PROMPT_VERSION = "semantic-evidence-extraction-v0.1"
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 90.0
TEMPERATURE = 0.1

SYSTEM_PROMPT = """You are the Semantic Sensor Front-End for Research Attention OS (RAOS).

Your task is source-grounded semantic extraction, not recommendation or judgment.
Recover what the supplied raw source says while preserving provenance, attribution,
uncertainty, temporal status, and the distinction between event-like facts and
non-event epistemic content.

Constitutional boundaries:
- Do NOT output or infer D / Standing Radar Fit.
- Do NOT output or infer S / Material Consequence.
- Do NOT output or infer P / Collective Attention Salience.
- Do NOT output AWARE / DROP / WATCH / ENGAGE.
- Do NOT judge user interest, relevance, importance, editorial worthiness, or whether
  the user should read the source.
- Do NOT use outside/world knowledge to fill gaps or correct the supplied source.
- Do NOT silently turn missing information into absence/zero.
- Do NOT turn a source's claim, quote, prediction, marketing statement, or interview
  opinion into an unattributed world fact.

A raw source does NOT necessarily correspond to one event.
It may contain:
- zero, one, or multiple concrete event/result/change units;
- tutorial or methodological content;
- interview opinions/predictions;
- discussion/community preferences;
- historical background;
- multiple attributed claims.

Use event_frames only when there is a concrete event-like or result-like semantic unit
that can be characterized by what happened/changed, substantive actors/objects,
possibly affected systems/populations, and time/status. A primary research paper may
have an event frame such as 'the paper reports experimental result X'. Do not force
pure tutorial, opinion, preference, or discussion content into an event frame merely
so that a frame exists.

Use non_event_units for major source-grounded claims, observations, methodological
statements, opinions, predictions, or discussion content that should remain available
to the cognitive path but is not naturally an event frame.

Epistemic status:
- SOURCE_CLAIM: something asserted/reported/quoted by the source or a speaker/author.
- DIRECT_OBSERVATION: direct raw observation/measurement actually present in the
  supplied material, not merely a journalist or interviewee saying something occurred.
- EXTRACTOR_INFERENCE: a semantic inference you make from supported source content.
  Use sparingly and never hide it as source fact.

Provenance rules:
- Every support_pointer must use a marker visible in the supplied source, e.g.
  'PARA 0012' or 'PAGE 0004'.
- Keep support_excerpt short and diagnostic; do not reproduce long passages.
- Each event-frame actor/change/affected-system must cite valid evidence ids.
- Preserve proposal vs announcement vs enacted/effective/observed/historical state.
- If scope, actor role, time, or support is uncertain, record uncertainty rather than
  inventing precision.

Extraction granularity:
- Prefer a small set of high-value semantic units over sentence-by-sentence exhaustiveness.
- Normally use <= 8 event frames and <= 20 non-event units for one source.
- Split genuinely distinct events/results; do not split every detail into a separate event.

Return JSON matching SemanticExtractionBatchV0_1 only.
"""

USER_PROMPT_TEMPLATE = """Measurement as_of: {as_of}

Pinned source metadata (must be preserved exactly where represented in event-frame source records):
source_id: {source_id}
locator: {locator}
media_type: {media_type}
git_blob_sha: {git_blob_sha}

Raw source snapshot with stable support markers:
--- SOURCE BEGIN ---
{source_text}
--- SOURCE END ---

Output one SemanticExtractionBatchV0_1 for this source.
Use batch_id = "{source_id}-semantic-batch-v0.1" and source_ids = ["{source_id}"].
For every event frame:
- event.as_of and temporal_context.as_of must equal "{as_of}";
- sources must contain exactly one source record;
- that source record must use source_id "{source_id}", source_type "{media_type}",
  and locator "{locator}";
- published_at may be extracted only when explicitly supported by the source,
  otherwise use "unknown".
"""


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE
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
        source_text=source.rendered_text,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _is_transport_failure(exc: BaseException) -> bool:
    text = str(exc).lower()
    tokens = ("timeout", "timed out", "connection", "503", "502", "500", "429", "temporarily")
    return any(token in text for token in tokens)


def _validate_source_binding(
    batch: SemanticExtractionBatchV0_1,
    source: LoadedSemanticSource,
    *,
    as_of: str,
) -> None:
    if batch.source_ids != [source.source_id]:
        raise ValueError(
            f"batch source_ids must equal [{source.source_id!r}], got {batch.source_ids!r}"
        )

    for frame in batch.event_frames:
        if frame.event.as_of != as_of or frame.temporal_context.as_of != as_of:
            raise ValueError("event/temporal as_of does not match measurement as_of")
        if len(frame.sources) != 1:
            raise ValueError("each single-source event frame must contain exactly one source record")
        bound = frame.sources[0]
        if bound.source_id != source.source_id:
            raise ValueError("event frame source_id does not match pinned source")
        if bound.source_type != source.media_type:
            raise ValueError("event frame source_type does not match pinned media_type")
        if bound.locator != source.path:
            raise ValueError("event frame locator does not match pinned source path")

    for unit in batch.non_event_units:
        if unit.source_id != source.source_id:
            raise ValueError("non-event unit source_id does not match pinned source")


def estimate_semantic_evidence_v0_1(
    source: LoadedSemanticSource,
    *,
    as_of: str,
    chat_fn=None,
) -> dict[str, Any]:
    """Run one development extraction. Never invent a batch on model failure."""

    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    messages = build_messages(source, as_of=as_of)
    last_error: BaseException | None = None
    transport_retries = 0

    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                SemanticExtractionBatchV0_1,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            try:
                _validate_source_binding(obj, source, as_of=as_of)
            except (ValueError, ValidationError) as exc:
                return {
                    "scorable": False,
                    "batch": None,
                    "failure_kind": "source_binding_validation",
                    "error": str(exc)[:2000],
                    "transport_retries": transport_retries,
                    "schema_events": events,
                    "model_meta": dict(meta or {}),
                }
            return {
                "scorable": True,
                "batch": obj.model_dump(mode="json"),
                "failure_kind": None,
                "error": None,
                "transport_retries": transport_retries,
                "schema_events": events,
                "model_meta": dict(meta or {}),
            }
        except SchemaValidationError as exc:
            return {
                "scorable": False,
                "batch": None,
                "failure_kind": "schema_validation",
                "error": str(exc)[:2000],
                "transport_retries": transport_retries,
                "schema_events": list(exc.errors or []),
                "model_meta": None,
            }
        except LLMError as exc:
            last_error = exc
            if attempt == 0 and _is_transport_failure(exc):
                transport_retries += 1
                continue
            return {
                "scorable": False,
                "batch": None,
                "failure_kind": "model_call",
                "error": str(exc)[:2000],
                "transport_retries": transport_retries,
                "schema_events": [],
                "model_meta": None,
            }

    return {
        "scorable": False,
        "batch": None,
        "failure_kind": "model_call",
        "error": str(last_error)[:2000] if last_error else "unknown model failure",
        "transport_retries": transport_retries,
        "schema_events": [],
        "model_meta": None,
    }


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
        "structured_schema": "SemanticExtractionBatchV0_1",
    }
