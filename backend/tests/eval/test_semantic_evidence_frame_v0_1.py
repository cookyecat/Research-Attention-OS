from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.semantic_evidence_frame_v0_1 import SemanticEvidenceFrameV0_1


def valid_frame() -> dict:
    return {
        "interface_version": "semantic-evidence-frame-v0.1",
        "event": {
            "event_id": "E1",
            "as_of": "2026-09-07T06:00:00Z",
            "summary": "A national regulator announced a mandatory pricing-rule change.",
        },
        "sources": [
            {
                "source_id": "S1",
                "source_type": "article",
                "published_at": "2026-09-07T05:00:00Z",
                "locator": "source://S1",
            }
        ],
        "evidence": [
            {
                "evidence_id": "EV1",
                "source_id": "S1",
                "support_pointer": "paragraph 4",
                "support_excerpt": "The new rule will become mandatory next year.",
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
            }
        ],
        "substantive_actors_objects": [
            {
                "name": "national regulator",
                "role": "regulator",
                "substantive_basis": "issued the rule",
                "support_ids": ["EV1"],
            }
        ],
        "actions_changes": [
            {
                "description": "mandatory pricing rule announced",
                "temporal_status": "ANNOUNCED",
                "support_ids": ["EV1"],
            }
        ],
        "affected_systems_populations": [
            {
                "description": "regulated market participants",
                "reference_scope": "national market",
                "support_ids": ["EV1"],
            }
        ],
        "temporal_context": {
            "event_time": "2026-09-07",
            "effective_time": "2027",
            "as_of": "2026-09-07T06:00:00Z",
            "notes": "announced, not yet effective",
        },
        "uncertainties": [],
    }


def test_valid_semantic_evidence_frame_round_trips():
    obj = SemanticEvidenceFrameV0_1.model_validate(valid_frame())
    assert obj.event.event_id == "E1"
    assert obj.actions_changes[0].temporal_status == "ANNOUNCED"


def test_dsp_and_attention_action_leakage_is_rejected():
    for key, value in (
        ("D", "IN"),
        ("S", "MATERIAL"),
        ("P", "SALIENT"),
        ("predicted_attention_action", "AWARE"),
    ):
        data = valid_frame()
        data[key] = value
        with pytest.raises(ValidationError):
            SemanticEvidenceFrameV0_1.model_validate(data)


def test_evidence_must_reference_existing_source():
    data = valid_frame()
    data["evidence"][0]["source_id"] = "MISSING"
    with pytest.raises(ValidationError, match="missing source_id"):
        SemanticEvidenceFrameV0_1.model_validate(data)


def test_semantic_objects_must_reference_existing_evidence():
    data = valid_frame()
    data["actions_changes"][0]["support_ids"] = ["MISSING"]
    with pytest.raises(ValidationError, match="missing evidence_id"):
        SemanticEvidenceFrameV0_1.model_validate(data)


def test_as_of_must_be_consistent():
    data = valid_frame()
    data["temporal_context"]["as_of"] = "2026-09-08T00:00:00Z"
    with pytest.raises(ValidationError, match="must equal event.as_of"):
        SemanticEvidenceFrameV0_1.model_validate(data)


def test_unknown_is_explicit_not_encoded_as_negative_fact():
    data = valid_frame()
    data["uncertainties"] = [
        {
            "field": "affected_systems_populations.reference_scope",
            "kind": "UNCERTAIN_SCOPE",
            "note": "The source does not quantify the affected population.",
            "support_ids": ["EV1"],
        }
    ]
    obj = SemanticEvidenceFrameV0_1.model_validate(data)
    assert obj.uncertainties[0].kind == "UNCERTAIN_SCOPE"
