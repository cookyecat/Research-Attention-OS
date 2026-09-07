"""Semantic Evidence Auditor v0.1 — development-only semantic support verifier.

Purpose:
Given exactly one semantic object and its already-cited evidence excerpts, decide whether
those excerpts are sufficient to support that object.

Occam boundary:
- does NOT reread/search the full source;
- does NOT retrieve replacement evidence;
- does NOT repair the extractor output;
- does NOT judge D/S/P/Delta or attention actions;
- does NOT verify outside-world truth.

It verifies only the local edge:

    semantic object  <-  cited evidence

This is an engineering verifier, not a new RAOS theoretical variable.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

AUDITOR_VERSION = "semantic-evidence-auditor-v0.1"
PROMPT_VERSION = "semantic-evidence-audit-v0.1"
INTERFACE_VERSION = "semantic-evidence-audit-result-v0.1"

THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 45.0
TEMPERATURE = 0.1

AuditVerdict = Literal["SUFFICIENT", "INSUFFICIENT", "UNCERTAIN"]


class EvidenceSupportV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=300)
    support_pointer: str = Field(min_length=1, max_length=1000)
    support_excerpt: str = Field(min_length=1, max_length=1600)


class SemanticEvidenceAuditResultV0_1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    interface_version: Literal["semantic-evidence-audit-result-v0.1"] = INTERFACE_VERSION
    audit_id: str = Field(min_length=1, max_length=300)
    verdict: AuditVerdict
    rationale: str = Field(min_length=1, max_length=1800)
    unsupported_or_uncertain_aspect: str = Field(default="", max_length=1200)


SYSTEM_PROMPT = """You are the Semantic Evidence Auditor for Research Attention OS (RAOS).

Your only job is to verify one local provenance edge:

    semantic object <- cited evidence excerpts

Question:
Do the cited excerpts, by themselves, sufficiently support the semantic object?

Hard boundaries:
- Judge ONLY the supplied semantic object and supplied evidence excerpts.
- Do not use outside knowledge.
- Do not search for, imagine, or request uncited nearby paragraphs.
- Do not repair or rewrite the semantic object.
- Do not propose replacement evidence.
- Do not judge whether the source claim is true in the outside world.
- Do not output D, S, P, Delta, AWARE, DROP, WATCH, ENGAGE, relevance, or importance.

Verdicts:
- SUFFICIENT: the cited evidence alone supports every material part of the semantic object,
  allowing conservative paraphrase and ordinary linguistic entailment.
- INSUFFICIENT: at least one material part is not supported by the cited evidence. Use this
  when support is absent, imported from outside context, or requires an uncited passage.
- UNCERTAIN: the cited evidence is genuinely relevant, but ambiguity of wording, reference,
  scope, or attribution prevents a confident support judgment. Do not use UNCERTAIN merely
  because evidence is missing; missing support is INSUFFICIENT.

Audit discipline:
- Evaluate the smallest material claims inside the semantic object.
- A pointer existing is not evidence sufficiency.
- A nearby fact that would make the object plausible is not enough unless it is in the cited excerpts.
- If the object adds a stronger scope, actor, causal relation, time, quantity, or system identity
  than the excerpts state or conservatively entail, mark INSUFFICIENT or UNCERTAIN as appropriate.
- Keep the rationale concise and source-grounded.

Return JSON only with exactly:
{
  "interface_version": "semantic-evidence-audit-result-v0.1",
  "audit_id": "<same audit id>",
  "verdict": "SUFFICIENT" | "INSUFFICIENT" | "UNCERTAIN",
  "rationale": "brief explanation tied only to the cited evidence",
  "unsupported_or_uncertain_aspect": "" or "the specific unsupported/ambiguous part"
}
"""

USER_PROMPT_TEMPLATE = """audit_id: {audit_id}
semantic_object_type: {object_type}
semantic_object:
{semantic_object}

cited_evidence:
{evidence_json}

Decide only whether the cited evidence above is sufficient for the semantic object above.
Return one SemanticEvidenceAuditResultV0_1 JSON object.
"""


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    """Normalize diagnostics so exception objects cannot break artifact serialization."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _validate_inputs(
    *,
    audit_id: str,
    object_type: str,
    semantic_object: str,
    evidence: list[dict[str, Any]],
) -> list[EvidenceSupportV0_1]:
    if not str(audit_id or "").strip():
        raise ValueError("audit_id is required")
    if not str(object_type or "").strip():
        raise ValueError("object_type is required")
    if not str(semantic_object or "").strip():
        raise ValueError("semantic_object is required")
    if not evidence:
        raise ValueError("at least one cited evidence item is required")
    return [EvidenceSupportV0_1.model_validate(item) for item in evidence]


