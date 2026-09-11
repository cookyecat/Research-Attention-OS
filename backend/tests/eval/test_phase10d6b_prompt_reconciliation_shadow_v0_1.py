from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes


def test_reconstruct_prod_matches_preserves_frozen_target_identity():
    selected = selected_cases()
    nodes = build_phase6b_mvp_kernel_nodes()
    for label, row in selected.items():
        case = row["case"]
        rebuilt = reconstruct_prod_matches(case, nodes)
        expected = {str(x["kernel_node_id"]) for x in case["locate"]["modal"]["selected_matches"]}
        assert {str(x.node_id) for x in rebuilt} == expected
        assert all(x.node_type for x in rebuilt)
