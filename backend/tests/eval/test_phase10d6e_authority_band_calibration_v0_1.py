from eval.live.run_phase10d6e_authority_band_calibration_v0_1 import load_verified, SOURCE, SOURCE_SHA, PARITY, PARITY_SHA, POLICIES


def test_authority_calibration_sources_are_frozen_and_policies_fixed():
    source=load_verified(SOURCE,SOURCE_SHA); parity=load_verified(PARITY,PARITY_SHA)
    assert source['selected_cases']==['A','D','X','N4']
    assert parity['n_replayed_samples']==168
    assert POLICIES==('NATIVE_RAW','PRODUCTION_IMPORTANCE','C1_CONSERVATIVE','C2_AUDITOR_TRUST_UPPER_BOUND')
