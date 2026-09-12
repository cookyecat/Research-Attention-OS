import json

from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6k_evaluator_capacity_bracket_v0_2 import (
    SOURCE,
    authority_for_row,
    build_evaluator_items,
    row_signature,
)


def test_frozen_evaluator_items_expose_no_strong_labels():
    src = json.loads(SOURCE.read_text())
    case = selected_cases()["N4"]["case"]
    targeted, open_new, sig_by_id = build_evaluator_items(
        "N4", case, src["results"]["N4"], build_phase6b_mvp_kernel_nodes()
    )
    assert targeted and open_new and sig_by_id
    assert all("strong_class" not in row and "strong_reason" not in row for row in targeted + open_new)
    assert all(row["support_texts"] for row in targeted + open_new)
    assert all(row["jurisdiction_anchor_ids"] for row in open_new)


def test_authority_selector_keeps_evaluator_arms_separate():
    targeted = {
        "operation": "REINFORCE", "target": "M1", "support_unit_ids": ["u1"],
        "jurisdiction_anchor_ids": [], "reason": "x",
    }
    sig = row_signature(targeted)
    weak_fit = {sig: "PARTIAL"}
    fit, jurisdiction = authority_for_row(
        "X", targeted, "K2_WEAK_EVALUATOR_AUTHORITY", weak_fit, {}
    )
    assert (fit, jurisdiction) == ("PARTIAL", None)
    fit, jurisdiction = authority_for_row(
        "X", targeted, "K3_STRONG_EVALUATOR_AUTHORITY", weak_fit, {}
    )
    assert (fit, jurisdiction) == ("DIRECT", None)
