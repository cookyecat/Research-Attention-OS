"""Standing Radar Fit (D) estimator v3 — eval/research only.

Clause-aware implementation of Standing Attention Jurisdiction.
Does not estimate S or P. Does not call production Attention Policy.

Prompt version: standing-radar-fit-v3
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "standing_radar_profile.v3.yaml"

ESTIMATOR_VERSION = "standing-radar-fit-estimator-v3"
PROMPT_VERSION = "standing-radar-fit-v3"
PROFILE_ID = "standing-radar-profile-v3"

THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.1

PROMPT_PROFILE_FIELDS = (
    "semantic_contract",
    "invariants",
    "standing_clauses",
    "scope_guards",
)

StandingRadarFitLabel = Literal["IN", "OUT"]

SYSTEM_PROMPT = """You estimate Standing Radar Fit (D) for Research Attention OS.

D definition:
D is Standing Attention Jurisdiction / Standing Radar Fit, independent of event significance.
It asks whether the stated event satisfies at least one stable Standing Radar Clause for the user.
Ignore importance, popularity, AWARE/DROP, S, P, Kernel relevance, cognitive change, and temporary current-project relevance.

Use this semantic procedure:
1. Understand the stated event semantically.
2. Identify all substantive radar anchors involved in the event. An anchor may be a topic, actor/entity/person, work/product/content object, place/governance scope, or stable affiliation described by the profile.
3. Do not collapse a multi-anchor event into one dominant domain.
4. Distinguish substantive involvement from incidental mention, ordinary tool use, implementation detail, organizational background, or application context.
5. Evaluate the event against every relevant Standing Radar Clause.
6. Return IN if at least one Standing Radar Clause is genuinely satisfied.
7. Treat scope guards only as guards against over-broad matching. They are not negative votes and must not veto an independently valid clause.

Do not invent unstated facts, relationships, affiliations, user interests, or downstream consequences.
Do not build a domain/entity/place ontology. Do not use numeric weights.

Return JSON only:
{
  "standing_radar_fit": "IN" or "OUT",
  "substantive_anchors": ["short semantic anchor", ...],
  "matched_clauses": ["short matching clause phrase", ...],
  "reason": "brief explanation"
}
Only standing_radar_fit is scored. The other fields are diagnostics only.
Keep reason short.
"""

USER_PROMPT_TEMPLATE = """Event:
{event}

Standing Radar profile:
{profile}
"""


class StandingRadarFitV3Response(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    standing_radar_fit: StandingRadarFitLabel
    substantive_anchors: list[str] = Field(default_factory=list)
    matched_clauses: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=700)


def prompt_sha256() -> str:
    payload = SYSTEM_PROMPT + "\n---\n" + USER_PROMPT_TEMPLATE + "\n---\n" + ",".join(PROMPT_PROFILE_FIELDS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_standing_radar_profile(path: Path | None = None) -> dict[str, Any]:
    import yaml

    raw = yaml.safe_load((path or PROFILE_PATH).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Standing Radar profile must be a mapping")
    missing = [key for key in PROMPT_PROFILE_FIELDS if key not in raw]
    if missing:
        raise ValueError(f"Standing Radar profile missing fields: {missing}")
    return {key: raw[key] for key in PROMPT_PROFILE_FIELDS}


def render_profile_for_prompt(profile: dict[str, Any]) -> str:
    import yaml

    allowed = {key: profile[key] for key in PROMPT_PROFILE_FIELDS}
    return yaml.safe_dump(allowed, sort_keys=False, allow_unicode=True).strip()


def build_messages(event_text: str, profile: dict[str, Any] | None = None) -> list[dict[str, str]]:
    if not str(event_text or "").strip():
        raise ValueError("event text is required")
    profile = profile if profile is not None else load_standing_radar_profile()
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


def estimate_standing_radar_fit_v3(
    event_text: str,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    """Call the frozen v3 model path. Never invent IN/OUT on failure."""
    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    messages = build_messages(event_text, profile)
    last_error: BaseException | None = None
    transport_retries = 0
    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                StandingRadarFitV3Response,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            return {
                "scorable": True,
                "standing_radar_fit": obj.standing_radar_fit,
                "substantive_anchors": list(obj.substantive_anchors),
                "matched_clauses": list(obj.matched_clauses),
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
                "standing_radar_fit": None,
                "substantive_anchors": [],
                "matched_clauses": [],
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
                "standing_radar_fit": None,
                "substantive_anchors": [],
                "matched_clauses": [],
                "reason": None,
                "failure_kind": kind,
                "error": str(exc)[:1000],
                "transport_retries": transport_retries,
                "schema_events": [],
                "model_meta": None,
            }
    return {
        "scorable": False,
        "standing_radar_fit": None,
        "substantive_anchors": [],
        "matched_clauses": [],
        "reason": None,
        "failure_kind": "model_call",
        "error": str(last_error)[:1000] if last_error else "unknown model failure",
        "transport_retries": transport_retries,
        "schema_events": [],
        "model_meta": None,
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
        "structured_schema": "StandingRadarFitV3Response",
    }
