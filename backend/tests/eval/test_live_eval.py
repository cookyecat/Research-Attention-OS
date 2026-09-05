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
    assert all("disposition" in r for r in rows)
    assert all("embedding_used" in r for r in rows)
    assert all("lexical_fallback" in r for r in rows)
    assert all("scheduler_features" in r for r in rows)


def test_unlabeled_not_in_accuracy_denominator():
    rows = [
        {
            "id": "u1",
            "gold_status": "UNLABELED",
            "disposition": "DROP",
            "human_gold": None,
        },
        {
            "id": "l1",
            "gold_status": "LABELED",
            "disposition": "ENGAGE",
            "human_gold": {
                "disposition": "ENGAGE",
                "update": {"operation": "OPEN_NEW", "target_node_id": None},
                "delta_content": "A new question about whether this is worth a branch.",
            },
            "cognitive_impact": {"effects": [{"target_kernel_node_id": None, "operation": "OPEN_NEW"}]},
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
        {"id": "b", "gold_status": "UNLABELED", "disposition": None},
        {"id": "a", "gold_status": "UNLABELED", "disposition": None},
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
            "expected_effects": [{"target_kernel": "Motor Intelligence", "acceptable_effects": ["REINFORCE"]}],
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
            "disposition": "ENGAGE",
            "processing_modes": ["VERIFY", "SYNTHESIZE"],
            "matched_kernel_titles": ["Motor Intelligence"],
            "matched_kernel_ids": ["abc"],
            "kernel_matches": [{"node_id": "abc", "title": "Motor Intelligence"}],
            "cognitive_impact": {
                "effects": [
                    {
                        "target_kernel_node_id": "abc",
                        "operation": "REINFORCE",
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
    assert metrics["exact_update"]["exact_update_accuracy"] == 1.0
    assert metrics["delta_content"]["n_with_delta_content"] == 1
    assert metrics["delta_content"]["auto_scored"] is False
    md = render_markdown(metrics)
    assert "## Disposition" in md
    assert "## Update Operation" in md
    assert "## Target" in md
    assert "## Exact Update" in md
    assert "## Delta Content" in md
    assert "attention_state" not in md
    assert "Processing Mode" not in md
    assert "key_claims" not in md


def test_report_scores_legacy_gold_without_refine_mapping():
    none_row = {
        "id": "open",
        "gold_status": "LABELED",
        "disposition": "AWARE",
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "cognitive_impact": {
            "effects": [{"target_kernel_node_id": None, "operation": "OPEN_NEW"}]
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
        "disposition": "ENGAGE",
        "matched_kernel_titles": ["Motor Intelligence"],
        "matched_kernel_ids": [],
        "kernel_matches": [{"node_id": "n1", "title": "Motor Intelligence"}],
        "cognitive_impact": {"effects": [{"target_kernel_node_id": "n1", "operation": "REINFORCE"}]},
        "human_gold": {
            "attention_state": ["ENGAGE"],
            "must_match_kernel": ["Motor Intelligence"],
            "acceptable_modes": ["VERIFY", "SYNTHESIZE"],
            "expected_effects": [{"target_kernel": "Motor Intelligence", "acceptable_effects": ["REINFORCE"]}],
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    metrics = compute_metrics([none_row, legacy_row])
    assert metrics["disposition"]["disposition_accuracy"] == 1.0
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["target_accuracy"] == 1.0
    assert metrics["exact_update"]["exact_update_accuracy"] == 1.0
    assert metrics["n_labeled"] == 2


def test_refine_prediction_is_not_mapped_to_reinforce():
    rows = [
        {
            "id": "refine-pred",
            "gold_status": "LABELED",
            "disposition": "ENGAGE",
            "cognitive_impact": {"effects": [{"target_kernel_node_id": "n1", "operation": "REFINE"}]},
            "kernel_matches": [{"node_id": "n1", "title": "Motor Intelligence"}],
            "human_gold": {
                "disposition": "ENGAGE",
                "update": {"operation": "REINFORCE", "target_node_id": "P1"},
                "delta_content": "Production must emit REINFORCE, not REFINE.",
            },
            "prediction_source": "model",
            "model_prediction": True,
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["update_operation"]["update_operation_accuracy"] == 0.0


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
            "disposition": "WATCH",
            "matched_kernel_titles": ["Motor Intelligence", "Collective Intelligence"],
            "matched_kernel_ids": ["n1", "n2"],
            "kernel_matches": [
                {"node_id": "n1", "title": "Motor Intelligence"},
                {"node_id": "n2", "title": "Collective Intelligence"},
            ],
            "cognitive_impact": {"effects": [{"target_kernel_node_id": "n2", "operation": "REINFORCE"}]},
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
    assert metrics["exact_update"]["exact_update_accuracy"] == 0.0


def test_open_new_is_not_a_target_metric_and_empty_pred_is_not_a_hit():
    empty_pred = {
        "id": "empty-pred",
        "gold_status": "LABELED",
        "disposition": "WATCH",
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "update": {"operation": None, "target_node_id": None},
        "cognitive_impact": {"effects": []},
        "human_gold": {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "A new branch, not an existing node.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    reinforce_instead = {
        "id": "reinforce-existing",
        "gold_status": "LABELED",
        "disposition": "WATCH",
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "kernel_matches": [],
        "cognitive_impact": {"effects": [{"target_kernel_node_id": "abc", "operation": "REINFORCE"}]},
        "human_gold": {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "A new branch, not an existing node.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    explicit_open = {
        "id": "explicit-open",
        "gold_status": "LABELED",
        "disposition": "WATCH",
        "update": {"operation": "OPEN_NEW", "target_node_id": None},
        "cognitive_impact": {"effects": [{"target_kernel_node_id": None, "operation": "OPEN_NEW"}]},
        "human_gold": {
            "disposition": "WATCH",
            "update": {"operation": "OPEN_NEW", "target_node_id": None},
            "delta_content": "Explicit OPEN_NEW.",
        },
        "prediction_source": "model",
        "model_prediction": True,
    }
    metrics = compute_metrics([empty_pred, reinforce_instead, explicit_open])
    assert metrics["target"]["denominator"] == 0
    assert metrics["update_operation"]["denominator"] == 3
    assert metrics["update_operation"]["update_operation_accuracy"] == 1 / 3
    assert metrics["exact_update"]["denominator"] == 3
    assert metrics["exact_update"]["exact_update_accuracy"] == 1 / 3


def test_primary_update_not_any_effect_open_new():
    rows = [
        {
            "id": "mixed",
            "gold_status": "LABELED",
            "disposition": "WATCH",
            "matched_kernel_titles": ["Motor Intelligence"],
            "matched_kernel_ids": ["abc"],
            "kernel_matches": [{"node_id": "abc", "title": "Motor Intelligence"}],
            "cognitive_impact": {
                "effects": [
                    {"target_kernel_node_id": "abc", "operation": "REINFORCE", "change_magnitude": 0.7, "target_importance": 0.65},
                    {"target_kernel_node_id": None, "operation": "OPEN_NEW", "change_magnitude": 0.55, "target_importance": 0.55},
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
    assert metrics["update_operation"]["update_operation_accuracy"] == 0.0
    assert metrics["target"]["denominator"] == 0
    assert metrics["exact_update"]["exact_update_accuracy"] == 0.0


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
            "disposition": "ENGAGE",
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
            "disposition": "ENGAGE",
            "human_gold": {"disposition": "ENGAGE"},
            "prediction_source": "model",
            "fallback": False,
            "model_prediction": True,
        },
        {
            "id": "fb",
            "gold_status": "LABELED",
            "disposition": "ENGAGE",
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
    assert metrics["fallback_excluded_from_model_metrics"] is False
    assert metrics["stage_scoped_scoring"] is True
    assert metrics["disposition"]["denominator"] == 1
    assert metrics["disposition"]["disposition_accuracy"] == 1.0


def test_delta_fallback_does_not_exclude_impact_metrics():
    rows = [
        {
            "id": "mixed",
            "gold_status": "LABELED",
            "disposition": "ENGAGE",
            "update": {"operation": "REINFORCE", "target_node_id": "M1"},
            "human_gold": {
                "disposition": "ENGAGE",
                "update": {"operation": "REINFORCE", "target_node_id": "M1"},
                "delta_content": "Separable motor intelligence.",
            },
            "prediction_source": "mixed",
            "fallback": True,
            "fallback_stages": ["delta"],
            "model_prediction": True,
            "scorable": {
                "disposition": True,
                "update": True,
                "target": True,
                "delta_content": False,
            },
            "stage_provenance": {
                "extraction": {"provider": "model", "status": "success"},
                "impact": {"provider": "model", "status": "success"},
                "delta": {
                    "provider": "rule",
                    "status": "fallback",
                    "fallback_from": "model",
                    "error_type": "LLMError",
                    "error": "model did not return JSON",
                },
            },
        }
    ]
    metrics = compute_metrics(rows)
    assert metrics["n_fallback"] == 1
    assert metrics["n_model_predictions"] == 1
    assert metrics["disposition"]["denominator"] == 1
    assert metrics["disposition"]["disposition_accuracy"] == 1.0
    assert metrics["update_operation"]["denominator"] == 1
    assert metrics["update_operation"]["update_operation_accuracy"] == 1.0
    assert metrics["target"]["denominator"] == 1
    assert metrics["delta_content"]["n_with_delta_content"] == 0


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


def test_pilot12_v2_adjudicates_only_project_location_gold():
    original = load_manifest(ROOT / "eval" / "live" / "manifest.pilot12.yaml")
    v2 = load_manifest(ROOT / "eval" / "live" / "manifest.pilot12.v2.yaml")
    assert len(original.cases) == len(v2.cases) == 12
    first_o, first_v = original.cases[0], v2.cases[0]
    assert first_o.id == first_v.id == "pilot12-01"
    assert first_o.human_gold.update.operation == "REINFORCE"
    assert first_o.human_gold.update.target_node_id == "P1"
    assert first_v.human_gold.update.operation == "OPEN_NEW"
    assert first_v.human_gold.update.target_node_id is None
    assert first_v.human_gold.disposition == first_o.human_gold.disposition == "WATCH"
    for left, right in zip(original.cases[1:], v2.cases[1:]):
        assert left.id == right.id
        assert dump_human_gold(left.human_gold) == dump_human_gold(right.human_gold)


def test_live_eval_row_from_production_pipeline(client):
    from tests.conftest import add_text, analyze

    src = add_text(
        client,
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once.",
        title="live-map",
    )
    payload = analyze(client, src["id"])
    row = analysis_payload_to_eval_row(payload)
    assert row["disposition"]
    assert row["update"] is not None
    assert "delta_content" in row
    assert isinstance(row["kernel_matches"], list)
    assert row["lexical_fallback"] is True
    assert isinstance(row.get("retrieval_candidates"), list)
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
        assert row["disposition"]
        assert row["delta_summary"] is not None
        assert row["lexical_fallback"] is True
        assert row["skipped"] is False
        assert "extraction" in (row.get("stage_provenance") or {})
    finally:
        session.close()


def test_aware_null_update_is_allowed_gold():
    gold = HumanGold.model_validate({"disposition": "AWARE", "update": None, "delta_content": None})
    assert gold.disposition == "AWARE"
    assert gold.update is None
    dumped = dump_human_gold(gold)
    assert dumped["disposition"] == "AWARE"
    assert dumped["update"]["operation"] is None
    assert dumped["update"]["target_node_id"] is None
    case = LiveCase(id="aware-null", human_gold=gold)
    assert gold_status_of(case) == "LABELED"


def test_oracle_none_delta_is_drop():
    from eval.live.oracle_policy import run_oracle_policy

    gold = HumanGold.model_validate({"disposition": "AWARE", "update": None})
    out = run_oracle_policy(gold)
    assert out["used_production_route"] is True
    assert out["skipped_stages"] == ["extract", "locate", "impact"]
    assert out["disposition"] == "DROP"


def test_oracle_material_reinforce_is_not_drop():
    from eval.live.oracle_policy import run_oracle_policy
    from eval.live.schema import FrozenDelta

    gold = HumanGold.model_validate(
        {
            "disposition": "ENGAGE",
            "update": {"operation": "REINFORCE", "target_node_id": "B1"},
            "delta_content": "The existing belief is strengthened.",
        }
    )
    frozen = FrozenDelta(
        operation="REINFORCE",
        target_node_id="B1",
        target_type="BELIEF",
        change_magnitude=0.75,
        epistemic_strength=0.5,
        target_importance=0.75,
    )
    out = run_oracle_policy(gold, frozen_delta=frozen)
    assert out["disposition"] != "DROP"
    assert out["used_production_route"] is True


def test_oracle_policy_does_not_call_extract_locate_impact(monkeypatch):
    import app.services.pipeline as pipeline_mod
    from eval.live.oracle_policy import run_oracle_policy

    def boom(*_a, **_k):
        raise AssertionError("oracle path must not call the production pipeline")

    monkeypatch.setattr(pipeline_mod, "extract_source", boom)
    monkeypatch.setattr(pipeline_mod, "run_pipeline", boom)
    gold = HumanGold.model_validate({"disposition": "AWARE", "update": None})
    assert run_oracle_policy(gold)["disposition"] == "DROP"


def test_oracle_policy_calls_production_route(monkeypatch):
    import app.services.scheduler as scheduler_mod
    from eval.live.oracle_policy import run_oracle_policy

    calls = {"n": 0}
    real_route = scheduler_mod.route
    real_validate = scheduler_mod.validate_plan

    def counting_route(*args, **kwargs):
        calls["n"] += 1
        return real_route(*args, **kwargs)

    monkeypatch.setattr(scheduler_mod, "route", counting_route)
    gold = HumanGold.model_validate({"disposition": "AWARE", "update": None})
    run_oracle_policy(gold)
    assert calls["n"] == 1
    assert real_validate is scheduler_mod.validate_plan


def test_oracle_policy_metrics_and_report_sections():
    from eval.live.oracle_policy import attention_policy_eval_row, compare_disposition
    from eval.live.report import compute_oracle_policy_metrics

    gold = HumanGold.model_validate({"disposition": "WATCH", "update": None})
    row = {
        "id": "p1",
        "gold_status": "LABELED",
        "human_gold": dump_human_gold(gold),
        "disposition": "DROP",
        "update": {"operation": None, "target_node_id": None},
        "oracle_policy": {"disposition": "DROP"},
        "attention_policy_eval": attention_policy_eval_row(
            gold=gold,
            production_disposition="DROP",
            production_update={"operation": None, "target_node_id": None},
            oracle={"disposition": "DROP"},
        ),
    }
    cmp_ = compare_disposition("WATCH", "DROP")
    assert cmp_["false_drop"] is True
    assert cmp_["under_attention"] is True
    assert cmp_["critical_under_attention"] is True
    assert cmp_["exact_disposition_hit"] is False
    assert cmp_["disposition_distance"] == 2
    metrics = compute_oracle_policy_metrics([row])
    assert metrics["n_scored"] == 1
    assert metrics["false_drop_rate"] == 1.0
    assert metrics["critical_under_attention_rate"] == 1.0
    md = render_markdown(
        {
            **compute_metrics([row]),
            "production_end_to_end": {"disposition": {"disposition_accuracy": 0.0}},
            "oracle_delta_attention_policy": metrics,
        }
    )
    assert "## Production End-to-End" in md
    assert "## Oracle-Δ Attention Policy" in md


def test_policy_counterfactual_template_is_unlabeled_slots():
    path = ROOT / "eval" / "live" / "manifest.policy_counterfactual.template.yaml"
    manifest = load_manifest(path)
    assert 24 <= len(manifest.cases) <= 36
    assert all(gold_status_of(c) == "UNLABELED" for c in manifest.cases)
    assert all(not (c.source.text or c.source.url or c.source.local_file) for c in manifest.cases)
    text = path.read_text()
    assert "change_magnitude" in text
    assert "epistemic_strength" in text
    assert "target_importance" in text
    assert "runtime_context" in text
    assert "Do NOT invent" in text or "do not invent" in text.lower()


def test_oracle_only_skips_pipeline_on_template(tmp_path):
    code = main(
        [
            "--oracle-only",
            "--manifest",
            str(ROOT / "eval" / "live" / "manifest.policy_counterfactual.template.yaml"),
            "--out-dir",
            str(tmp_path / "oracle"),
            "--timestamp",
            "20000101T000001Z",
        ]
    )
    assert code == 0
    summary = json.loads((tmp_path / "oracle" / "summary.json").read_text())
    assert "production_end_to_end" in summary
    assert "oracle_delta_attention_policy" in summary
    assert summary["oracle_only"] is True
    assert summary["oracle_delta_attention_policy"]["n_scored"] == 0
    rows = [json.loads(line) for line in (tmp_path / "oracle" / "cases.jsonl").read_text().splitlines() if line]
    assert len(rows) == summary["n_cases"]
    assert all(r.get("skipped") is True for r in rows)
