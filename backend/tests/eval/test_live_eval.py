from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.report import compute_metrics
from eval.live.run_live_eval import load_manifest, main, write_report
from eval.live.schema import LiveCase, LiveSource, gold_status_of


def test_live_eval_dry_run(tmp_path):
    code = main(
        [
            "--dry-run",
            "--manifest",
            str(ROOT / "eval" / "live" / "manifest.example.yaml"),
            "--out-dir",
            str(tmp_path / "run1"),
            "--timestamp",
            "20000101T000000Z",
        ]
    )
    assert code == 0
    out = tmp_path / "run1"
    assert (out / "summary.json").exists()
    assert (out / "summary.md").exists()
    assert (out / "cases.jsonl").exists()
    summary = json.loads((out / "summary.json").read_text())
    assert summary["n_unlabeled"] == summary["n_cases"]
    assert summary["n_labeled"] == 0
    assert summary["unlabeled_excluded_from_accuracy"] is True
    assert summary["attention"]["denominator"] == 0
    assert summary["attention"]["attention_accuracy"] is None


def test_unlabeled_not_in_accuracy_denominator():
    rows = [
        {
            "id": "u1",
            "gold_status": "UNLABELED",
            "attention_state": "DROP",
            "human_gold": None,
        },
        {
            "id": "l1",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "human_gold": {"attention_state": ["ENGAGE"]},
            "claim_texts": [],
            "observation_texts": [],
        },
    ]
    metrics = compute_metrics(rows)
    assert metrics["n_labeled"] == 1
    assert metrics["n_unlabeled"] == 1
    assert metrics["attention"]["denominator"] == 1
    assert metrics["attention"]["attention_accuracy"] == 1.0


def test_live_eval_report_reproducible(tmp_path):
    rows = [
        {"id": "b", "gold_status": "UNLABELED", "attention_state": None},
        {"id": "a", "gold_status": "UNLABELED", "attention_state": None},
    ]
    summary = compute_metrics(rows)
    summary["timestamp"] = "fixed"
    write_report(tmp_path / "r1", summary, rows)
    write_report(tmp_path / "r2", summary, rows)
    assert (tmp_path / "r1" / "summary.json").read_text() == (tmp_path / "r2" / "summary.json").read_text()
    assert (tmp_path / "r1" / "cases.jsonl").read_text() == (tmp_path / "r2" / "cases.jsonl").read_text()
    assert (tmp_path / "r1" / "summary.md").read_text() == (tmp_path / "r2" / "summary.md").read_text()


def test_empty_gold_is_unlabeled():
    case = LiveCase(id="x", source=LiveSource(text=None), human_gold=None, gold_status="UNLABELED")
    assert gold_status_of(case) == "UNLABELED"


def test_manifest_example_loads():
    manifest = load_manifest(ROOT / "eval" / "live" / "manifest.example.yaml")
    assert len(manifest.cases) >= 6
    assert all(gold_status_of(c) == "UNLABELED" for c in manifest.cases)
