from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect
from eval.live.phase10d6k_evaluator_authority_v0_2 import (
    canonical_epistemic,
    strong_jurisdiction,
    strong_target_fit,
)


def test_strong_case_level_policy_is_frozen():
    assert strong_target_fit("A", "REINFORCE", "M1") == "INSUFFICIENT"
    assert strong_target_fit("D", "CHALLENGE", "B2") == "INSUFFICIENT"
    assert strong_target_fit("X", "REINFORCE", "M1") == "DIRECT"
    assert strong_target_fit("X", "CHALLENGE", "B1") == "INSUFFICIENT"
    assert strong_target_fit("N4", "REINFORCE", "B1") == "DIRECT"
    assert strong_target_fit("N4", "REINFORCE", "M1") == "DIRECT"
    assert strong_target_fit("N4", "REINFORCE", "BT1") == "PARTIAL"
    assert strong_target_fit("N4", "REINFORCE", "Q1") == "PARTIAL"
    assert strong_target_fit("N4", "CHALLENGE", "M1") == "INSUFFICIENT"
    assert strong_jurisdiction("A") == "INSUFFICIENT_JURISDICTION"
    assert strong_jurisdiction("D") == "INSUFFICIENT_JURISDICTION"
    assert strong_jurisdiction("X") == "SUPPORTED_JURISDICTION"
    assert strong_jurisdiction("N4") == "SUPPORTED_JURISDICTION"


def test_canonical_authority_rejects_bad_grounding_and_jurisdiction():
    assert canonical_epistemic(
        "REINFORCE", "DIRECT", None, "PRIMARY_SOURCE", support_bound=True
    )[:2] == (True, 1)
    assert canonical_epistemic(
        "REINFORCE", "PARTIAL", None, "PRIMARY_SOURCE", support_bound=True
    )[:2] == (True, 0)
    assert canonical_epistemic(
        "REINFORCE", "INSUFFICIENT", None, "PRIMARY_SOURCE", support_bound=True
    )[:2] == (False, 0)
    assert canonical_epistemic(
        "OPEN_NEW", None, "SUPPORTED_JURISDICTION", "PRIMARY_SOURCE", support_bound=True
    )[:2] == (True, 1)
    assert canonical_epistemic(
        "OPEN_NEW", None, "INSUFFICIENT_JURISDICTION", "PRIMARY_SOURCE", support_bound=True
    )[:2] == (False, 0)
    assert canonical_epistemic(
        "OPEN_NEW", None, "SUPPORTED_JURISDICTION", "PRIMARY_SOURCE", support_bound=False
    )[:2] == (False, 0)
