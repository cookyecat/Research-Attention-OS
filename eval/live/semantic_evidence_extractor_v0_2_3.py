"""Semantic Evidence Extractor v0.2.3 — minimal-sufficient representation candidate.

Controlled revision over v0.2.2:
- keeps SemanticExtractionBatchV0_2 and EventFrame v0.1 structures;
- keeps temporal-anchor and evidence-sufficiency rules;
- changes only semantic compression / bounded representation policy;
- adds an experimental hard cap of 12 non-event semantic units and 4 supports per unit.

No D/S/P labels, Attention Actions, user relevance, or importance judgments.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import ValidationError

from eval.live.semantic_evidence_batch_v0_2 import SemanticExtractionBatchV0_2
from eval.live.semantic_source_loader_v0_1 import LoadedSemanticSource
from eval.live.semantic_evidence_extractor_v0_2_2 import (
    _json_safe,
    _validation_errors,
    _validate_source_binding,
)

EXTRACTOR_VERSION = "semantic-evidence-extractor-v0.2.3"
PROMPT_VERSION = "semantic-evidence-extraction-v0.2.3-minimal-sufficient"
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 90.0
TEMPERATURE = 0.1

MAX_NON_EVENT_UNITS = 12
MAX_SUPPORTS_PER_NON_EVENT_UNIT = 4
PREFERRED_NON_EVENT_RANGE = "6..10 when the source genuinely contains that many independent epistemic points"

MINIMAL_OUTPUT_CONTRACT = r'''Required top-level shape:
{
  "interface_version": "semantic-evidence-batch-v0.2",
  "batch_id": "<source_id>-semantic-batch-v0.2",
  "source_ids": ["<source_id>"],
  "event_frames": [ ... max 8 SemanticEvidenceFrameV0_1 objects ... ],
  "non_event_units": [ ... EXPERIMENTAL HARD CAP 12 objects ... ],
  "notes": []
}

Each non_event_units item MUST be exactly:
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
Use at most 4 supports per non-event unit; normally 1-2 supports should suffice.

Each event_frames item MUST match SemanticEvidenceFrameV0_1 exactly:
{
  "interface_version": "semantic-evidence-frame-v0.1",
  "event": {"event_id":"...", "as_of":"<measurement as_of>", "summary":"..."},
  "sources": [{"source_id":"<source_id>", "source_type":"<media_type>", "published_at":"unknown-or-supported", "locator":"<pinned path>"}],
  "evidence": [{"evidence_id":"...", "source_id":"<source_id>", "support_pointer":"PARA/PAGE ...", "support_excerpt":"smallest sufficient excerpt", "epistemic_status":"SOURCE_CLAIM|DIRECT_OBSERVATION|EXTRACTOR_INFERENCE", "confidence":"HIGH|MEDIUM|LOW|UNKNOWN"}],
  "substantive_actors_objects": [{"name":"...", "role":"...", "substantive_basis":"...", "support_ids":["evidence-id"]}],
  "actions_changes": [{"description":"...", "temporal_status":"PROPOSED|ANNOUNCED|ENACTED|EFFECTIVE|OBSERVED|HISTORICAL|UNKNOWN", "support_ids":["evidence-id"]}],
  "affected_systems_populations": [{"description":"...", "reference_scope":"...", "support_ids":["evidence-id"]}],
  "temporal_context": {"event_time":"unknown-or-supported", "effective_time":"unknown-or-supported", "as_of":"<measurement as_of>", "notes":""},
  "uncertainties": [{"field":"...", "kind":"UNKNOWN|CONFLICTING_SOURCES|UNCERTAIN_SCOPE|UNCERTAIN_ACTOR_ROLE|INSUFFICIENT_SUPPORT", "note":"...", "support_ids":[]}]
}

Compression policy:
- Preserve independent events/results, claims, methods, mechanisms, causal relations, material quantitative conclusions, conditions/caveats, attribution, temporal status, and uncertainty.
- Do NOT create one unit per sentence, example, benchmark, implementation variant, or repeated restatement.
- Merge details when they support the same underlying semantic predicate and share attribution/temporal/causal role.
- Keep quantitative details inside the parent unit when they materially distinguish magnitude, comparison, threshold, or outcome.
- A support example may remain only as provenance; it does not require its own semantic unit.
- Keep note empty unless it carries necessary qualification not represented elsewhere.
'''

SYSTEM_PROMPT = """You are the Semantic Sensor Front-End for Research Attention OS (RAOS).

Your job is source-grounded semantic extraction with MINIMAL SUFFICIENT REPRESENTATION.
The goal is not to restate the source in structured form. The goal is to preserve the
smallest set of independent semantic distinctions needed to understand what the source
actually says and to audit why the Sensor says it.

