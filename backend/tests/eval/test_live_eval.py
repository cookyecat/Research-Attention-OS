from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.kernel_snapshot import kernel_snapshot_picker
from eval.live.report import compute_metrics, render_markdown
from eval.live.run_live_eval import analysis_payload_to_eval_row, load_manifest, live_eval_runtime_fields, main, run_case, write_report
from eval.live.schema import (
    DISPOSITIONS,
    HUMAN_GOLD_TEMPLATE,
    UPDATE_OPERATIONS,
    CognitiveUpdate,
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
    assert summary["disposition"]["denominator"] == 0
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
            "human_gold": {
                "disposition": "ENGAGE",
                "update": {"operation": "OPEN_NEW", "target_node_id": None},
                "delta_content": "A new question about whether this is worth a branch.",
            },
            "cognitive_impact": {"effects": [{"target_kernel_node_id": None, "effect": "OPEN_NEW"}]},
            "claim_texts": [],
            "observation_texts": [],
        },
    ]
    metrics = compute_metrics(rows)
    assert metrics["n_labeled"] == 1
    assert metrics["n_unlabeled"] == 1
    assert metrics["disposition"]["denominator"] == 1
    assert metrics["disposition"]["disposition_accuracy"] == 1.0


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


def test_minimal_human_gold_parses_and_is_labeled():
    gold = HumanGold.model_validate(
        {
            "disposition": "WATCH",
            "update": {"operation": "REINFORCE", "target_node_id": "P1"},
            "delta_content": "Motor Intelligence is more clearly a separable control loop, not a proof from the source.",
        }
    )
    assert gold.disposition in DISPOSITIONS
    assert gold.update is not None
    assert gold.update.operation in UPDATE_OPERATIONS
    assert gold.update.target_node_id == "P1"
    dumped = dump_human_gold(gold)
    assert dumped["disposition"] == "WATCH"
    assert dumped["update"] == {"operation": "REINFORCE", "target_node_id": "P1"}
    assert dumped["delta_content"]
    assert set(dumped) == {"disposition", "update", "delta_content"}
    assert list(HUMAN_GOLD_TEMPLATE) == ["disposition", "update", "delta_content"]
    case = LiveCase(id="min", source=LiveSource(text="x"), human_gold=gold)
    assert gold_status_of(case) == "LABELED"


def test_reinforce_valid_target():
    gold = HumanGold(
        disposition="WATCH",
        update=CognitiveUpdate(operation="REINFORCE", target_node_id="P1"),
        delta_content="The existing Motor Intelligence branch is strengthened, not replaced.",
    )
    assert gold.update.target_node_id == "P1"


def test_challenge_valid_target():
    gold = HumanGold.model_validate(
        {
            "disposition": "ENGAGE",
            "update": {"operation": "CHALLENGE", "target_node_id": "B1"},
            "delta_content": "The unified-model belief now needs a narrower scope for high-frequency control.",
        }
    )
    assert gold.update.operation == "CHALLENGE"
    assert gold.update.target_node_id == "B1"


def test_open_new_null_target():
    gold = HumanGold.model_validate(
        {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "A new branch: whether household folding skill transfer is its own question.",
        }
    )
    assert gold.update.operation == "OPEN_NEW"
    assert gold.update.target_node_id is None


def test_open_new_empty_string_target_is_null():
    gold = HumanGold.model_validate(
        {
            "disposition": "AWARE",
            "update": {"operation": "OPEN_NEW", "target_node_id": ""},
            "delta_content": "Opened a new watchline rather than attaching to an existing node.",
        }
    )
    assert gold.update.target_node_id is None


def test_illegal_operation_rejected():
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "WATCH",
                "update": {"operation": "REFINE", "target_node_id": "P1"},
                "delta_content": "should not parse",
            }
        )
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "WATCH",
                "update": {"operation": "NO_MATERIAL_CHANGE", "target_node_id": None},
                "delta_content": "should not parse",
            }
        )


def test_reinforce_and_challenge_require_target():
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "WATCH",
                "update": {"operation": "REINFORCE", "target_node_id": None},
                "delta_content": "missing target",
            }
        )
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "ENGAGE",
                "update": {"operation": "CHALLENGE"},
                "delta_content": "missing target",
            }
        )


