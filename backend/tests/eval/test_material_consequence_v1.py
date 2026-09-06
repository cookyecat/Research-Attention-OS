"""Material Consequence (S) estimator v1 tests."""

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

from eval.live.material_consequence_v1 import (
    ESTIMATOR_VERSION,
    PROFILE_ID,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    MaterialConsequenceV1Response,
    build_messages,
    compute_material_consequence_metrics,
    estimate_material_consequence_v1,
    load_material_consequence_profile,
    prompt_sha256,
    render_profile_for_prompt,
)
from eval.live.run_material_consequence_v1_eval import (
    validate_manifest_provenance,
    write_artifact,
)


def test_s_v1_versions_and_prompt_hash():
    assert ESTIMATOR_VERSION == "material-consequence-estimator-v1"
    assert PROMPT_VERSION == "material-consequence-v1"
    assert len(prompt_sha256()) == 64


def test_s_v1_prompt_encodes_shared_system_semantics_without_dp_leakage():
    blob = SYSTEM_PROMPT
    assert "consequential shared reference system" in blob
    assert "smallest affected unit" in blob
    assert "raw reach" in blob
    assert "media coverage" in blob
    assert "user personally cares" in blob
    assert "D" in blob and "P" in blob


def test_s_v1_profile_has_frozen_semantic_fields_only():
    profile = load_material_consequence_profile()
    assert set(profile) == {
        "semantic_contract",
        "invariants",
        "shared_reference_system_examples",
        "boundary_principles",
    }
    dumped = render_profile_for_prompt(profile)
    assert "national or high-level governance" in dumped
    assert "Raw population count" in dumped
    assert "media coverage" in dumped


def test_s_v1_prompt_does_not_leak_calibration_case_ids():
    profile = load_material_consequence_profile()
    messages = build_messages("A generic event.", profile)
    blob = "\n".join(m["content"] for m in messages)
    for marker in ("MC1", "MC6", "MC10", "MS1", "MS2", "MS10"):
        assert marker not in blob


def test_s_v1_schema_diagnostics_are_not_labels():
    obj = MaterialConsequenceV1Response.model_validate(
        {
            "material_consequence": "MATERIAL",
            "affected_shared_systems": ["industry practice"],
            "material_changes": ["standard engineering practice changes"],
            "reason": "field-level change",
        }
    )
    assert obj.material_consequence == "MATERIAL"
    with pytest.raises(ValidationError):
        MaterialConsequenceV1Response.model_validate(
            {
                "material_consequence": "MAYBE",
                "affected_shared_systems": [],
                "material_changes": [],
                "reason": "x",
            }
        )


def test_s_v1_estimator_fails_closed():
    from app.cognitive.client import LLMError

    def fake_chat(messages, **kwargs):
        return {
            "material_consequence": "MATERIAL",
            "affected_shared_systems": ["industry"],
            "material_changes": ["industry practice changes"],
            "reason": "material shared-state change",
        }, {"model": "fake-s-v1", "latency_ms": 1, "prompt_tokens": 1, "completion_tokens": 1}

    out = estimate_material_consequence_v1("A field-wide practice changes.", chat_fn=fake_chat)
    assert out["scorable"] is True
    assert out["material_consequence"] == "MATERIAL"

    def boom(messages, **kwargs):
        raise LLMError("provider 503 unavailable")

    failed = estimate_material_consequence_v1("A field-wide practice changes.", chat_fn=boom)
    assert failed["scorable"] is False
    assert failed["material_consequence"] is None


def test_s_v1_metrics_have_no_embedded_success_gate():
    rows = [
        {"scorable": True, "gold": "MATERIAL", "prediction": "MATERIAL"},
        {"scorable": True, "gold": "NOT_MATERIAL", "prediction": "NOT_MATERIAL"},
        {"scorable": True, "gold": "MATERIAL", "prediction": "NOT_MATERIAL"},
    ]
    metrics = compute_material_consequence_metrics(rows)
    assert metrics["n_scored"] == 3
    assert metrics["exact_accuracy"] == pytest.approx(2 / 3)
    assert metrics["material_recall"] == pytest.approx(0.5)
    assert metrics["not_material_recall"] == pytest.approx(1.0)
    assert "success_criterion" not in metrics
    assert "metrics_pass" not in metrics


def test_s_v1_is_eval_only_and_direct_not_mandatory_pipeline():
    source = inspect.getsource(estimate_material_consequence_v1)
    assert "scheduler" not in source
    assert "anchor" not in source.lower()
    assert "clause" not in source.lower()


def test_s_v1_manifest_provenance_validation():
    manifest = {
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "profile_id": PROFILE_ID,
        "prompt_sha256": prompt_sha256(),
    }
    validate_manifest_provenance(manifest)

    bad = dict(manifest)
    bad["prompt_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance mismatch"):
        validate_manifest_provenance(bad)


def test_s_v1_first_run_artifact_is_write_once(tmp_path):
    path = tmp_path / "first_run.json"
    write_artifact({"ok": True}, path)
    with pytest.raises(FileExistsError):
        write_artifact({"ok": False}, path)
