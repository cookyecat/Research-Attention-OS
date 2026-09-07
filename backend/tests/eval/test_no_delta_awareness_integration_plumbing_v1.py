"""Regression tests for integrated no-Delta AWARE measurement plumbing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import eval.live.run_no_delta_awareness_integration_v1_eval as runner
from eval.live.run_no_delta_awareness_integration_v1_eval import DEFAULT_GOLD, DEFAULT_TEMPLATE


def test_integrated_harness_loads_repo_env_before_scheduler_import():
    path = ROOT / "eval" / "live" / "no_delta_awareness_integration_v1.py"
    source = path.read_text(encoding="utf-8")
    assert source.index("load_repo_env()") < source.index("from app.services.scheduler import")


def test_integrated_runner_refuses_missing_runtime_api_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_api_key", None)
    with pytest.raises(RuntimeError, match="RAOS_LLM_API_KEY is unavailable"):
        runner.run_integrated_v1(
            DEFAULT_TEMPLATE,
            DEFAULT_GOLD,
            dry_run=False,
        )


def test_partial_component_results_survive_other_component_failure(monkeypatch):
    def fake_integrated(event_text, p_packet, **kwargs):
        return {
            "scorable": False,
            "disposition": None,
            "gate_wiring_matches": None,
            "component_scorable": {"D": False, "S": True, "P": True},
            "D": {
                "scorable": False,
                "standing_radar_fit": None,
                "failure_kind": "model_call",
                "error": "synthetic D failure",
                "model_meta": None,
            },
            "S": {
                "scorable": True,
                "material_consequence": "MATERIAL",
                "failure_kind": None,
                "error": None,
                "model_meta": {"model": "fake-s"},
            },
            "P": {
                "scorable": True,
                "collective_attention_salience": "SALIENT",
                "failure_kind": None,
                "error": None,
                "model_meta": {"model": "fake-p"},
            },
        }

    monkeypatch.setattr(runner, "estimate_integrated_no_delta_awareness_v1", fake_integrated)

    # Supplying all chat fns bypasses real credential preflight; fake_integrated ignores them.
    dummy = lambda *args, **kwargs: None
    out = runner.run_integrated_v1(
        DEFAULT_TEMPLATE,
        DEFAULT_GOLD,
        dry_run=False,
        d_chat_fn=dummy,
        s_chat_fn=dummy,
        p_chat_fn=dummy,
    )

    assert out["metrics"]["D"]["n_scored"] == 0
    assert out["metrics"]["S"]["n_scored"] == 12
    assert out["metrics"]["P"]["n_scored"] == 12
    assert out["metrics"]["final"]["n_scored"] == 0
    assert out["actual_models"]["S"] == ["fake-s"]
    assert out["actual_models"]["P"] == ["fake-p"]
    assert out["n_component_failures"] == 12