def test_open_new_rejects_target():
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "WATCH",
                "update": {"operation": "OPEN_NEW", "target_node_id": "P1"},
                "delta_content": "should not attach to an existing node",
            }
        )


def test_illegal_disposition_rejected():
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "SCAN",
                "update": {"operation": "OPEN_NEW", "target_node_id": None},
                "delta_content": "SCAN is not a disposition",
            }
        )


def test_target_is_snapshot_picker_not_ontology():
    picker = kernel_snapshot_picker("mvp")
    assert picker
    assert all(set(item) == {"id", "title"} for item in picker)
    assert all("PROJECT" not in item["title"] for item in picker)
    gold = HumanGold.model_validate(
        {
            "disposition": "WATCH",
            "update": {"operation": "REINFORCE", "target_node_id": "Motor Intelligence"},
            "delta_content": "Picker titles resolve to snapshot ids internally.",
        }
    )
    assert gold.update.target_node_id == "P1"


def test_unknown_snapshot_target_rejected():
    with pytest.raises(ValidationError):
        HumanGold.model_validate(
            {
                "disposition": "WATCH",
                "update": {"operation": "REINFORCE", "target_node_id": "not-a-kernel-node"},
                "delta_content": "cannot invent a target",
            }
        )


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
    assert gold.disposition == "ENGAGE"
    assert gold.update is not None
    assert gold.update.operation == "REINFORCE"
    assert gold.update.target_node_id == "P1"
    dumped = dump_human_gold(gold)
    assert dumped["disposition"] == "ENGAGE"
    assert dumped["update"]["operation"] == "REINFORCE"
    assert dumped["update"]["target_node_id"] == "P1"
    assert set(dumped) == {"disposition", "update", "delta_content"}
    assert gold.must_match_kernel == ["Motor Intelligence"]
    assert gold.key_claims == ["zero-shot"]


def test_report_scores_new_contract_fields():
    rows = [
        {
            "id": "v3",
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
                        "effect": "REINFORCE",
                    }
                ]
            },
            "human_gold": {
                "disposition": "ENGAGE",
                "update": {"operation": "REINFORCE", "target_node_id": "P1"},
                "delta_content": "The motor/cognitive split is a clearer existing branch, not a source proof.",
            },
            "prediction_source": "model",
            "fallback": False,
            "model_prediction": True,
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["disposition"]["disposition_accuracy"] == 1.0
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["target_accuracy"] == 1.0
    assert metrics["delta_content"]["n_with_delta_content"] == 1
    assert metrics["delta_content"]["auto_scored"] is False
    md = render_markdown(metrics)
    assert "## Disposition" in md
    assert "## Update Operation" in md
    assert "## Target" in md
    assert "## Delta Content" in md
    assert "attention_state" not in md
    assert "Processing Mode" not in md
    assert "key_claims" not in md


