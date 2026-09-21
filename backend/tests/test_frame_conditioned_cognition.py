from __future__ import annotations

from uuid import uuid4
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cognitive.research_aligned_contract import canonical_semantic_units
from app.models.event import EventEvidenceFrame
from app.services.frame_conditioned_cognition import (
    FRAME_CONDITIONED_COGNITION_CONTRACT,
    FrameConditionedCognitionError,
    event_frame_to_extraction,
)


def _frame(db, *, units):
    source_id = uuid4()
    frame = EventEvidenceFrame(
        identity_key=f"frame-{uuid4()}",
        workspace_id="pytest",
        source_id=source_id,
        source_snapshot_id=None,
        analysis_run_id=None,
        frame_contract_version="event-evidence-frame-v0.3",
        semantic_input_digest=f"semantic-{uuid4()}",
        frame_payload={
            "event_key": "evt-test",
            "event_summary": "A bounded event proposition.",
            "audited_semantic_units": units,
        },
        frame_digest=f"digest-{uuid4()}",
    )
    # The FK source is deliberately not persisted because this unit test only
    # exercises pure frame -> cognition projection.
    return frame


def _units():
    sid = str(uuid4())
    return [
        {
            "unit_id": "evt-test:action_change:1",
            "statement": "A controller reduced closed-loop latency to 4 ms.",
            "epistemic_status": "SOURCE_CLAIM",
            "confidence": "HIGH",
            "supports": [
                {
                    "source_id": sid,
                    "support_pointer": "PARA 0004",
                    "support_excerpt": "The controller reduced closed-loop latency to 4 ms.",
                }
            ],
        },
        {
            "unit_id": "evt-test:affected_system_population:1",
            "statement": "The result applies to high-frequency embodied control.",
            "epistemic_status": "DIRECT_OBSERVATION",
            "confidence": "MEDIUM",
            "supports": [
                {
                    "source_id": sid,
                    "support_pointer": "PARA 0005",
                    "support_excerpt": "Evaluation covers high-frequency embodied control.",
                }
            ],
        },
    ]


def test_frame_adapter_preserves_phase6b_canonical_semantic_units():
    from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction

    units = _units()
    frame = _frame(None, units=units)
    current = event_frame_to_extraction(frame)
    historical = audited_units_to_extraction(units)

    assert canonical_semantic_units(current) == canonical_semantic_units(historical)
    assert current.analysis_provenance["contract"] == FRAME_CONDITIONED_COGNITION_CONTRACT
    assert current.analysis_provenance["decision_scope"] == "EVENT_FRAME"
    assert current.analysis_provenance["event_key"] == "evt-test"


def test_frame_adapter_fails_closed_without_audited_units():
    frame = _frame(None, units=[])
    with pytest.raises(FrameConditionedCognitionError, match="audited_semantic_units"):
        event_frame_to_extraction(frame)


def test_frame_adapter_fails_closed_without_support_evidence():
    units = _units()
    units[0]["supports"] = []
    frame = _frame(None, units=units)
    with pytest.raises(FrameConditionedCognitionError, match="lacks evidence supports"):
        event_frame_to_extraction(frame)
