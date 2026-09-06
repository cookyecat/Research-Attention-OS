"""Collective Attention Salience (P) final fresh runner plumbing tests."""

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

from eval.live.run_collective_attention_v1_eval import (
    DEFAULT_GOLD,
    DEFAULT_TEMPLATE,
    ESTIMATOR_FREEZE_DECLARATION_COMMIT,
    FRESH_TEMPLATE_COMMIT,
    HUMAN_GOLD_COMMIT,
    EXPECTED_CASE_IDS,
    join_template_and_gold,
    load_fresh_template,
    load_human_gold,
    run_final_fresh_v1,
    validate_manifest_provenance,
    write_artifact,
)


def test_p_final_fresh_manifests_join_exact_pf1_pf12():
    template = load_fresh_template(DEFAULT_TEMPLATE)
    gold = load_human_gold(DEFAULT_GOLD)
    validate_manifest_provenance(template, gold)
    joined = join_template_and_gold(template, gold)

    assert tuple(case["id"] for case in joined) == EXPECTED_CASE_IDS
    assert len(joined) == 12
    assert sum(case["gold"] == "SALIENT" for case in joined) == 6
    assert sum(case["gold"] == "NOT_SALIENT" for case in joined) == 6
    assert all("packet" in case for case in joined)


def test_p_final_fresh_provenance_is_fixed_not_measurement_head():
    template = load_fresh_template(DEFAULT_TEMPLATE)
    gold = load_human_gold(DEFAULT_GOLD)
    validate_manifest_provenance(template, gold)

    assert template["estimator_freeze_declaration_commit"] == ESTIMATOR_FREEZE_DECLARATION_COMMIT
    assert gold["fresh_template_commit"] == FRESH_TEMPLATE_COMMIT
    assert HUMAN_GOLD_COMMIT == "1b6bfb23a84411701cbee84caecf271e672e807b"

    bad = dict(gold)
    bad["prompt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance mismatch"):
        validate_manifest_provenance(template, bad)


def test_p_final_fresh_dry_run_validates_packets_without_model_call():
    called = False

    def should_not_call(messages, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("dry run must not call model")

    payload = run_final_fresh_v1(dry_run=True, score=True, chat_fn=should_not_call)
    assert called is False
    assert payload["n_cases"] == 12
    assert payload["metrics"] is None
    assert payload["scored"] is False
    assert payload["estimator_freeze_declaration_commit"] == ESTIMATOR_FREEZE_DECLARATION_COMMIT
    assert payload["fresh_template_commit"] == FRESH_TEMPLATE_COMMIT
    assert payload["human_gold_commit"] == HUMAN_GOLD_COMMIT
    assert all(row.get("dry_run") is True for row in payload["cases"])
    assert all(row.get("prompt_chars", 0) > 0 for row in payload["cases"])


def test_p_final_fresh_fake_measurement_plumbing_and_metrics():
    def always_salient(messages, **kwargs):
        return {
            "measurement_status": "scorable",
            "collective_attention_salience": "SALIENT",
            "objective_constituency": "test constituency",
            "attention_state_summary": "test evidence summary",
            "inertia_summary": "test history summary",
            "reason": "test measurement",
        }, {"model": "fake-p-final-v1", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    payload = run_final_fresh_v1(dry_run=False, score=True, chat_fn=always_salient)
    metrics = payload["metrics"]
    assert metrics["n_scored"] == 12
    assert metrics["n_gold_salient"] == 6
    assert metrics["n_gold_not_salient"] == 6
    assert metrics["n_pred_salient"] == 12
    assert metrics["exact_accuracy"] == pytest.approx(0.5)
    assert metrics["salient_recall"] == pytest.approx(1.0)
    assert metrics["not_salient_recall"] == pytest.approx(0.0)
    assert payload["n_insufficient_evidence"] == 0
    assert payload["n_technical_failures"] == 0
    assert payload["actual_models"] == ["fake-p-final-v1"]


def test_p_final_fresh_insufficient_evidence_is_separate_from_technical_failure():
    def insufficient(messages, **kwargs):
        return {
            "measurement_status": "insufficient_evidence",
            "collective_attention_salience": None,
            "objective_constituency": "test constituency",
            "attention_state_summary": "not enough current evidence",
            "inertia_summary": "history does not resolve it",
            "reason": "insufficient evidence",
        }, {"model": "fake-p-final-v1", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    payload = run_final_fresh_v1(dry_run=False, score=True, chat_fn=insufficient)
    assert payload["n_insufficient_evidence"] == 12
    assert payload["n_technical_failures"] == 0
    assert payload["metrics"]["n_scored"] == 0


def test_p_final_fresh_artifact_is_write_once(tmp_path):
    path = tmp_path / "collective_attention_v1_final_fresh_first_run.json"
    write_artifact({"ok": True}, path)
    with pytest.raises(FileExistsError):
        write_artifact({"ok": False}, path)
