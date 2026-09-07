"""Standing Radar Fit (D) estimator v4 user-profile binding.

D semantics and the LLM semantic procedure are unchanged from estimator v3.
Version v4 binds the estimator to the user's post-IA calibrated Standing Radar
Clause profile and records the profile hash separately for provenance.

This is user-parameter calibration, not a new D semantic definition and not
fresh validation evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from eval.live import standing_radar_fit_v3 as v3

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "eval" / "live" / "standing_radar_profile.v4.yaml"

ESTIMATOR_VERSION = "standing-radar-fit-estimator-v4"
PROMPT_VERSION = v3.PROMPT_VERSION
PROFILE_ID = "standing-radar-profile-v4"

THINKING = v3.THINKING
REASONING_EFFORT = v3.REASONING_EFFORT
TIMEOUT_SECONDS = v3.TIMEOUT_SECONDS
TEMPERATURE = v3.TEMPERATURE
SYSTEM_PROMPT = v3.SYSTEM_PROMPT
USER_PROMPT_TEMPLATE = v3.USER_PROMPT_TEMPLATE
PROMPT_PROFILE_FIELDS = v3.PROMPT_PROFILE_FIELDS
StandingRadarFitV4Response = v3.StandingRadarFitV3Response


def prompt_sha256() -> str:
    # Semantic estimator procedure is intentionally unchanged from v3.
    return v3.prompt_sha256()


def profile_sha256(path: Path | None = None) -> str:
    payload = (path or PROFILE_PATH).read_bytes()
    return hashlib.sha256(payload).hexdigest()


def load_standing_radar_profile(path: Path | None = None) -> dict[str, Any]:
    return v3.load_standing_radar_profile(path or PROFILE_PATH)


def build_messages(event_text: str, profile: dict[str, Any] | None = None) -> list[dict[str, str]]:
    return v3.build_messages(
        event_text,
        profile if profile is not None else load_standing_radar_profile(),
    )


def estimate_standing_radar_fit_v4(
    event_text: str,
    *,
    profile: dict[str, Any] | None = None,
    chat_fn=None,
) -> dict[str, Any]:
    return v3.estimate_standing_radar_fit_v3(
        event_text,
        profile=profile if profile is not None else load_standing_radar_profile(),
        chat_fn=chat_fn,
    )


def invocation_record(
    *,
    requested_model: str | None,
    provider_base_url: str | None,
    thinking_protocol: str | None,
) -> dict[str, Any]:
    return {
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "profile_id": PROFILE_ID,
        "profile_sha256": profile_sha256(),
        "requested_model": requested_model,
        "provider_base_url": provider_base_url,
        "thinking_protocol": thinking_protocol,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "timeout_seconds": TIMEOUT_SECONDS,
        "temperature": TEMPERATURE,
        "response_format": "json_object",
        "structured_schema": "StandingRadarFitV4Response",
    }
