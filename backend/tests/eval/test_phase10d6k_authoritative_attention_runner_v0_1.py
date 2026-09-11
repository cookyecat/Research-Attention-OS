from eval.live.run_phase10d6k_conservative_authoritative_attention_replay_v0_1 import conservative_modal

def test_conservative_modal_prefers_more_conservative_on_tie():
    fit,counts=conservative_modal(['DIRECT','PARTIAL','DIRECT','PARTIAL'])
    assert fit=='PARTIAL'
    assert counts=={'DIRECT':2,'PARTIAL':2}