def build_messages(
    *,
    audit_id: str,
    object_type: str,
    semantic_object: str,
    evidence: list[dict[str, Any]],
) -> list[dict[str, str]]:
    supports = _validate_inputs(
        audit_id=audit_id,
        object_type=object_type,
        semantic_object=semantic_object,
        evidence=evidence,
    )
    user = USER_PROMPT_TEMPLATE.format(
        audit_id=str(audit_id).strip(),
        object_type=str(object_type).strip(),
        semantic_object=str(semantic_object).strip(),
        evidence_json=json.dumps([s.model_dump(mode="json") for s in supports], ensure_ascii=False, indent=2),
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def audit_semantic_evidence_v0_1(
    *,
    audit_id: str,
    object_type: str,
    semantic_object: str,
    evidence: list[dict[str, Any]],
    chat_fn=None,
) -> dict[str, Any]:
    """Audit one semantic-object/evidence edge with one structural repair fallback."""
    from app.cognitive.client import LLMError, chat_json, merge_usage_meta

    fn = chat_fn or chat_json
    messages = build_messages(
        audit_id=audit_id,
        object_type=object_type,
        semantic_object=semantic_object,
        evidence=evidence,
    )
    call_kw = {
        "model": None,
        "timeout": TIMEOUT_SECONDS,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
    }
    schema_events: list[dict[str, Any]] = []

    try:
        parsed, meta = fn(messages, **call_kw)
    except LLMError as exc:
        return {
            "scorable": False,
            "result": None,
            "failure_kind": "model_call",
            "error": str(exc)[:2000],
            "repair_used": False,
            "schema_events": [],
            "invalid_raw": None,
            "model_meta": None,
        }

    try:
        obj = SemanticEvidenceAuditResultV0_1.model_validate(parsed)
        if obj.audit_id != audit_id:
            raise ValueError("audit_id does not match request")
        meta = dict(meta or {})
        meta["schema_repaired"] = False
        return {
            "scorable": True,
            "result": obj.model_dump(mode="json"),
            "failure_kind": None,
            "error": None,
            "repair_used": False,
            "schema_events": [],
            "invalid_raw": None,
            "model_meta": meta,
        }
    except (ValidationError, ValueError) as exc:
        errors = (
            exc.errors(include_url=False)
            if isinstance(exc, ValidationError)
            else [{"type": "request_binding", "msg": str(exc)}]
        )
        schema_events.append({"retry": 0, "status": "invalid", "errors": _json_safe(errors)})

    repair_messages = list(messages) + [
        {"role": "assistant", "content": json.dumps(parsed, ensure_ascii=False)[:8000]},
        {
            "role": "user",
            "content": (
                "Your JSON failed the audit output contract. Correct structural/binding errors only. "
                "Do not change the evidence or invent new evidence.\nErrors:\n"
                + json.dumps(schema_events[-1]["errors"], ensure_ascii=False)
                + "\nReturn corrected JSON only using the exact audit result contract from the system prompt."
            ),
        },
    ]

    try:
        parsed2, meta2 = fn(repair_messages, **call_kw)
        meta = merge_usage_meta(meta, meta2)
    except LLMError as exc:
        return {
            "scorable": False,
            "result": None,
            "failure_kind": "model_call_after_schema_failure",
            "error": str(exc)[:2000],
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": parsed,
            "model_meta": dict(meta or {}),
        }

    try:
        obj = SemanticEvidenceAuditResultV0_1.model_validate(parsed2)
        if obj.audit_id != audit_id:
            raise ValueError("audit_id does not match request")
        schema_events.append({"retry": 1, "status": "repaired"})
        meta["schema_repaired"] = True
        return {
            "scorable": True,
            "result": obj.model_dump(mode="json"),
            "failure_kind": None,
            "error": None,
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": None,
            "model_meta": meta,
        }
    except (ValidationError, ValueError) as exc2:
        errors2 = (
            exc2.errors(include_url=False)
            if isinstance(exc2, ValidationError)
            else [{"type": "request_binding", "msg": str(exc2)}]
        )
        schema_events.append({"retry": 1, "status": "invalid", "errors": _json_safe(errors2)})
        return {
            "scorable": False,
            "result": None,
            "failure_kind": "schema_validation",
            "error": "SemanticEvidenceAuditResultV0_1 invalid after repair",
            "repair_used": True,
            "schema_events": schema_events,
            "invalid_raw": parsed2,
            "model_meta": meta,
        }


def invocation_record(*, requested_model: str | None, provider_base_url: str | None) -> dict[str, Any]:
    return {
        "auditor_version": AUDITOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": TEMPERATURE,
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "response_format": "json_object",
        "structured_schema": "SemanticEvidenceAuditResultV0_1",
        "audit_scope": "one-semantic-object-vs-cited-evidence-only",
    }