Hard boundaries:
- Never output D, S, P, Delta, AWARE, DROP, WATCH, ENGAGE, user relevance, or importance.
- Never use outside knowledge to fill gaps or correct the supplied source.
- Never turn missing information into absence/zero.
- Never turn a quote, prediction, marketing statement, interview opinion, or discussion
  comment into an unattributed world fact.

A raw source may yield zero, one, or multiple event frames. Tutorials, opinions,
preferences, methodological advice, interpretations, arguments, and discussion patterns
should normally be non-event semantic units unless there is a concrete event/result/change.

Epistemic status:
- SOURCE_CLAIM: asserted/reported/quoted by the source or a speaker/author.
- DIRECT_OBSERVATION: direct raw observation/measurement present in the supplied material.
- EXTRACTOR_INFERENCE: your semantic inference from supported content; use sparingly.
- Do not label your own inference as SOURCE_CLAIM.
- Unsupported speculation must be omitted.

Confidence means confidence that the extraction/attribution is supported by the supplied
source. It does NOT mean confidence that the source's claim is true in the outside world.

MINIMAL SUFFICIENT COMPRESSION — HARD POLICY:
- Think in independent semantic predicates/clusters, not sentences.
- Create a separate unit only if removing it would lose a distinct proposition that
  cannot be reconstructed from remaining units without changing truth-conditional
  meaning, actor attribution, causal role, method/mechanism, quantitative conclusion,
  temporal status, scope/condition, or uncertainty.
- If deleting a candidate unit does NOT remove an independent meaning, merge it.
- Merge multiple examples, benchmark values, implementation variants, and repeated
  explanations when they support the same higher-level source-grounded point.
- Preserve quantitative values when they materially distinguish a result, comparison,
  threshold, scale, or outcome; do not create one unit for every number.
- Prefer roughly 6-10 non-event units when that is enough for the source. Never exceed 12.
- Do not fill the budget merely because it exists. A simpler source may need fewer units.
- Avoid duplicating the same semantic payload across an Event Frame and a non-event unit.

MINIMAL SUFFICIENT PROVENANCE — HARD POLICY:
- Every support pointer must use a visible PARA/PAGE marker from the supplied source.
- Every semantic object must be supported by the evidence it cites.
- Use the fewest supports necessary for the exact claim; non-event units may use at most 4.
- Normally 1-2 supports should suffice.
- Quote the smallest excerpt that actually demonstrates the claim. Evidence excerpts are
  audit material, not a backup copy of the article.
- Do not rely on an uncited nearby paragraph.
- If a claim genuinely requires multiple passages, cite all necessary passages.
- Prefer minimal sufficient evidence; do not attach irrelevant evidence.

Locator / page-chrome filtering:
- Bare URLs, navigation labels, advertisements, share controls, reaction counts, page
  furniture, and source locators are metadata/page chrome, not epistemic units by default.
- Never infer what a linked page/video contains from the URL alone.

Temporal anchoring — unchanged from v0.2.2:
- measurement_as_of is NOT source publication time.
- Use pinned source_published_at only when known and applicable.
- source_updated_at and source_captured_at are distinct metadata and are not substitutes.
- An explicit date inside the source may anchor nearby source-relative language when supported.
- If source publication time is unknown and no source-local anchor exists, preserve relative
  time and mark absolute calendar time unresolved.
- Never invent an absolute date from measurement_as_of.

Return JSON only and obey the minimal output contract supplied in the user message.
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

Before emitting JSON, silently apply the Semantic Independence Test:
Create a separate semantic unit only when deleting it would lose an independent meaning.
Merge examples/details that support the same predicate. Do not output this internal check.

{output_contract}

Raw source snapshot with stable support markers:
--- SOURCE BEGIN ---
{source_text}
--- SOURCE END ---

