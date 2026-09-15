from types import SimpleNamespace
from uuid import uuid4

from eval.live.phase12b_residual_necessity_v0_1 import summarize_feedback


def row(**attr):
    return SimpleNamespace(id=uuid4(), attribution=attr)


def test_no_feedback_keeps_identity() -> None:
    out = summarize_feedback([])
    assert out["personalization_eligible_rows"] == 0
    assert out["calibration_decision"] == "IDENTITY_RETAINED"


def test_unresolved_and_proxy_rows_are_not_eligible() -> None:
    out = summarize_feedback([
        row(causal_scope="UNRESOLVED", evidence_provenance="HUMAN_EXPLICIT", personalization_eligible=False),
        row(causal_scope="USER_POLICY_RESIDUAL", evidence_provenance="ASSISTANT_PROXY", personalization_eligible=False),
    ])
    assert out["personalization_eligible_rows"] == 0
    assert out["unresolved_or_missing_attribution_rows"] == 1


def test_single_eligible_residual_does_not_trigger_calibration() -> None:
    out = summarize_feedback([
        row(causal_scope="USER_POLICY_RESIDUAL", evidence_provenance="HUMAN_EXPLICIT", feedback_class="ATTENTION_POLICY_CORRECTION", personalization_eligible=True),
    ])
    assert out["personalization_eligible_rows"] == 1
    assert out["calibration_decision"] == "IDENTITY_RETAINED_PENDING_REPLICATION"
