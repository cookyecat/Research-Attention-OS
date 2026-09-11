from eval.live.run_phase10d6c_canonical_input_reconciliation_v0_1 import canonical_user_prompt, reconstruct_prod_matches
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes


def test_canonical_payload_preserves_unit_identity_and_supports():
    selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); case=selected['N4']['case']
    matches=reconstruct_prod_matches(case,nodes); prompt=canonical_user_prompt(case['frozen_units'],matches,nodes)
    first=case['frozen_units'][0]
    assert first['unit_id'] in prompt
    assert first['statement'] in prompt
    assert 'supports' in prompt
    assert 'Eligible cognitive targets' in prompt
