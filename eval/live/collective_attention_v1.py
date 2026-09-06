"""Collective Attention Salience (P) estimator v1 — eval/research only.

Direct semantic implementation of the frozen P contract over frozen Evidence Packet v1.
Does not estimate D or S. Does not call production Attention Policy.

Prompt version: collective-attention-v1
Evidence interface: collective-attention-evidence-packet-v1
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "collective_attention_profile.v1.yaml"

ESTIMATOR_VERSION = "collective-attention-estimator-v1"
PROMPT_VERSION = "collective-attention-v1"
PROFILE_ID = "collective-attention-profile-v1"
EVIDENCE_INTERFACE_VERSION = "collective-attention-evidence-packet-v1"

THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.1

PROMPT_PROFILE_FIELDS = (
    "semantic_contract",
    "constituency_principles",
    "attention_evidence_principles",
    "temporal_principles",
    "orthogonality_and_missingness",
)

CollectiveAttentionLabel = Literal["SALIENT", "NOT_SALIENT"]
MeasurementStatus = Literal["scorable", "insufficient_evidence"]
ConstituencyScope = Literal["domain", "geographic", "product", "organization", "broad_public", "other"]
ReferenceScale = Literal["10^1", "10^2", "10^3", "10^4", "10^5", "10^6", "10^7+", "unknown"]
ConstituencyBasis = Literal["lookup", "llm_prior", "explicit_event_scope", "external_source", "unknown"]
EvidenceQuality = Literal["direct", "structural", "weak", "contaminated"]
ContaminationKind = Literal["paid", "bot", "forced_exposure", "duplicate", "unknown"]


class PEventV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(min_length=1, max_length=300)
    as_of: str = Field(min_length=1, max_length=100)
    semantic_summary: str = Field(min_length=1, max_length=4000)


class ConstituencyPriorV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=1000)
    scope: ConstituencyScope
    reference_scale: ReferenceScale
    reference_size_hint: str = Field(default="unknown", max_length=200)
    basis: ConstituencyBasis
    provenance: str = Field(min_length=1, max_length=1500)


class CollectionContextV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channels_checked: list[str] = Field(default_factory=list, max_length=100)
    channels_unavailable: list[str] = Field(default_factory=list, max_length=100)
    notes: str = Field(default="", max_length=2000)


class AttentionObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(min_length=1, max_length=200)
    window: str = Field(min_length=1, max_length=300)
    observation: str = Field(min_length=1, max_length=3000)
    source: str = Field(min_length=1, max_length=500)
    observed_at: str = Field(min_length=1, max_length=100)
    independence_group: str = Field(default="unknown", max_length=500)
    quality: EvidenceQuality
    contamination: list[ContaminationKind] = Field(default_factory=list, max_length=20)


class AttentionHistoryObservationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    window: str = Field(min_length=1, max_length=300)
    observation: str = Field(min_length=1, max_length=3000)
    source: str = Field(min_length=1, max_length=500)


class CollectiveAttentionEvidencePacketV1(BaseModel):
    """Frozen sensor boundary for P estimator v1."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event: PEventV1
    constituency_prior: ConstituencyPriorV1
    collection_context: CollectionContextV1
    current_attention_evidence: list[AttentionObservationV1] = Field(default_factory=list, max_length=200)
    recent_attention_history: list[AttentionHistoryObservationV1] = Field(default_factory=list, max_length=100)


