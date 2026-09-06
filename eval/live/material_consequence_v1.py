"""Material Consequence (S) estimator v1 — eval/research only.

Direct semantic implementation of the frozen S contract:
material disturbance of consequential shared reference systems.
Does not estimate D or P. Does not call production Attention Policy.

Prompt version: material-consequence-v1
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "material_consequence_profile.v1.yaml"

ESTIMATOR_VERSION = "material-consequence-estimator-v1"
PROMPT_VERSION = "material-consequence-v1"
PROFILE_ID = "material-consequence-profile-v1"

THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.1

PROMPT_PROFILE_FIELDS = (
    "semantic_contract",
    "invariants",
    "shared_reference_system_examples",
    "boundary_principles",
)

MaterialConsequenceLabel = Literal["MATERIAL", "NOT_MATERIAL"]

SYSTEM_PROMPT = """You estimate Material Consequence (S) for Research Attention OS.

S definition:
S is the material consequence of the underlying event itself, independent of user interest and public attention.
It asks whether the event causes a material disturbance to at least one consequential shared reference system.

Use this semantic procedure:
1. Understand the stated event directly and semantically.
2. Evaluate whether the event itself changes the state, control, constraints, rules, capability, accepted knowledge, common practice, market structure, public system, or broadly shared cultural state of a consequential shared reference system.
3. Do NOT normalize importance to the smallest affected unit. A family, classroom, township, local office, or single firm can be radically changed while S remains NOT_MATERIAL if the consequence stays bounded there.
4. Distinguish raw reach from real disturbance. Large population count, famous actors, novelty, quality, or widespread distribution are not sufficient when meaningful state barely changes.
5. Conversely, do not require nationwide reach. A narrow niche can be MATERIAL if the whole relevant industry/field/rule system is structurally changed.
6. Changes in control or option structure of a consequential shared system can themselves be material even before downstream outcomes are observed.
7. Judge only stated facts. Do not manufacture plausible future consequences.
8. Ignore media coverage, virality, discussion volume, and whether the user personally cares. Those belong to P or D, not S.

Evaluate the S predicate directly over the event semantics. The diagnostic fields below are explanatory only; they are not mandatory intermediate gates.

Return JSON only:
{
  "material_consequence": "MATERIAL" or "NOT_MATERIAL",
  "affected_shared_systems": ["short system description", ...],
  "material_changes": ["short causal change", ...],
  "reason": "brief explanation"
}
Only material_consequence is scored. The other fields are diagnostics only.
Keep reason short.
"""

USER_PROMPT_TEMPLATE = """Event:
{event}

