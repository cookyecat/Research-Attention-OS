from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.live.run_phase14c_counterfactual_decision_relevance_v0_1 import run


def test_same_event_current_contract_blindness_with_sensitive_positive_control():
    report = run()
    diagnostics = report["diagnostics"]
    states = report["states"]

    assert diagnostics["same_event_belief_exists"] is True
    assert diagnostics["same_event_keeps_provenance_independence_fixed"] is True
    assert diagnostics["same_event_does_not_change_decision_digest"] is True
    assert diagnostics["same_event_does_not_change_current_probe_attention"] is True

    assert diagnostics["positive_control_changes_decision_digest"] is True
    assert diagnostics["positive_control_changes_attention"] is True

    assert states["R_BASE"]["cognitive_probe"]["disposition"] == "ENGAGE"
    assert states["R_SAME"]["cognitive_probe"]["disposition"] == "ENGAGE"
    assert states["R_SECONDARY_POSITIVE_CONTROL"]["cognitive_probe"]["disposition"] == "WATCH"

    assert report["interpretation"]["current_direct_same_event_decision_influence"] == (
        "ZERO_BY_CURRENT_CONTRACT"
    )
    assert report["interpretation"]["potential_counterfactual_same_event_decision_relevance"] == (
        "UNKNOWN"
    )
