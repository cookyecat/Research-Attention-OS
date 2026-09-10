from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.cognitive_map_distance_v0_1 import compare_cognitive_maps, execution_snapshot as distance_snapshot
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, execution_snapshot as map_snapshot
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import _nodes
from eval.live.run_phase8c12_locate_relation_longitudinal_v0_1 import reconstruct_historical_modal_matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features, reconstruct_effects
from eval.live.run_phase8c14_open_new_branch_causal_attribution_v0_1 import branch_relation_key
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _matches

RUN_VERSION='phase10b-temporal-cognitive-basin-shift-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10b_temporal_cognitive_basin_shift_v0_1'
SOURCE8=ROOT/'eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json'
SOURCE8_SHA='f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216'
SOURCE9=ROOT/'eval/live/results/phase8c9_anchored_open_new_admission_v0_1/phase8c9_anchored_open_new_admission_v0.1_20260909T200448Z.json'
SOURCE9_SHA='01e74482a1883b234f9446efd2cfd7ce6af2d23930c09a303460c5a58ade8efe'
SOURCE10A=ROOT/'eval/live/results/phase10a_static_probabilistic_cognitive_map_v0_1/phase10a_static_probabilistic_cognitive_map_v0.1_20260910T075824Z.json'
SOURCE10A_SHA='f3a56fdd7a1d3c95a96b41ae1a282f3ae1c94218b4adc43e7ed23390f5be25b7'
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
CASES=('RS05','RS15','RS11','RS12')

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_verified(p,h):
    a=sha256(p)
    if a!=h: raise RuntimeError(f'SHA mismatch {p}: {a}')
    return json.loads(Path(p).read_text())
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def freeze(x):
    if isinstance(x,list): return tuple(freeze(v) for v in x)
    return x

def historical_samples(case, hist_case, expected_rows, strategy):
    nodes=_nodes(case)
    native_matches=reconstruct_historical_modal_matches(hist_case,nodes)
    prod_matches=_matches(native_matches,nodes)
    key=branch_relation_key(case,nodes)
    expected={(r['case'],int(r['repeat'])):r['candidate']['disposition'] for r in expected_rows}
    rows=[]
    for run in hist_case['impact']['runs']:
        if run.get('status')!='OK': continue
        effects=reconstruct_effects(run['effects'],nodes)
        ass=CognitiveImpactAssessment(effects=effects)
        base=route(features(),RuntimeView(),assessment=ass,matches=prod_matches,decision_strategy=strategy).disposition.value
        exp=expected.get((case,int(run['repeat'])))
        if exp is not None and base!=exp:
            raise RuntimeError(f'historical strategy replay mismatch {case} r{run["repeat"]}: {base}!={exp}')
        core=analyze_decision_causal_core(assessment=ass,matches=prod_matches,features=features(),decision_strategy=strategy,relation_key=key)
        rows.append({
            'sample_id':f't0-{run["repeat"]}',
            'topology':sorted({key(e) for e in effects},key=repr),
            'necessary_core':core.necessary_core,
            'sufficient_supports':core.sufficient_supports,
            'attention':base,
        })
    return rows

def current_samples(rows):
    out=[]
    for s in rows:
        out.append({
            'sample_id':s.get('sample_id'),
            'topology':[freeze(r) for r in s.get('topology') or []],
            'necessary_core':[freeze(r) for r in s.get('necessary_core') or []],
            'sufficient_supports':[freeze(r) for r in s.get('sufficient_supports') or []],
            'attention':s['attention'],
        })
    return out

def main():
    d8=load_verified(SOURCE8,SOURCE8_SHA); d9=load_verified(SOURCE9,SOURCE9_SHA); d1=load_verified(SOURCE10A,SOURCE10A_SHA)
    by8={r['case']:r for r in d8['cases']}; strategy=get_decision_strategy(STRATEGY_ID)
    t0_maps={}; comparisons={}; t0_samples_all={}; t1_samples_all={}
    for case in CASES:
        t0=historical_samples(case,by8[case],d9['replay_rows'],strategy)
        t1=current_samples(d1['samples'][case])
        m0=summarize_static_cognitive_map(t0); m1=summarize_static_cognitive_map(t1)
        # Verify current map reconstruction matches the canonical Phase10A sample count and attention counts.
        if m1['n'] != d1['final_maps'][case]['n'] or m1['attention_distribution']['counts'] != d1['final_maps'][case]['attention_distribution']['counts']:
            raise RuntimeError(f'Phase10A reconstruction mismatch {case}')
        cmp=compare_cognitive_maps(m0,t0,m1,t1)
        t0_maps[case]=m0; comparisons[case]=cmp; t0_samples_all[case]=t0; t1_samples_all[case]=t1
        print(json.dumps({
            'case':case,'n_t0':len(t0),'n_t1':len(t1),
            'attention_js_bits':cmp['attention_js_bits'],
            'load_bearing_js_bits':cmp['load_bearing_state_js_bits'],
            'topology_js_bits':cmp['topology_state_js_bits'],
            'attention_t0':cmp['attention_t0'],'attention_t1':cmp['attention_t1'],
            'max_core_frequency_drift':cmp['load_bearing_relation_frequency_drift']['max_abs_delta'],
        },ensure_ascii=False),flush=True)
    out={
        'run_version':RUN_VERSION,'status':'SYSTEM_LEVEL_CROSS_EPOCH_DISTRIBUTION_COMPARISON','measurement_sha':git_head(),
        'sources':{
            't0_phase8c8':str(SOURCE8.relative_to(ROOT)),'t0_phase8c8_sha256':SOURCE8_SHA,
            't0_policy_replay_phase8c9':str(SOURCE9.relative_to(ROOT)),'t0_policy_replay_phase8c9_sha256':SOURCE9_SHA,
            't1_phase10a':str(SOURCE10A.relative_to(ROOT)),'t1_phase10a_sha256':SOURCE10A_SHA,
        },
        'configuration_identity':{
            't0_response_model':'deepseek-v4-flash',
            't0_requested_model':'NOT_DIRECTLY_RECORDED',
            't1_requested_model':'deepseek-v4-flash (current instrumentation/live probe)',
            't1_response_model':'deepseek-flash',
            'interpretation':'current probe proves request/response alias can differ; historical request identity is inferred, so provider/model-causal attribution is forbidden',
        },
        'decision_strategy':strategy.execution_snapshot(),'map_chip':map_snapshot(),'distance_chip':distance_snapshot(),
        't0_maps':t0_maps,'t1_maps':{c:d1['final_maps'][c] for c in CASES},'comparisons':comparisons,
        't0_samples':t0_samples_all,'t1_samples':t1_samples_all,
        'guardrails':['No LLM calls.','Both epochs replay/measure Article Attention under the same anchored-open-new plus magnitude-free Pareto strategy.','OPEN_NEW uses explicit source-unit branch identity.','JSD is descriptive empirical distance, not a calibrated significance test.','Historical requested-model identity was not directly recorded.','Do not attribute cross-epoch drift purely to model/provider drift.','No stochastic-process model is fitted.'],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    print('\nSUMMARY')
    for case,c in comparisons.items():
        print(case, json.dumps({k:c[k] for k in ['attention_js_bits','load_bearing_state_js_bits','topology_state_js_bits','attention_t0','attention_t1']},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
