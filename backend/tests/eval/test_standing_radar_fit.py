"""Standing Radar Fit estimator tests. Do not load Human Gold labels here."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.standing_radar_fit import (
    ESTIMATOR_VERSION,
    PROMPT_PROFILE_FIELDS,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    StandingRadarFitResponse,
    TEMPERATURE,
    THINKING,
    TIMEOUT_SECONDS,
    build_messages,
    compute_standing_radar_fit_metrics,
    estimate_standing_radar_fit,
    load_standing_radar_profile,
    prompt_sha256,
    render_profile_for_prompt,
)
from eval.live.run_standing_radar_fit_eval import load_fit_manifest, run_manifest

GOLD_PATH = ROOT / "eval" / "live" / "manifest.standing_radar_fit_human_gold.v1.yaml"


def test_prompt_version_and_invocation_are_frozen():
    assert ESTIMATOR_VERSION == "standing-radar-fit-estimator-v1"
    assert PROMPT_VERSION == "standing-radar-fit-v1"
    assert THINKING == "disabled"
    assert TIMEOUT_SECONDS == 60.0
    assert TEMPERATURE == 0.1
    assert prompt_sha256() == prompt_sha256()
    assert len(prompt_sha256()) == 64


def test_profile_for_prompt_omits_boundary_examples():
    profile = load_standing_radar_profile()
    assert set(profile) == set(PROMPT_PROFILE_FIELDS)
    dumped = render_profile_for_prompt(profile)
    assert "boundary_examples_non_gold" not in dumped
    assert "Fusion research using a routine neural-network" not in dumped
    assert "space-repair robot" not in dumped.lower()
    text = SYSTEM_PROMPT + dumped
    for field in PROMPT_PROFILE_FIELDS:
        assert field in dumped or field in SYSTEM_PROMPT


def test_messages_contain_contract_and_exclude_policy_and_gold():
    profile = load_standing_radar_profile()
    messages = build_messages("A lab publishes a paper on an unrelated industrial process.", profile)
    blob = "\n".join(m["content"] for m in messages)
    assert "Standing Interest Fit independent of event significance" in blob
    assert "Incidental mention" in blob
    assert "Do not invent unstated facts" in blob
    assert "standing_interests" in blob
    assert "standing_exclusions" in blob
    assert "AWARE iff" not in blob
    assert "Human Gold" not in blob
    assert "FD1" not in blob
    assert "boundary_examples_non_gold" not in blob
    assert "DROP" in blob  # exclusion: do not answer DROP
    assert "keyword overlap" in blob
    assert inspect.getsource(estimate_standing_radar_fit).count("scheduler") == 0


def test_structured_output_schema_is_minimal():
    obj = StandingRadarFitResponse.model_validate(
        {"standing_radar_fit": "IN", "matched_interests": ["Quantum computing"], "reason": "topic match"}
    )
    assert obj.standing_radar_fit == "IN"
    with pytest.raises(ValidationError):
        StandingRadarFitResponse.model_validate({"standing_radar_fit": "MAYBE", "matched_interests": [], "reason": "x"})
    with pytest.raises(ValidationError):
        StandingRadarFitResponse.model_validate(
            {"standing_radar_fit": "OUT", "matched_interests": [], "reason": "x", "significance": "high"}
        )


def test_estimate_uses_chat_json_schema_and_does_not_fallback_on_failure(monkeypatch):
    from app.cognitive.client import LLMError

    calls = {"n": 0}

    def fake_chat(messages, **kwargs):
        calls["n"] += 1
        assert kwargs.get("thinking") == "disabled"
        assert kwargs.get("timeout") == 60.0
        blob = messages[0]["content"] + messages[1]["content"]
        assert "boundary_examples_non_gold" not in blob
        return {
            "standing_radar_fit": "OUT",
            "matched_interests": [],
            "reason": "outside standing interests",
        }, {"model": "fake-d", "latency_ms": 1, "prompt_tokens": 2, "completion_tokens": 3}

    out = estimate_standing_radar_fit("Ordinary municipal zoning hearing.", chat_fn=fake_chat)
    assert out["scorable"] is True
    assert out["standing_radar_fit"] == "OUT"
    assert calls["n"] == 1

    def boom(messages, **kwargs):
        raise LLMError("provider 503 unavailable")

    failed = estimate_standing_radar_fit("Ordinary municipal zoning hearing.", chat_fn=boom)
    assert failed["scorable"] is False
    assert failed["standing_radar_fit"] is None
    assert failed["failure_kind"] in {"model_call", "timeout"}
    assert failed["transport_retries"] == 1


def test_metrics_balanced_accuracy_handles_imbalance():
    rows = (
        [{"gold": "IN", "prediction": "IN", "scorable": True} for _ in range(15)]
        + [{"gold": "OUT", "prediction": "IN", "scorable": True} for _ in range(5)]
    )
    always_in = compute_standing_radar_fit_metrics(rows)
    assert always_in["n_scored"] == 20
    assert always_in["exact_accuracy"] == 0.75
    assert always_in["in_recall"] == 1.0
    assert always_in["out_recall"] == 0.0
    assert always_in["balanced_accuracy"] == 0.5
    assert always_in["metrics_pass"] is False
    mixed = compute_standing_radar_fit_metrics(
        [
            {"gold": "IN", "prediction": "IN", "scorable": True},
            {"gold": "IN", "prediction": "OUT", "scorable": True},
            {"gold": "OUT", "prediction": "OUT", "scorable": True},
            {"gold": "OUT", "prediction": "IN", "scorable": True},
        ]
    )
    assert mixed["exact_accuracy"] == 0.5
    assert mixed["balanced_accuracy"] == 0.5
    assert mixed["false_in_count"] == 1
    assert mixed["false_out_count"] == 1


def test_loader_and_dry_run_do_not_need_gold_file(tmp_path):
    path = tmp_path / "fixture.yaml"
    path.write_text(
        """
name: fixture-not-gold
cases:
  - id: T1
    event: A quantum computing lab reports a new qubit coherence result.
    gold_status: LABELED
    standing_radar_fit: IN
  - id: T2
    event: A municipal parking-rule change in an unrelated city.
    gold_status: LABELED
    standing_radar_fit: OUT
""",
        encoding="utf-8",
    )
    manifest = load_fit_manifest(path)
    assert [c["id"] for c in manifest["cases"]] == ["T1", "T2"]
    payload = run_manifest(path, score=False, dry_run=True)
    assert payload["dry_run"] is True
    assert payload["scored"] is False
    assert all(row["gold"] is None for row in payload["cases"])
    assert all(row["prediction"] is None for row in payload["cases"])


def test_estimator_source_does_not_embed_holdout_ids():
    source = (ROOT / "eval" / "live" / "standing_radar_fit.py").read_text(encoding="utf-8")
    assert "FD1" not in source
    assert "standing_radar_fit_human_gold" not in source
    assert GOLD_PATH.exists()
