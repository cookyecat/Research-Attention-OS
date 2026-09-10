from __future__ import annotations

VERSION='cognitive-temporal-regime-v0.1'


def classify_three_checkpoint(d01: bool, d02: bool, d12: bool) -> str:
    pattern=(bool(d01),bool(d02),bool(d12))
    return {
        (False,False,False): 'STABLE',
        (True,True,False): 'PERSISTENT_SHIFT',
        (True,False,True): 'TRANSIENT_RETURN',
        (False,True,True): 'LATE_SHIFT',
        (True,True,True): 'CONTINUING_OR_MULTI_REGIME_DRIFT',
    }.get(pattern,'INDETERMINATE')


def classify_case(persistence: dict) -> dict:
    out={}
    for metric,row in persistence.items():
        d01=bool(row['t0_t1_shift_supported'])
        d02=bool(row['t0_t2_shift_supported'])
        d12=bool(row['t1_t2_shift_supported'])
        out[metric]={
            'pattern':[int(d01),int(d02),int(d12)],
            'regime':classify_three_checkpoint(d01,d02,d12),
        }
    return out


def execution_snapshot() -> dict:
    return {
        'version':VERSION,
        'inputs':'three null-calibrated pairwise drift booleans',
        'stochastic_process':False,
        'scalar_stability_score':False,
    }
