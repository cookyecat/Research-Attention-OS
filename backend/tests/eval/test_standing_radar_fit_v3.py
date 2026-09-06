"""Standing Radar Fit v3 Standing Attention Jurisdiction tests."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.standing_radar_fit_v3 import (
    ESTIMATOR_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    StandingRadarFitV3Response,
    build_messages,
    estimate_standing_radar_fit_v3,
    load_standing_radar_profile,
    prompt_sha256,
    render_profile_for_prompt,
)
from eval.live.run_standing_radar_fit_v3_eval import write_artifact


def test_v3_versions_are_distinct():
    assert ESTIMATOR_VERSION == "standing-radar-fit-estimator-v3"
    assert PROMPT_VERSION == "standing-radar-fit-v3"
    assert len(prompt_sha256()) == 64


def test_v3_prompt_encodes_jurisdiction_and_clause_semantics():
    blob = SYSTEM_PROMPT
    assert "Standing Attention Jurisdiction" in blob
    assert "substantive radar anchors" in blob
    assert "Standing Radar Clause" in blob
    assert "at least one Standing Radar Clause" in blob
    assert "not negative votes" in blob
    assert "numeric weights" in blob


def test_v3_profile_uses_clauses_not_domain_weights():
    profile = load_standing_radar_profile()
    assert "standing_clauses" in profile
    assert "scope_guards" in profile
    clauses = "\n".join(profile["standing_clauses"])
    assert "OpenAI" in clauses
    assert "direct-family affiliation" in clauses
    assert "hometown/local-governance" in clauses
    assert "weights" not in clauses.lower()


def test_v3_prompt_uses_only_allowed_profile_fields_and_no_old_cases():
    profile = load_standing_radar_profile()
    dumped = render_profile_for_prompt(profile)
    messages = build_messages("A generic event.", profile)
    blob = "\n".join(m["content"] for m in messages)
    assert "boundary_examples_non_gold" not in dumped
    for marker in ("FD6", "FD16", "IX2", "IX4", "RV4", "FV1", "BC1"):
        assert marker not in blob


def test_v3_schema_exposes_anchors_only_as_diagnostics():
    obj = StandingRadarFitV3Response.model_validate(
        {
            "standing_radar_fit": "IN",
            "substantive_anchors": ["robotics", "commercial-space company"],
            "matched_clauses": ["monitor substantive robotics"],
            "reason": "robotics is substantively involved",
        }
    )
    assert obj.standing_radar_fit == "IN"
    assert obj.substantive_anchors == ["robotics", "commercial-space company"]
    with pytest.raises(ValidationError):
        StandingRadarFitV3Response.model_validate(
            {
                "standing_radar_fit": "MAYBE",
                "substantive_anchors": [],
                "matched_clauses": [],
                "reason": "x",
            }
        )


def test_v3_estimator_fails_closed():
    from app.cognitive.client import LLMError

    def fake_chat(messages, **kwargs):
        return {
            "standing_radar_fit": "IN",
            "substantive_anchors": ["robotics"],
            "matched_clauses": ["robotics clause"],
            "reason": "substantive robotics",
        }, {"model": "fake-v3", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_standing_radar_fit_v3("A robot is developed.", chat_fn=fake_chat)
    assert out["scorable"] is True
    assert out["standing_radar_fit"] == "IN"

    def boom(messages, **kwargs):
        raise LLMError("provider 503 unavailable")

    failed = estimate_standing_radar_fit_v3("A robot is developed.", chat_fn=boom)
    assert failed["scorable"] is False
    assert failed["standing_radar_fit"] is None


def test_v3_is_eval_only_and_does_not_import_scheduler():
    source = inspect.getsource(estimate_standing_radar_fit_v3)
    assert "scheduler" not in source


def test_v3_first_run_artifact_is_write_once(tmp_path):
    path = tmp_path / "first_run.json"
    write_artifact({"ok": True}, path)
    with pytest.raises(FileExistsError):
        write_artifact({"ok": False}, path)
