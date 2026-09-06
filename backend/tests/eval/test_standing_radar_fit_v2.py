"""Standing Radar Fit v2 semantic-composition repair tests."""

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

from eval.live.standing_radar_fit_v2 import (
    ESTIMATOR_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    StandingRadarFitV2Response,
    build_messages,
    estimate_standing_radar_fit_v2,
    load_standing_radar_profile,
    prompt_sha256,
    render_profile_for_prompt,
)
from eval.live.run_standing_radar_fit_v2_eval import write_artifact


def test_v2_versions_are_distinct_from_v1():
    assert ESTIMATOR_VERSION == "standing-radar-fit-estimator-v2"
    assert PROMPT_VERSION == "standing-radar-fit-v2"
    assert len(prompt_sha256()) == 64


def test_v2_prompt_encodes_minimal_semantic_composition_repair():
    blob = SYSTEM_PROMPT
    assert "all substantive semantic facets" in blob
    assert "Do not collapse a multi-facet event into one dominant domain" in blob
    assert "at least one substantive facet genuinely matches" in blob
    assert "scope guards against over-broad matching" in blob
    assert "must not veto" in blob
    assert "numeric domain weights" in blob


def test_v2_profile_scope_matches_calibrated_cancer_preference():
    profile = load_standing_radar_profile()
    interests = "\n".join(profile["standing_interests"])
    exclusions = "\n".join(profile["standing_exclusions"])
    invariants = "\n".join(profile["invariants"])
    assert "Cancer and tumor research and field development" in interests
    assert "routine local hospital adoption/operation" in interests
    assert "research-and-field-development scope" in exclusions
    assert "routine local organizational adoption/operation" in invariants


def test_v2_prompt_uses_only_allowed_profile_fields_and_no_old_cases():
    profile = load_standing_radar_profile()
    dumped = render_profile_for_prompt(profile)
    messages = build_messages("A generic event.", profile)
    blob = "\n".join(m["content"] for m in messages)
    assert "boundary_examples_non_gold" not in dumped
    assert "FD6" not in blob
    assert "FD16" not in blob
    assert "IX2" not in blob
    assert "IX4" not in blob
    assert "standing_radar_fit_human_gold" not in blob
    assert "standing_radar_intersection_diag" not in blob


def test_v2_schema_exposes_facets_only_as_diagnostics():
    obj = StandingRadarFitV2Response.model_validate(
        {
            "standing_radar_fit": "IN",
            "substantive_facets": ["robotics", "space operations"],
            "matched_interests": ["Robotics"],
            "reason": "robotics is substantive",
        }
    )
    assert obj.standing_radar_fit == "IN"
    assert obj.substantive_facets == ["robotics", "space operations"]
    with pytest.raises(ValidationError):
        StandingRadarFitV2Response.model_validate(
            {
                "standing_radar_fit": "MAYBE",
                "substantive_facets": [],
                "matched_interests": [],
                "reason": "x",
            }
        )


def test_v2_estimator_fails_closed(monkeypatch):
    from app.cognitive.client import LLMError

    def fake_chat(messages, **kwargs):
        return {
            "standing_radar_fit": "IN",
            "substantive_facets": ["robotics"],
            "matched_interests": ["Robotics"],
            "reason": "substantive robotics",
        }, {"model": "fake-v2", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_standing_radar_fit_v2("A robot is developed.", chat_fn=fake_chat)
    assert out["scorable"] is True
    assert out["standing_radar_fit"] == "IN"

    def boom(messages, **kwargs):
        raise LLMError("provider 503 unavailable")

    failed = estimate_standing_radar_fit_v2("A robot is developed.", chat_fn=boom)
    assert failed["scorable"] is False
    assert failed["standing_radar_fit"] is None


def test_v2_is_eval_only_and_does_not_import_scheduler():
    source = inspect.getsource(estimate_standing_radar_fit_v2)
    assert "scheduler" not in source


def test_v2_first_run_artifact_is_write_once(tmp_path):
    path = tmp_path / "first_run.json"
    write_artifact({"ok": True}, path)
    with pytest.raises(FileExistsError):
        write_artifact({"ok": False}, path)
