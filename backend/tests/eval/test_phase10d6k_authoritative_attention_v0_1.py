from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect
from eval.live.phase10d6k_authoritative_attention_v0_1 import canonical_epistemic


def test_canonical_epistemic_is_conservative():
    assert canonical_epistemic("REINFORCE", "DIRECT", "PRIMARY_SOURCE", support_bound=True)[:2] == (True, 1)
    assert canonical_epistemic("CHALLENGE", "DIRECT", "SECONDARY_REPORT", support_bound=True)[:2] == (True, 0)
    assert canonical_epistemic("CHALLENGE", "PARTIAL", "PRIMARY_SOURCE", support_bound=True)[:2] == (True, 0)
    assert canonical_epistemic("REINFORCE", "INSUFFICIENT", "PRIMARY_SOURCE", support_bound=True)[:2] == (False, 0)
    assert canonical_epistemic("CHALLENGE", "CONTRADICTS_OPERATION", "PRIMARY_SOURCE", support_bound=True)[:2] == (False, 0)


def test_open_new_uses_provenance_not_numeric_guess():
    assert canonical_epistemic("OPEN_NEW", None, "PRIMARY_SOURCE", support_bound=True)[:2] == (True, 1)
    assert canonical_epistemic("OPEN_NEW", None, "SECONDARY_REPORT", support_bound=True)[:2] == (True, 0)
    assert canonical_epistemic("OPEN_NEW", None, "PRIMARY_SOURCE", support_bound=False)[:2] == (False, 0)
