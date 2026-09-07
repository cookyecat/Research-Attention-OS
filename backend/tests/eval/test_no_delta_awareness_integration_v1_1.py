from __future__ import annotations

from app.enums import Disposition
from eval.live.no_delta_awareness_integration_v1 import expected_gate_disposition
from eval.live.no_delta_awareness_integration_v1_1 import determine_gate_disposition


def test_partial_determinacy_matches_all_fully_observed_truth_table_rows():
    for d in ("IN", "OUT"):
        for s in ("MATERIAL", "NOT_MATERIAL"):
            for p in ("SALIENT", "NOT_SALIENT"):
                assert determine_gate_disposition(d, s, p) == expected_gate_disposition(d, s, p)


def test_ia7_shape_is_aware_even_when_p_unknown():
    assert determine_gate_disposition("IN", "MATERIAL", None) == Disposition.AWARE


def test_ia11_shape_remains_unresolved_when_p_unknown():
    assert determine_gate_disposition("OUT", "MATERIAL", None) is None


def test_not_material_short_circuits_all_unknowns_to_drop():
    assert determine_gate_disposition(None, "NOT_MATERIAL", None) == Disposition.DROP


def test_false_d_or_p_short_circuits_unknown_s_to_drop():
    assert determine_gate_disposition("OUT", None, "NOT_SALIENT") == Disposition.DROP


def test_unknown_s_with_positive_d_or_p_remains_unresolved():
    assert determine_gate_disposition("IN", None, None) is None
    assert determine_gate_disposition("OUT", None, "SALIENT") is None
