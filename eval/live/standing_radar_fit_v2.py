"""Standing Radar Fit (D) estimator v2 — eval/research only.

Minimal semantic-composition repair of v1.
Does not estimate S or P. Does not call production Attention Policy.

Prompt version: standing-radar-fit-v2
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "standing_radar_profile.v2.yaml"

ESTIMATOR_VERSION = "standing-radar-fit-estimator-v2"
PROMPT_VERSION = "standing-radar-fit-v2"
PROFILE_ID = "standing-radar-profile-v2"

THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.1

PROMPT_PROFILE_FIELDS = (
    "semantic_contract",
    "invariants",
    "standing_interests",
    "standing_exclusions",
)

StandingRadarFitLabel = Literal["IN", "OUT"]

SYSTEM_PROMPT = """You estimate Standing Radar Fit (D) for Research Attention OS.

D definition:
D is Standing Interest Fit independent of event significance.
Ignore importance, popularity, AWARE/DROP, S, P, Kernel relevance, cognitive change, and current-project relevance.

Use this semantic procedure:
1. Identify all substantive semantic facets of the stated event.
2. Do not collapse a multi-facet event into one dominant domain.
3. Distinguish substantive facets from incidental tools, implementation details, organizational context, and application setting.
4. Compare each substantive facet against the Standing Radar profile.
5. Return IN if at least one substantive facet genuinely matches a standing interest.
6. Treat standing_exclusions only as scope guards against over-broad matching. An exclusion must not veto an independently substantive standing-interest facet.

A substantive facet is itself part of what is being developed, released, studied, deployed, measured, changed, or operated in the event. Merely using AI/GPU/Python/cloud/neural networks or occurring inside an excluded industry is not enough by itself.

Judge only facts stated in the event. Do not invent unstated actors, motivations, applications, or downstream consequences.
Do not build a domain taxonomy. Do not use numeric domain weights.

Return JSON only:
{
  "standing_radar_fit": "IN" or "OUT",
  "substantive_facets": ["short semantic facet", ...],
  "matched_interests": ["short profile phrase", ...],
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


class StandingRadarFitV2Response(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    standing_radar_fit: StandingRadarFitLabel
    substantive_facets: list[str] = Field(default_factory=list)
    matched_interests: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=600)


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


def estimate_standing_radar_fit_v2(
    event_text: str,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    """Call the frozen v2 model path. Never invent IN/OUT on failure."""
    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    messages = build_messages(event_text, profile)
    last_error: BaseException | None = None
    transport_retries = 0
    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                StandingRadarFitV2Response,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            return {
                "scorable": True,
                "standing_radar_fit": obj.standing_radar_fit,
                "substantive_facets": list(obj.substantive_facets),
                "matched_interests": list(obj.matched_interests),
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
                "substantive_facets": [],
                "matched_interests": [],
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
                "substantive_facets": [],
                "matched_interests": [],
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
        "substantive_facets": [],
        "matched_interests": [],
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
        "structured_schema": "StandingRadarFitV2Response",
    }
