"""Standing Radar Fit (D) estimator — eval/research only.

Estimates D = Standing Interest Fit independent of event significance.
Does not estimate S or P. Does not call production Attention Policy.

Prompt version: standing-radar-fit-v1
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "standing_radar_profile.v1.yaml"

ESTIMATOR_VERSION = "standing-radar-fit-estimator-v1"
PROMPT_VERSION = "standing-radar-fit-v1"
PROFILE_ID = "standing-radar-profile-v1"

# Frozen invocation settings. Matching-like semantic membership, existing client temperature.
THINKING: Literal["disabled"] = "disabled"
REASONING_EFFORT = None
TIMEOUT_SECONDS = 60.0
TEMPERATURE = 0.1  # app.cognitive.client.chat_json default; not overridden

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
Canonical question: Ignoring how important this particular event is, does its substantive topic belong to a world the user wants RAOS to monitor on a standing basis?

D is NOT:
- event significance S
- public-attention salience P
- AWARE or DROP disposition
- Kernel relevance
- cognitive change Delta
- current-project relevance
- keyword overlap

You receive a compact natural-language Standing Radar profile with only these fields:
semantic_contract, invariants, standing_interests, standing_exclusions.
Do not expand it into a taxonomy.

Invariants:
- Incidental mention or ordinary use of AI, GPU, Python, cloud, neural networks, or similar tools does not create radar membership.
- Judge the event that is stated. Do not invent unstated facts, actors, motivations, or downstream applications.
- D granularity follows stable user preference, not taxonomy depth.
- An ordinary event in a standing-interest area may still be D=IN even if the event is unimportant.
- An event outside the standing radar may later become AWARE through high S and high P. That possibility must not influence D.
- Do not estimate S or P.
- Do not answer AWARE/DROP.

Return JSON only:
{
  "standing_radar_fit": "IN" or "OUT",
  "matched_interests": ["short profile phrase", ...],
  "reason": "brief explanation"
}
Only standing_radar_fit is the D decision. matched_interests and reason are diagnostics.
Keep reason short.
"""

USER_PROMPT_TEMPLATE = """Event:
{event}

Standing Radar profile:
{profile}
"""


class StandingRadarFitResponse(BaseModel):
    """Structured D estimate. Only standing_radar_fit is scored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    standing_radar_fit: StandingRadarFitLabel
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


def estimate_standing_radar_fit(
    event_text: str,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    """Call the frozen model path. Never invent IN/OUT on failure."""
    from app.cognitive.client import LLMError, SchemaValidationError, chat_json_schema

    messages = build_messages(event_text, profile)
    last_error: BaseException | None = None
    transport_retries = 0
    for attempt in range(2):
        try:
            obj, meta, events = chat_json_schema(
                messages,
                StandingRadarFitResponse,
                chat_fn=chat_fn,
                thinking=THINKING,
                reasoning_effort=REASONING_EFFORT,
                timeout=TIMEOUT_SECONDS,
            )
            return {
                "scorable": True,
                "standing_radar_fit": obj.standing_radar_fit,
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
        "matched_interests": [],
        "reason": None,
        "failure_kind": "model_call",
        "error": str(last_error)[:1000] if last_error else "unknown model failure",
        "transport_retries": transport_retries,
        "schema_events": [],
        "model_meta": None,
    }


def compute_standing_radar_fit_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [
        row
        for row in rows
        if row.get("scorable")
        and row.get("gold") in {"IN", "OUT"}
        and row.get("prediction") in {"IN", "OUT"}
    ]
    n = len(scored)
    gold_in = [row for row in scored if row["gold"] == "IN"]
    gold_out = [row for row in scored if row["gold"] == "OUT"]
    pred_in = [row for row in scored if row["prediction"] == "IN"]
    pred_out = [row for row in scored if row["prediction"] == "OUT"]
    hits = sum(1 for row in scored if row["gold"] == row["prediction"])
    false_in = sum(1 for row in scored if row["prediction"] == "IN" and row["gold"] == "OUT")
    false_out = sum(1 for row in scored if row["prediction"] == "OUT" and row["gold"] == "IN")
    in_recall = (sum(1 for row in gold_in if row["prediction"] == "IN") / len(gold_in)) if gold_in else None
    out_recall = (sum(1 for row in gold_out if row["prediction"] == "OUT") / len(gold_out)) if gold_out else None
    balanced = None
    if in_recall is not None and out_recall is not None:
        balanced = (in_recall + out_recall) / 2
    exact = (hits / n) if n else None
    criterion = {
        "exact_accuracy_min": 0.80,
        "balanced_accuracy_min": 0.80,
        "no_clear_systematic_failure": "human_judgment_after_residuals",
    }
    metrics_pass = bool(
        exact is not None
        and balanced is not None
        and exact >= 0.80
        and balanced >= 0.80
    )
    return {
        "n_scored": n,
        "n_gold_in": len(gold_in),
        "n_gold_out": len(gold_out),
        "n_pred_in": len(pred_in),
        "n_pred_out": len(pred_out),
        "exact_accuracy": exact,
        "in_recall": in_recall,
        "out_recall": out_recall,
        "balanced_accuracy": balanced,
        "false_in_count": false_in,
        "false_in_rate": (false_in / n) if n else None,
        "false_out_count": false_out,
        "false_out_rate": (false_out / n) if n else None,
        "success_criterion": criterion,
        "metrics_pass": metrics_pass,
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
        "structured_schema": "StandingRadarFitResponse",
    }
