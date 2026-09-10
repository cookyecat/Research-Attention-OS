from __future__ import annotations

from datetime import datetime, timezone
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'eval/live/results/phase10b_temporal_cognitive_basin_shift_v0_1/phase10b_temporal_cognitive_basin_shift_v0.1_20260910T081018Z.json'
SOURCE_SHA256 = '098dde0df2922a2244c26b99777a7744384394603831031f647d066605dc72d0'
OUT_DIR = ROOT / 'eval/live/results/phase10b1_cross_epoch_null_calibration_v0_1'
RUN_VERSION = 'phase10b1-cross-epoch-null-calibration-v0.1'
PERMUTATIONS = 5000
SEED = 20260910

from eval.live.cognitive_map_distance_v0_1 import attention_distribution, empirical_state_distribution, js_divergence_bits
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate, execution_snapshot as null_snapshot


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()


def verified(path: Path, expected: str) -> dict:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f'SHA mismatch {actual} != {expected}')
    return json.loads(path.read_text())


def att_js(a,b):
    return js_divergence_bits(attention_distribution(a), attention_distribution(b))


def top_js(a,b):
    return js_divergence_bits(empirical_state_distribution(a,'topology'), empirical_state_distribution(b,'topology'))


def core_js(a,b):
    return js_divergence_bits(empirical_state_distribution(a,'load_bearing'), empirical_state_distribution(b,'load_bearing'))


def main() -> int:
    src = verified(SOURCE, SOURCE_SHA256)
    rows = {}
    stats = [('attention', att_js), ('topology_state', top_js), ('load_bearing_state', core_js)]
    for case in ('RS05','RS15','RS11','RS12'):
        s0 = src['t0_samples'][case]
        s1 = src['t1_samples'][case]
        case_row = {'n_t0': len(s0), 'n_t1': len(s1), 'metrics': {}}
        for name, fn in stats:
            result = permutation_calibrate(s0, s1, statistic=fn, permutations=PERMUTATIONS, seed=SEED)
            case_row['metrics'][name] = result
        rows[case] = case_row
        print(json.dumps({'case':case, **{k:{'obs':v['observed'],'p95':v['null_p95'],'p':v['tail_probability'],'supported':v['drift_supported_v0_1']} for k,v in case_row['metrics'].items()}}, ensure_ascii=False), flush=True)
    out = {
        'run_version': RUN_VERSION,
        'status': 'EMPIRICAL_NULL_CALIBRATION_COMPLETE',
        'measurement_sha': git_head(),
        'source_phase10b': str(SOURCE.relative_to(ROOT)),
        'source_phase10b_sha256': SOURCE_SHA256,
        'permutation_chip': null_snapshot(),
        'results': rows,
        'guardrails': [
            'No LLM calls.',
            'Epoch labels are permuted while preserving original group sizes.',
            'Each metric is calibrated separately.',
            'drift_supported_v0.1 is a descriptive research gate, not a multiple-comparison-corrected confirmatory test.',
            'No stochastic-process model is fit.',
            'Production default remains one-delta-v1.',
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = OUT_DIR / f'{RUN_VERSION.replace("-","_")}_{stamp}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
    print('RESULT_PATH='+str(path.relative_to(ROOT)))
    print('RESULT_SHA256='+sha256(path))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
