from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.report import compute_metrics, render_markdown
from eval.live.run_live_eval import analysis_payload_to_eval_row, load_manifest, live_eval_runtime_fields, main, run_case, write_report
from eval.live.schema import (
    ATTENTION_STATES,
    COGNITIVE_EFFECTS,
    HUMAN_GOLD_TEMPLATE,
    KERNEL_TARGET_NONE,
    PROCESSING_MODES,
    HumanGold,
    LiveCase,
    LiveSource,
    dump_human_gold,
    gold_status_of,
)


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


def test_minimal_v2_human_gold_parses_and_is_labeled():
    gold = HumanGold.model_validate(
        {
            "attention_state": ["ENGAGE"],
            "processing_modes": ["VERIFY", "SYNTHESIZE"],
            "kernel_targets": ["Motor Intelligence"],
            "cognitive_effects": ["REFINE", "REINFORCE"],
            "expected_delta": "Refine the motor/cognitive split if the architecture is hierarchical.",
        }
    )
    assert set(gold.attention_state) <= set(ATTENTION_STATES)
    assert set(gold.processing_modes) <= set(PROCESSING_MODES)
    assert set(gold.cognitive_effects) <= set(COGNITIVE_EFFECTS)
    assert gold.kernel_targets == ["Motor Intelligence"]
    assert "must_match_kernel" not in dump_human_gold(gold)
    assert "forbidden_effects" not in dump_human_gold(gold)
    case = LiveCase(id="v2-min", source=LiveSource(text="x"), human_gold=gold)
    assert gold_status_of(case) == "LABELED"
    assert list(HUMAN_GOLD_TEMPLATE) == [
        "attention_state",
        "processing_modes",
        "kernel_targets",
        "cognitive_effects",
        "expected_delta",
    ]


def test_multiple_acceptable_attention_modes_and_effects():
    gold = HumanGold(
        attention_state=["ENGAGE", "WATCH"],
        processing_modes=["VERIFY", "SYNTHESIZE", "LEARN"],
        kernel_targets=["Motor Intelligence", "NONE"],
        cognitive_effects=["REFINE", "OPEN_NEW"],
        expected_delta="Either refine Motor Intelligence or open a new question.",
    )
    pairs = gold.target_effect_pairs()
    assert pairs == [("Motor Intelligence", ["REFINE"]), ("NONE", ["OPEN_NEW"])]


def test_kernel_target_none_is_expressible():
    gold = HumanGold(
        attention_state=["AWARE"],
        processing_modes=["SCAN"],
        kernel_targets=[KERNEL_TARGET_NONE],
        cognitive_effects=["NO_MATERIAL_CHANGE"],
        expected_delta="No Kernel target; nothing material to absorb.",
    )
    assert gold.kernel_targets == ["NONE"]
    assert gold.target_effect_pairs() == [("NONE", ["NO_MATERIAL_CHANGE"])]


def test_legacy_manifest_gold_still_parses():
    gold = HumanGold.model_validate(
        {
            "attention_state": ["ENGAGE"],
            "acceptable_modes": ["VERIFY"],
            "must_match_kernel": ["Motor Intelligence"],
            "expected_effects": [{"target_kernel": "Motor Intelligence", "acceptable_effects": ["REFINE"]}],
            "key_claims": ["zero-shot"],
            "delta_rubric": 2,
        }
    )
    assert gold.processing_modes == ["VERIFY"]
    assert gold.kernel_targets == ["Motor Intelligence"]
    assert "REFINE" in gold.cognitive_effects
    dumped = dump_human_gold(gold)
    assert dumped["processing_modes"] == ["VERIFY"]
    assert dumped["must_match_kernel"] == ["Motor Intelligence"]
    assert dumped["key_claims"] == ["zero-shot"]


def test_report_scores_v2_core_fields_not_legacy_keys():
    rows = [
        {
            "id": "v2",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "processing_modes": ["VERIFY", "SYNTHESIZE"],
            "matched_kernel_titles": ["Motor Intelligence"],
            "matched_kernel_ids": ["abc"],
            "kernel_matches": [{"node_id": "abc", "title": "Motor Intelligence"}],
            "cognitive_impact": {
                "effects": [
                    {
                        "target_kernel_node_id": "abc",
                        "effect": "REFINE",
                    }
                ]
            },
            "human_gold": {
                "attention_state": ["ENGAGE", "WATCH"],
                "processing_modes": ["VERIFY", "SYNTHESIZE", "LEARN"],
                "kernel_targets": ["Motor Intelligence"],
                "cognitive_effects": ["REFINE", "REINFORCE"],
                "expected_delta": "Refine the motor/cognitive split.",
            },
            "prediction_source": "model",
            "fallback": False,
            "model_prediction": True,
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["attention"]["attention_accuracy"] == 1.0
    assert metrics["processing_mode"]["processing_mode_accuracy"] == 1.0
    assert metrics["kernel_target"]["kernel_target_accuracy"] == 1.0
    assert metrics["cognitive_effect"]["cognitive_effect_accuracy"] == 1.0
    assert metrics["expected_delta"]["n_with_expected_delta"] == 1
    assert metrics["expected_delta"]["auto_scored"] is False
    md = render_markdown(metrics)
    assert "## Attention" in md
    assert "## Processing Mode" in md
    assert "## Kernel Target" in md
    assert "## Cognitive Effect" in md
    assert "## Expected Delta" in md
    assert "Must-Match Recall" in md
    assert "key_claims" not in md


def test_report_kernel_none_and_legacy_must_match_still_readable():
    none_row = {
        "id": "none",
        "gold_status": "LABELED",
        "attention_state": "AWARE",
        "processing_modes": ["SCAN"],
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "cognitive_impact": {
            "effects": [{"target_kernel_node_id": None, "effect": "NO_MATERIAL_CHANGE"}]
        },
        "human_gold": {
            "attention_state": ["AWARE", "DROP"],
            "processing_modes": ["SCAN"],
            "kernel_targets": ["NONE"],
            "cognitive_effects": ["NO_MATERIAL_CHANGE"],
            "expected_delta": "Nothing to absorb.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    legacy_row = {
        "id": "legacy",
        "gold_status": "LABELED",
        "attention_state": "ENGAGE",
        "processing_modes": ["VERIFY"],
        "matched_kernel_titles": ["Motor Intelligence"],
        "matched_kernel_ids": [],
        "kernel_matches": [{"node_id": "n1", "title": "Motor Intelligence"}],
        "cognitive_impact": {"effects": [{"target_kernel_node_id": "n1", "effect": "REFINE"}]},
        "human_gold": {
            "attention_state": ["ENGAGE"],
            "must_match_kernel": ["Motor Intelligence"],
            "acceptable_modes": ["VERIFY", "SYNTHESIZE"],
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    metrics = compute_metrics([none_row, legacy_row])
    assert metrics["kernel_target"]["kernel_target_none_accuracy"] == 1.0
    assert metrics["kernel_target"]["kernel_target_accuracy"] == 1.0
    assert metrics["processing_mode"]["processing_mode_accuracy"] == 1.0
    assert metrics["n_labeled"] == 2


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