class CollectiveAttentionV1Response(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    measurement_status: MeasurementStatus
    collective_attention_salience: CollectiveAttentionLabel | None = None
    objective_constituency: str = Field(default="", max_length=1000)
    attention_state_summary: str = Field(default="", max_length=1200)
    inertia_summary: str = Field(default="", max_length=1000)
    reason: str = Field(default="", max_length=900)

    @model_validator(mode="after")
    def validate_label_status(self):
        if self.measurement_status == "scorable" and self.collective_attention_salience is None:
            raise ValueError("scorable response requires collective_attention_salience")
        if self.measurement_status == "insufficient_evidence" and self.collective_attention_salience is not None:
            raise ValueError("insufficient_evidence response must not invent a semantic label")
        return self


SYSTEM_PROMPT = """You estimate Collective Attention Salience (P) for Research Attention OS.

P definition:
P asks whether, at the stated evaluation time, an event has already formed, or is clearly forming, a salient state of genuine collective attention within the event's Objective Attention Constituency. Attention is interpreted relative to the scale of that constituency and has temporal inertia.

You receive a frozen Evidence Packet v1. Treat it as sensor evidence about a latent attention state, not as a pre-computed answer.

Use this semantic procedure:
1. Read the event semantics and the supplied constituency prior. The correct reference constituency is the audience/community naturally implied by the event, independent of user preference and independent of who currently happens to be discussing it.
2. Do not shrink the denominator after seeing the attention observations. A small constituency is legitimate when the event itself is genuinely scoped to that group.
3. Judge genuine attention relative to that constituency's scale. Raw absolute discussion, reach, views, or impressions are not P by themselves.
4. Distinguish genuine attention from exposure or synthetic activity. Paid impressions, forced/autoplay exposure, bots, duplicates, and manipulated trend volume can overstate attention. Meaningful reads/views, active search, human engagement/discussion, voluntary propagation, independent institutional follow-up, and structural community uptake are stronger evidence.
5. Multi-source propagation is useful evidence but is not a mandatory gate. One large source may still generate genuine collective attention if many real constituency members meaningfully attend.
6. Current salience does not require positive growth. Stable high attention may remain SALIENT.
7. Emerging salience may already be SALIENT when current evidence clearly shows collective attention forming, even before absolute volume is large.
8. Preserve temporal inertia. A short-term decline does not by itself erase an established attention state. Use recent observation history to distinguish fluctuation from sustained decay.
9. Treat unavailable channels as unknown, not zero. Use collection_context to distinguish missing evidence from checked channels with no meaningful signal.
10. Judge only the supplied Evidence Packet. Do not browse, rely on unstated current facts, or manufacture current attention from pretrained memory.
11. Ignore whether the user personally cares (D), whether the event is intrinsically important/material (S), sentiment, stance, approval, controversy, and downstream AWARE/DROP decisions.
12. If the supplied packet lacks enough current evidence for a defensible judgment, return measurement_status=insufficient_evidence and no semantic label. Do not use uncertainty to create a third P state.

Evaluate P directly from the joint event/constituency/evidence/history semantics. Diagnostic fields are explanatory only; they are not mandatory symbolic sub-gates.

Return JSON only:
{
  "measurement_status": "scorable" or "insufficient_evidence",
  "collective_attention_salience": "SALIENT" or "NOT_SALIENT" or null,
  "objective_constituency": "short description",
  "attention_state_summary": "short evidence synthesis",
  "inertia_summary": "short temporal-state synthesis",
  "reason": "brief explanation"
}
Only collective_attention_salience is scored when measurement_status is scorable. Diagnostics are not scored.
Keep explanations short.
"""

USER_PROMPT_TEMPLATE = """Frozen Evidence Packet v1:
{packet}

Collective Attention profile:
{profile}
"""


def prompt_sha256() -> str:
    payload = (
        SYSTEM_PROMPT
        + "\n---\n"
        + USER_PROMPT_TEMPLATE
        + "\n---\n"
        + ",".join(PROMPT_PROFILE_FIELDS)
        + "\n---\n"
        + EVIDENCE_INTERFACE_VERSION
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_collective_attention_profile(path: Path | None = None) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load((path or PROFILE_PATH).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Collective Attention profile must be a mapping")
    missing = [key for key in PROMPT_PROFILE_FIELDS if key not in raw]
    if missing:
        raise ValueError(f"Collective Attention profile missing fields: {missing}")
    return {key: raw[key] for key in PROMPT_PROFILE_FIELDS}


def render_profile_for_prompt(profile: dict[str, Any]) -> str:
    import yaml

    allowed = {key: profile[key] for key in PROMPT_PROFILE_FIELDS}
    return yaml.safe_dump(allowed, sort_keys=False, allow_unicode=True).strip()


def validate_evidence_packet(packet: dict[str, Any] | CollectiveAttentionEvidencePacketV1) -> CollectiveAttentionEvidencePacketV1:
    if isinstance(packet, CollectiveAttentionEvidencePacketV1):
        return packet
    return CollectiveAttentionEvidencePacketV1.model_validate(packet)


def render_packet_for_prompt(packet: dict[str, Any] | CollectiveAttentionEvidencePacketV1) -> str:
    obj = validate_evidence_packet(packet)
    return json.dumps(obj.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2)


def build_messages(
    packet: dict[str, Any] | CollectiveAttentionEvidencePacketV1,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    profile = profile if profile is not None else load_collective_attention_profile()
    user = USER_PROMPT_TEMPLATE.format(
        packet=render_packet_for_prompt(packet),
        profile=render_profile_for_prompt(profile),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _is_transport_failure(exc: BaseException) -> bool:
    from app.cognitive.client import LLMTimeoutError, SchemaValidationError

    if isinstance(exc, SchemaValidationError):
        return False
    if isinstance(exc, LLMTimeoutError):
        return True
    text = str(exc).lower()
    tokens = ("timeout", "timed out", "connection", "503", "502", "500", "429", "temporarily")
    return any(token in text for token in tokens)


def estimate_collective_attention_v1(
    packet: dict[str, Any] | CollectiveAttentionEvidencePacketV1,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    """Call P v1. Never invent SALIENT/NOT_SALIENT on failure or insufficient evidence."""
    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    try:
        messages = build_messages(packet, profile)
    except Exception as exc:
        return {
            "scorable": False,
            "measurement_status": "invalid_packet",
            "collective_attention_salience": None,
            "objective_constituency": "",
            "attention_state_summary": "",
            "inertia_summary": "",
            "reason": None,
            "failure_kind": "invalid_packet",
            "error": str(exc)[:1000],
            "transport_retries": 0,
            "schema_events": [],
            "model_meta": None,
        }

    last_error: BaseException | None = None
    transport_retries = 0
    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                CollectiveAttentionV1Response,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            scorable = obj.measurement_status == "scorable"
            return {
                "scorable": scorable,
                "measurement_status": obj.measurement_status,
                "collective_attention_salience": obj.collective_attention_salience,
                "objective_constituency": obj.objective_constituency,
                "attention_state_summary": obj.attention_state_summary,
                "inertia_summary": obj.inertia_summary,
                "reason": obj.reason,
                "failure_kind": None if scorable else "insufficient_evidence",
                "error": None,
                "transport_retries": transport_retries,
                "schema_events": events,
                "model_meta": dict(meta or {}),
            }
        except SchemaValidationError as exc:
            return {
                "scorable": False,
                "measurement_status": "technical_failure",
                "collective_attention_salience": None,
                "objective_constituency": "",
                "attention_state_summary": "",
                "inertia_summary": "",
                "reason": None,
                "failure_kind": "schema_validation",
                "error": str(exc)[:1000],
                "transport_retries": transport_retries,
                "schema_events": list(exc.errors or []),
                "model_meta": None,
            }
        except LLMError as exc:
            last_error = exc
            if attempt == 0 and _is_transport_failure(exc):
                transport_retries += 1
                continue
            kind = "timeout" if "timeout" in str(exc).lower() else "model_call"
            return {
                "scorable": False,
                "measurement_status": "technical_failure",
                "collective_attention_salience": None,
                "objective_constituency": "",
                "attention_state_summary": "",
                "inertia_summary": "",
                "reason": None,
                "failure_kind": kind,
                "error": str(exc)[:1000],
                "transport_retries": transport_retries,
                "schema_events": [],
                "model_meta": None,
            }
    return {
        "scorable": False,
        "measurement_status": "technical_failure",
        "collective_attention_salience": None,
        "objective_constituency": "",
        "attention_state_summary": "",
        "inertia_summary": "",
        "reason": None,
        "failure_kind": "model_call",
        "error": str(last_error)[:1000] if last_error else "unknown model failure",
        "transport_retries": transport_retries,
        "schema_events": [],
        "model_meta": None,
    }


def compute_collective_attention_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [
        row for row in rows
        if row.get("scorable") and row.get("gold") in {"SALIENT", "NOT_SALIENT"}
    ]
    n = len(scored)
    n_gold_salient = sum(row["gold"] == "SALIENT" for row in scored)
    n_gold_not = sum(row["gold"] == "NOT_SALIENT" for row in scored)
    n_pred_salient = sum(row.get("prediction") == "SALIENT" for row in scored)
    n_pred_not = sum(row.get("prediction") == "NOT_SALIENT" for row in scored)
    exact = sum(row.get("prediction") == row.get("gold") for row in scored)
    true_salient = sum(
        row.get("gold") == "SALIENT" and row.get("prediction") == "SALIENT"
        for row in scored
    )
    true_not = sum(
        row.get("gold") == "NOT_SALIENT" and row.get("prediction") == "NOT_SALIENT"
        for row in scored
    )
    false_salient = sum(
        row.get("gold") == "NOT_SALIENT" and row.get("prediction") == "SALIENT"
        for row in scored
    )
    false_not = sum(
        row.get("gold") == "SALIENT" and row.get("prediction") == "NOT_SALIENT"
        for row in scored
    )

    salient_recall = true_salient / n_gold_salient if n_gold_salient else None
    not_salient_recall = true_not / n_gold_not if n_gold_not else None
    recall_values = [x for x in (salient_recall, not_salient_recall) if x is not None]
    balanced = sum(recall_values) / len(recall_values) if recall_values else None

    return {
        "n_scored": n,
        "n_gold_salient": n_gold_salient,
        "n_gold_not_salient": n_gold_not,
        "n_pred_salient": n_pred_salient,
        "n_pred_not_salient": n_pred_not,
        "exact_accuracy": exact / n if n else None,
        "salient_recall": salient_recall,
        "not_salient_recall": not_salient_recall,
        "balanced_accuracy": balanced,
        "false_salient_count": false_salient,
        "false_salient_rate": false_salient / n if n else None,
        "false_not_salient_count": false_not,
        "false_not_salient_rate": false_not / n if n else None,
    }


def invocation_record(*, requested_model: str | None, provider_base_url: str | None, thinking_protocol: str | None) -> dict[str, Any]:
    return {
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "profile_id": PROFILE_ID,
        "evidence_interface_version": EVIDENCE_INTERFACE_VERSION,
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "thinking_protocol": thinking_protocol,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": TEMPERATURE,
        "response_format": "json_object",
        "structured_schema": "CollectiveAttentionV1Response",
    }
