from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.report import compute_metrics
from eval.live.run_live_eval import analysis_payload_to_eval_row, load_manifest, live_eval_runtime_fields, main, run_case, write_report
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
    rows = [json.loads(line) for line in (out / "cases.jsonl").read_text().splitlines() if line]
    assert rows
    assert all("stage_provenance" in r for r in rows)
    assert all(r["prediction_source"] is None for r in rows)
    assert all(r["model_prediction"] is None for r in rows)
    assert all("processing_mode" in r for r in rows)
    assert all("embedding_used" in r for r in rows)
    assert all("lexical_fallback" in r for r in rows)
    assert all("scheduler_features" in r for r in rows)


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


def test_live_eval_records_stage_provenance_and_visible_fallback(tmp_path):
    class FallbackProv:
        fallback_used = True
        provider_type = "model+rule-fallback"
        last_meta = {"latency_ms": 90, "prompt_tokens": 10, "completion_tokens": 3}
        stage_provenance = {
            "extraction": {
                "provider": "rule",
                "status": "fallback",
                "fallback_from": "model",
                "thinking": "disabled",
                "reasoning_effort": None,
                "timeout": 60.0,
                "latency_ms": 90,
                "prompt_tokens": 10,
                "completion_tokens": 3,
                "error_type": "timeout",
                "error": "timeout after 60.0s",
            }
        }

    fields = live_eval_runtime_fields(FallbackProv())
    assert fields["prediction_source"] == "rule-fallback"
    assert fields["model_prediction"] is False
    assert fields["fallback"] is True
    assert "extraction" in fields["fallback_stages"]
    assert fields["stage_provenance"]["extraction"]["error_type"] == "timeout"

    rows = [
        {
            "id": "fb",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "human_gold": {"attention_state": ["ENGAGE"]},
            **fields,
        }
    ]
    write_report(tmp_path / "fb", {"n_cases": 1}, rows)
    stored = json.loads((tmp_path / "fb" / "cases.jsonl").read_text().splitlines()[0])
    assert stored["stage_provenance"]["extraction"]["status"] == "fallback"
    assert stored["prediction_source"] == "rule-fallback"
    assert stored["model_prediction"] is False


def test_fallback_excluded_from_model_accuracy():
    rows = [
        {
            "id": "ok",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "human_gold": {"attention_state": ["ENGAGE"]},
            "prediction_source": "model",
            "fallback": False,
            "model_prediction": True,
        },
        {
            "id": "fb",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "human_gold": {"attention_state": ["ENGAGE"]},
            "prediction_source": "rule-fallback",
            "fallback": True,
            "model_prediction": False,
            "stage_provenance": {"extraction": {"status": "fallback", "provider": "rule"}},
        },
    ]
    metrics = compute_metrics(rows)
    assert metrics["n_labeled"] == 2
    assert metrics["n_fallback"] == 1
    assert metrics["fallback_excluded_from_model_metrics"] is True
    assert metrics["attention"]["denominator"] == 1
    assert metrics["attention"]["attention_accuracy"] == 1.0


def test_manifest_example_loads():
    manifest = load_manifest(ROOT / "eval" / "live" / "manifest.example.yaml")
    assert len(manifest.cases) >= 6
    assert all(gold_status_of(c) == "UNLABELED" for c in manifest.cases)


def test_live_eval_row_from_production_pipeline(client):
    from tests.conftest import add_text, analyze

    src = add_text(
        client,
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once.",
        title="live-map",
    )
    payload = analyze(client, src["id"])
    row = analysis_payload_to_eval_row(payload)
    assert row["attention_state"]
    assert row["processing_mode"] is not None
    assert isinstance(row["kernel_matches"], list)
    assert row["lexical_fallback"] is True
    assert row["scheduler_features"]
    assert "delta_summary" in row
    assert row["stage_provenance"] is not None


def test_live_eval_run_case_full_pipeline(client, engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        case = LiveCase(
            id="live-full-01",
            source=LiveSource(
                type="TEXT",
                title="zero-shot",
                text="The founder says the robot generalizes zero-shot. In the video, it succeeds once.",
            ),
            source_kind="news",
            kernel_fixture="mvp",
        )
        row = run_case(case, dry_run=False, db=session)
        assert not row.get("error"), row.get("error")
        assert row["attention_state"]
        assert row["delta_summary"] is not None
        assert row["lexical_fallback"] is True
        assert row["skipped"] is False
        assert "extraction" in (row.get("stage_provenance") or {})
    finally:
        session.close()