Return one SemanticExtractionBatchV0_2. Use batch_id = "{source_id}-semantic-batch-v0.2" and source_ids = ["{source_id}"].
For event frames:
- event.as_of and temporal_context.as_of must equal measurement_as_of "{as_of}" because those fields record extraction state;
- the single source record must preserve pinned source_id/media_type/locator exactly;
- source.published_at must equal pinned source_published_at "{published_at}" exactly;
- temporal_context.event_time must preserve source/source-relative time faithfully;
- every actor/object, action/change, affected-system/population, and uncertainty must cite only evidence ids sufficient for that exact object.
"""


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE + "\n---\n" + MINIMAL_OUTPUT_CONTRACT
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
        output_contract=MINIMAL_OUTPUT_CONTRACT,
        source_text=source.rendered_text,
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _validate_compression_policy(batch: SemanticExtractionBatchV0_2) -> None:
    if len(batch.non_event_units) > MAX_NON_EVENT_UNITS:
        raise ValueError(
            f"minimal-sufficient policy allows at most {MAX_NON_EVENT_UNITS} non-event units; "
            f"got {len(batch.non_event_units)}"
        )
    for unit in batch.non_event_units:
        if len(unit.supports) > MAX_SUPPORTS_PER_NON_EVENT_UNIT:
            raise ValueError(
                f"minimal-sufficient policy allows at most {MAX_SUPPORTS_PER_NON_EVENT_UNIT} "
                f"supports per non-event unit; {unit.unit_id} has {len(unit.supports)}"
            )


def _validate_candidate(
    batch: SemanticExtractionBatchV0_2,
    source: LoadedSemanticSource,
    *,
    as_of: str,
) -> None:
    _validate_source_binding(batch, source, as_of=as_of)
    _validate_compression_policy(batch)


def estimate_semantic_evidence_v0_2_3(source: LoadedSemanticSource, *, as_of: str, chat_fn=None) -> dict[str, Any]:
    """Run one minimal-sufficient extraction with one structural/policy repair."""
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
        return {
            "scorable": False,
            "batch": None,
            "failure_kind": "model_call",
            "error": str(exc)[:2000],
            "repair_used": False,
            "schema_events": [],
            "invalid_raw": None,
            "model_meta": None,
        }

    try:
        obj = SemanticExtractionBatchV0_2.model_validate(parsed)
        _validate_candidate(obj, source, as_of=as_of)
        meta = dict(meta or {})
        meta["schema_repaired"] = False
        return {
            "scorable": True,
            "batch": obj.model_dump(mode="json"),
            "failure_kind": None,
            "error": None,
            "repair_used": False,
            "schema_events": [],
            "invalid_raw": None,
            "model_meta": meta,
        }
    except (ValidationError, ValueError) as exc:
        errors = _validation_errors(exc)
        schema_events.append({"retry": 0, "status": "invalid", "errors": errors})

    repair_messages = list(messages) + [
        {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False, default=str)[:16000]},
        {
            "role": "user",
            "content": (
                "Your JSON failed the required structural/minimal-sufficient contract. "
                "Correct structural/provenance/temporal/compression-policy errors only. "
                "Do not invent unsupported evidence. Merge redundant semantic units rather "
                "than deleting independent meanings.\nErrors:\n"
                + json.dumps(schema_events[-1]["errors"], ensure_ascii=False)
                + "\nReturn corrected JSON only.\n\n"
                + MINIMAL_OUTPUT_CONTRACT
            ),
        },
    ]
    try:
        parsed2, meta2 = fn(repair_messages, **call_kw)
        meta = merge_usage_meta(meta, meta2)
    except LLMError as exc:
        return {
            "scorable": False,
            "batch": None,
            "failure_kind": "model_call_after_schema_failure",
            "error": str(exc)[:2000],
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": _json_safe(parsed),
            "model_meta": dict(meta or {}),
        }

    try:
        obj = SemanticExtractionBatchV0_2.model_validate(parsed2)
        _validate_candidate(obj, source, as_of=as_of)
        schema_events.append({"retry": 1, "status": "repaired"})
        meta["schema_repaired"] = True
        return {
            "scorable": True,
            "batch": obj.model_dump(mode="json"),
            "failure_kind": None,
            "error": None,
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": None,
            "model_meta": meta,
        }
    except (ValidationError, ValueError) as exc2:
        errors2 = _validation_errors(exc2)
        schema_events.append({"retry": 1, "status": "invalid", "errors": errors2})
        return {
            "scorable": False,
            "batch": None,
            "failure_kind": "schema_validation",
            "error": "SemanticExtractionBatchV0_2 invalid after minimal-sufficient repair",
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": _json_safe(parsed2),
            "model_meta": meta,
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
        "structured_schema": "SemanticExtractionBatchV0_2",
        "temporal_anchor_policy": "measurement-time-never-substitutes-source-time-v0.2.1",
        "audit_policy": "sufficient-provenance-attribution-locator-dedup-v0.2.2",
        "compression_policy": "minimal-sufficient-semantic-basis-v0.2.3",
        "max_non_event_units": MAX_NON_EVENT_UNITS,
        "max_supports_per_non_event_unit": MAX_SUPPORTS_PER_NON_EVENT_UNIT,
        "preferred_non_event_range": PREFERRED_NON_EVENT_RANGE,
    }
