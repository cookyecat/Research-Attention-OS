from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_SYSTEM_VNEXT
from eval.live.run_phase10d6c_canonical_input_reconciliation_v0_1 import canonical_assess


def test_interaction_uses_distinct_frozen_system_prompts():
    assert IMPACT_SYSTEM != IMPACT_SYSTEM_VNEXT
    assert 'largest useful cognitive change' in IMPACT_SYSTEM
    assert 'do not vote, rank, argmax, or suppress' in IMPACT_SYSTEM_VNEXT
    assert canonical_assess is not None