Material Consequence profile:
{profile}
"""


class MaterialConsequenceV1Response(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    material_consequence: MaterialConsequenceLabel
    affected_shared_systems: list[str] = Field(default_factory=list)
    material_changes: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=700)


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE + "\n---\n" + ",".join(PROMPT_PROFILE_FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_material_consequence_profile(path: Path | None = None) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load((path or PROFILE_PATH).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Material Consequence profile must be a mapping")
    missing = [key for key in PROMPT_PROFILE_FIELDS if key not in raw]
    if missing:
        raise ValueError(f"Material Consequence profile missing fields: {missing}")
    return {key: raw[key] for key in PROMPT_PROFILE_FIELDS}


def render_profile_for_prompt(profile: dict[str, Any]) -> str:
    import yaml

    allowed = {key: profile[key] for key in PROMPT_PROFILE_FIELDS}
    return yaml.safe_dump(allowed, sort_keys=False, allow_unicode=True).strip()


def build_messages(event_text: str, profile: dict[str, Any] | None = None) -> list[dict[str, str]]:
    if not str(event_text or "").strip():
        raise ValueError("event text is required")
    profile = profile if profile is not None else load_material_consequence_profile()
    user = USER_PROMPT_TEMPLATE.format(
        event=str(event_text).strip(),
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


def estimate_material_consequence_v1(
    event_text: str,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    """Call the S v1 model path. Never invent MATERIAL/NOT_MATERIAL on failure."""
    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    messages = build_messages(event_text, profile)
    last_error: BaseException | None = None
    transport_retries = 0
    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                MaterialConsequenceV1Response,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            return {
                "scorable": True,
                "material_consequence": obj.material_consequence,
                "affected_shared_systems": list(obj.affected_shared_systems),
                "material_changes": list(obj.material_changes),
                "reason": obj.reason,
                "failure_kind": None,
                "error": None,
                "transport_retries": transport_retries,
                "schema_events": events,
                "model_meta": dict(meta or {}),
            }
        except SchemaValidationError as exc:
            return {
                "scorable": False,
                "material_consequence": None,
                "affected_shared_systems": [],
                "material_changes": [],
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
                "material_consequence": None,
                "affected_shared_systems": [],
                "material_changes": [],
                "reason": None,
                "failure_kind": kind,
                "error": str(exc)[:1000],
                "transport_retries": transport_retries,
                "schema_events": [],
                "model_meta": None,
            }
    return {
        "scorable": False,
        "material_consequence": None,
        "affected_shared_systems": [],
        "material_changes": [],
        "reason": None,
        "failure_kind": "model_call",
        "error": str(last_error)[:1000] if last_error else "unknown model failure",
        "transport_retries": transport_retries,
        "schema_events": [],
        "model_meta": None,
    }


def compute_material_consequence_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [
        row for row in rows
        if row.get("scorable") and row.get("gold") in {"MATERIAL", "NOT_MATERIAL"}
    ]
    n = len(scored)
    n_gold_material = sum(row["gold"] == "MATERIAL" for row in scored)
    n_gold_not = sum(row["gold"] == "NOT_MATERIAL" for row in scored)
    n_pred_material = sum(row.get("prediction") == "MATERIAL" for row in scored)
    n_pred_not = sum(row.get("prediction") == "NOT_MATERIAL" for row in scored)
    exact = sum(row.get("prediction") == row.get("gold") for row in scored)
    true_material = sum(
        row.get("gold") == "MATERIAL" and row.get("prediction") == "MATERIAL"
        for row in scored
    )
    true_not = sum(
        row.get("gold") == "NOT_MATERIAL" and row.get("prediction") == "NOT_MATERIAL"
        for row in scored
    )
    false_material = sum(
        row.get("gold") == "NOT_MATERIAL" and row.get("prediction") == "MATERIAL"
        for row in scored
    )
    false_not = sum(
        row.get("gold") == "MATERIAL" and row.get("prediction") == "NOT_MATERIAL"
        for row in scored
    )

    material_recall = true_material / n_gold_material if n_gold_material else None
    not_material_recall = true_not / n_gold_not if n_gold_not else None
    recall_values = [x for x in (material_recall, not_material_recall) if x is not None]
    balanced = sum(recall_values) / len(recall_values) if recall_values else None

    return {
        "n_scored": n,
        "n_gold_material": n_gold_material,
        "n_gold_not_material": n_gold_not,
        "n_pred_material": n_pred_material,
        "n_pred_not_material": n_pred_not,
        "exact_accuracy": exact / n if n else None,
        "material_recall": material_recall,
        "not_material_recall": not_material_recall,
        "balanced_accuracy": balanced,
        "false_material_count": false_material,
        "false_material_rate": false_material / n if n else None,
        "false_not_material_count": false_not,
        "false_not_material_rate": false_not / n if n else None,
    }


def invocation_record(*, requested_model: str | None, provider_base_url: str | None, thinking_protocol: str | None) -> dict[str, Any]:
    return {
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "profile_id": PROFILE_ID,
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "thinking_protocol": thinking_protocol,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": TEMPERATURE,
        "response_format": "json_object",
        "structured_schema": "MaterialConsequenceV1Response",
    }
