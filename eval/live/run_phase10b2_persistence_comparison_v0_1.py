from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from eval.live.cognitive_map_distance_v0_1 import compare_cognitive_maps, attention_distribution, empirical_state_distribution, js_divergence_bits
from eval.live.cognitive_map_permutation_calibration_v0_1 import permutation_calibrate

RUN_VERSION='phase10b2-persistence-comparison-v0.1'
SOURCE10B=ROOT/'eval/live/results/phase10b_temporal_cognitive_basin_shift_v0_1/phase10b_temporal_cognitive_basin_shift_v0.1_20260910T081018Z.json'
SOURCE10B_SHA='098dde0df2922a2244c26b99777a7744384394603831031f647d066605dc72d0'
SOURCE10B1=ROOT/'eval/live/results/phase10b1_cross_epoch_null_calibration_v0_1/phase10b1_cross_epoch_null_calibration_v0.1_20260910T083329Z.json'
SOURCE10B1_SHA='439d6556ddea38eca28ca18e7a6ef5a059091ce99f4826a50ba05f4f4820fc46'
SOURCE_T2=ROOT/'eval/live/results/phase10b2_current_basin_persistence_v0_1/phase10b2_current_basin_persistence_v0.1_20260910T083922Z.json'
SOURCE_T2_SHA='67c36fb40e2185784bf75d744e54c86213f10a6c74d07f9897a68f54845b5f28'
OUT_DIR=ROOT/'eval/live/results/phase10b2_persistence_comparison_v0_1'
PERMUTATIONS=5000; SEED=20260910

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verified(p,h):
    a=sha256(p)
    if a!=h: raise RuntimeError(f'SHA mismatch {p}: {a} != {h}')
    return json.loads(Path(p).read_text())
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def att_js(a,b): return js_divergence_bits(attention_distribution(a),attention_distribution(b))
def top_js(a,b): return js_divergence_bits(empirical_state_distribution(a,'topology'),empirical_state_distribution(b,'topology'))
def core_js(a,b): return js_divergence_bits(empirical_state_distribution(a,'load_bearing'),empirical_state_distribution(b,'load_bearing'))
STATS={'attention':att_js,'topology_state':top_js,'load_bearing_state':core_js}

def calibrated(a,b):
    return {name:permutation_calibrate(a,b,statistic=fn,permutations=PERMUTATIONS,seed=SEED) for name,fn in STATS.items()}

def main():
    d10=verified(SOURCE10B,SOURCE10B_SHA); d101=verified(SOURCE10B1,SOURCE10B1_SHA); d2=verified(SOURCE_T2,SOURCE_T2_SHA)
    out_cases={}
    for case in ('RS05','RS15','RS11','RS12'):
        t0=d10['t0_samples'][case]; t1=d10['t1_samples'][case]; t2=d2['samples'][case]
        pairs={
            't0_t1': d101['results'][case]['metrics'],
            't0_t2': calibrated(t0,t2),
            't1_t2': calibrated(t1,t2),
        }
        persistence={}
        for metric in STATS:
            a=bool(pairs['t0_t1'][metric]['drift_supported_v0_1'])
            b=bool(pairs['t0_t2'][metric]['drift_supported_v0_1'])
            c=bool(pairs['t1_t2'][metric]['drift_supported_v0_1'])
            persistence[metric]={
                't0_t1_shift_supported':a,
                't0_t2_shift_supported':b,
                't1_t2_shift_supported':c,
                'persistent_new_basin_pattern': a and b and not c,
            }
        out_cases[case]={'n':{'t0':len(t0),'t1':len(t1),'t2':len(t2)},'pairs':pairs,'persistence':persistence}
        print(json.dumps({'case':case,'persistence':persistence,'distances':{pair:{m:round(v[m]['observed'],4) for m in STATS} for pair,v in pairs.items()}},ensure_ascii=False),flush=True)
    out={
      'run_version':RUN_VERSION,'status':'THREE_CHECKPOINT_PERSISTENCE_COMPARISON_COMPLETE','measurement_sha':git_head(),
      'sources':{'phase10b':str(SOURCE10B.relative_to(ROOT)),'phase10b_sha256':SOURCE10B_SHA,'phase10b1':str(SOURCE10B1.relative_to(ROOT)),'phase10b1_sha256':SOURCE10B1_SHA,'t2':str(SOURCE_T2.relative_to(ROOT)),'t2_sha256':SOURCE_T2_SHA},
      'permutations':PERMUTATIONS,'seed':SEED,'cases':out_cases,
      'guardrails':['No LLM calls.','Persistent-new-basin pattern requires t0-t1 and t0-t2 drift support plus no t1-t2 drift support for the same metric.','Three checkpoints do not justify fitting a stochastic process.','Historical requested-model identity remains incompletely observed.','Production default unchanged.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    return 0
if __name__=='__main__': raise SystemExit(main())