def test_report_maps_legacy_gold_and_refine_prediction():
    none_row = {
        "id": "open",
        "gold_status": "LABELED",
        "attention_state": "AWARE",
        "processing_modes": ["SCAN"],
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "cognitive_impact": {
            "effects": [{"target_kernel_node_id": None, "effect": "OPEN_NEW"}]
        },
        "human_gold": {
            "disposition": "AWARE",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "Nothing in the current Kernel is the right landing spot.",
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
            "expected_effects": [{"target_kernel": "Motor Intelligence", "acceptable_effects": ["REFINE"]}],
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    metrics = compute_metrics([none_row, legacy_row])
    assert metrics["disposition"]["disposition_accuracy"] == 1.0
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["target_accuracy"] == 1.0
    assert metrics["n_labeled"] == 2


def test_legacy_no_material_change_does_not_become_open_new():
    gold = HumanGold.model_validate(
        {
            "attention_state": ["AWARE"],
            "kernel_targets": ["NONE"],
            "cognitive_effects": ["NO_MATERIAL_CHANGE"],
        }
    )
    assert gold.disposition == "AWARE"
    assert gold.update is None


def test_legacy_challenge_without_target_still_parses():
    gold = HumanGold.model_validate(
        {
            "attention_state": ["ENGAGE"],
            "cognitive_effects": ["CHALLENGE"],
        }
    )
    assert gold.disposition == "ENGAGE"
    assert gold.update is None


def test_target_hit_uses_update_node_not_retrieval():
    rows = [
        {
            "id": "wrong-node",
            "gold_status": "LABELED",
            "attention_state": "WATCH",
            "matched_kernel_titles": ["Motor Intelligence", "Collective Intelligence"],
            "matched_kernel_ids": ["n1", "n2"],
            "kernel_matches": [
                {"node_id": "n1", "title": "Motor Intelligence"},
                {"node_id": "n2", "title": "Collective Intelligence"},
            ],
            "cognitive_impact": {"effects": [{"target_kernel_node_id": "n2", "effect": "REINFORCE"}]},
            "human_gold": {
                "disposition": "WATCH",
                "update": {"operation": "REINFORCE", "target_node_id": "P1"},
                "delta_content": "The update should land on Motor Intelligence, not merely retrieve it.",
            },
            "prediction_source": "model",
            "model_prediction": True,
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["target_accuracy"] == 0.0


def test_open_new_target_not_hit_by_empty_retrieval_or_targeted_open_new():
    empty_retrieval = {
        "id": "reinforce-existing",
        "gold_status": "LABELED",
        "attention_state": "WATCH",
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "cognitive_impact": {"effects": [{"target_kernel_node_id": "abc", "effect": "REINFORCE"}]},
        "human_gold": {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "A new branch, not an existing node.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    targeted_open = {
        "id": "open-with-target",
        "gold_status": "LABELED",
        "attention_state": "WATCH",
        "matched_kernel_titles": ["Motor Intelligence"],
        "matched_kernel_ids": ["abc"],
        "kernel_matches": [{"node_id": "abc", "title": "Motor Intelligence"}],
        "cognitive_impact": {"effects": [{"target_kernel_node_id": "abc", "effect": "OPEN_NEW"}]},
        "human_gold": {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "OPEN_NEW gold has an empty target.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    metrics = compute_metrics([empty_retrieval, targeted_open])
    assert metrics["target"]["target_accuracy"] == 0.0
    assert metrics["update_operation"]["update_operation_accuracy"] == 0.5


def test_open_new_target_misses_when_any_predicted_update_has_a_node():
    rows = [
        {
            "id": "mixed",
            "gold_status": "LABELED",
            "attention_state": "WATCH",
            "matched_kernel_titles": ["Motor Intelligence"],
            "matched_kernel_ids": ["abc"],
            "kernel_matches": [{"node_id": "abc", "title": "Motor Intelligence"}],
            "cognitive_impact": {
                "effects": [
                    {"target_kernel_node_id": "abc", "effect": "REINFORCE"},
                    {"target_kernel_node_id": None, "effect": "OPEN_NEW"},
                ]
            },
            "human_gold": {
                "disposition": "WATCH",
                "update": {"operation": "OPEN_NEW", "target_node_id": None},
                "delta_content": "No existing node is the landing spot.",
            },
            "prediction_source": "model",
            "model_prediction": True,
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["target_accuracy"] == 0.0


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
            "human_gold": {"disposition": "ENGAGE"},
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
            "human_gold": {"disposition": "ENGAGE"},
            "prediction_source": "model",
            "fallback": False,
            "model_prediction": True,
        },
        {
            "id": "fb",
            "gold_status": "LABELED",
            "attention_state": "ENGAGE",
            "human_gold": {"disposition": "ENGAGE"},
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
    assert metrics["disposition"]["denominator"] == 1
    assert metrics["disposition"]["disposition_accuracy"] == 1.0


def test_manifest_example_loads():
    manifest = load_manifest(ROOT / "eval" / "live" / "manifest.example.yaml")
    assert len(manifest.cases) >= 6
    assert all(gold_status_of(c) == "UNLABELED" for c in manifest.cases)
    text = (ROOT / "eval" / "live" / "manifest.example.yaml").read_text()
    assert "disposition:" in text
    assert "attention_state:" not in text
    assert "processing_modes:" not in text
    assert "kernel_targets:" not in text
    assert "cognitive_effects:" not in text
    assert "expected_delta:" not in text


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
