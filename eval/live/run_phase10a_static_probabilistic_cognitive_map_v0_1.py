from __future__ import annotations

import argparse
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

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM, native_assess
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, execution_snapshot as map_snapshot
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import _forced_chat, _nodes, load_units, serialize_effect
from eval.live.run_phase8c12_locate_relation_longitudinal_v0_1 import (
    reconstruct_historical_modal_matches, current_attention, load_verified,
)
from eval.live.run_phase8c14_open_new_branch_causal_attribution_v0_1 import branch_relation_key
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _features, _matches

RUN_VERSION='phase10a-static-probabilistic-cognitive-map-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10a_static_probabilistic_cognitive_map_v0_1'
CASES=('RS05','RS15','RS11','RS12')
SOURCE8=ROOT/'eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json'
SOURCE8_SHA='f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216'
SOURCE12=ROOT/'eval/live/results/phase8c12_locate_relation_longitudinal_v0_1/phase8c12_locate_relation_longitudinal_v0.1_20260910T072032Z.json'
SOURCE12_SHA='a67d7e40e403c7ad9bd7dd6a82312fd5c720ada0f2bf683b506475eb3d92e8be'
SOURCE14=ROOT/'eval/live/results/phase8c14_open_new_branch_causal_attribution_v0_1/phase8c14_open_new_branch_causal_attribution_v0.1_20260910T073517Z.json'
SOURCE14_SHA='1327abc2899acf7c93a936dd824c2ea139ae17e6b081fb9057678bdc342583f2'
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
INITIAL_N=12
EXPANDED_N=24
HALF_WIDTH_GATE=.20

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def freeze(x):
    if isinstance(x,list): return tuple(freeze(v) for v in x)
    return x

def prompt_sha(): return hashlib.sha256(NATIVE_IMPACT_SYSTEM.encode()).hexdigest()

def seed_sample(row):
    cp=row['causal_profile']
    return {
        'sample_id':f"seed-{row['repeat']}", 'source':'phase8c14/phase8c12-current',
        'topology':[freeze(r) for r in row['branch_topology']],
        'necessary_core':[freeze(r) for r in cp['necessary_core']],
        'sufficient_supports':[freeze(r) for r in cp['sufficient_supports']],
        'attention':row['attention'], 'meta':None, 'schema_events':[],
    }

def collect_sample(case, ordinal, hist_case, strategy):
    units,_=load_units(case); nodes=_nodes(case)
    native_matches=reconstruct_historical_modal_matches(hist_case,nodes)
    prod_matches=_matches(native_matches,nodes)
    parsed,meta,events=native_assess(units,nodes,native_matches,chat_fn=_forced_chat)
    disposition,legal=current_attention(parsed,native_matches,nodes)
    key=branch_relation_key(case,nodes)
    ass=CognitiveImpactAssessment(effects=legal)
    report=analyze_decision_causal_core(
        assessment=ass,matches=prod_matches,features=_features(parsed),
        decision_strategy=strategy,relation_key=key,
    )
    if report.baseline_decision != disposition:
        raise RuntimeError(f'causal baseline mismatch {case} {ordinal}: {report.baseline_decision}!={disposition}')
    _,code_by_str=__import__('eval.live.run_phase8c8_semantic_topology_stability_v0_1',fromlist=['_code_maps'])._code_maps(nodes)
    present=sorted({key(e) for e in legal},key=repr)
    return {
        'sample_id':f'fresh-{ordinal}', 'source':'phase10a-fresh-relation',
        'topology':present,
        'necessary_core':report.necessary_core,
        'sufficient_supports':report.sufficient_supports,
        'attention':disposition,
        'effects':[serialize_effect(e,code_by_str) for e in legal],
        'causal_profile':report.as_dict(),'meta':meta,'schema_events':events,
    }

def expansion_reasons(m):
    reasons=[]
    att=m['attention_distribution']
    lo,hi=att['dominant_wilson95']
    if (hi-lo)/2 > HALF_WIDTH_GATE:
        reasons.append({'kind':'dominant_attention_precision','half_width':(hi-lo)/2,'action':att['dominant_action']})
    for rel,row in m['relation_map'].items():
        p=row['load_bearing']['p']; hw=row['load_bearing']['half_width']
        if .25 <= p <= .75 and hw > HALF_WIDTH_GATE:
            reasons.append({'kind':'load_bearing_precision','relation':rel,'p':p,'half_width':hw})
    return reasons

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--initial-n',type=int,default=INITIAL_N); ap.add_argument('--expanded-n',type=int,default=EXPANDED_N); args=ap.parse_args()
    if args.initial_n < 6 or args.expanded_n < args.initial_n: raise ValueError('invalid sample targets')
    d8=load_verified(SOURCE8,SOURCE8_SHA); load_verified(SOURCE12,SOURCE12_SHA); d14=load_verified(SOURCE14,SOURCE14_SHA)
    hist={r['case']:r for r in d8['cases']}; strategy=get_decision_strategy(STRATEGY_ID)
    all_samples={}; stage12_maps={}; expansion={}
    for case in CASES:
        samples=[seed_sample(r) for r in d14['results'][case]['samples']]
        for ordinal in range(len(samples)+1,args.initial_n+1):
            s=collect_sample(case,ordinal,hist[case],strategy); samples.append(s)
            print(json.dumps({'case':case,'stage':'N12','sample':ordinal,'attention':s['attention'],'topology':s['topology'],'necessary':s['necessary_core'],'sufficient':s['sufficient_supports']},ensure_ascii=False),flush=True)
        m=summarize_static_cognitive_map(samples)
        reasons=expansion_reasons(m); stage12_maps[case]=m; expansion[case]={'triggered':bool(reasons),'reasons':reasons}
        print(json.dumps({'case':case,'stage':'N12_MAP','attention':m['attention_distribution'],'expansion':expansion[case]},ensure_ascii=False),flush=True)
        if reasons:
            for ordinal in range(len(samples)+1,args.expanded_n+1):
                s=collect_sample(case,ordinal,hist[case],strategy); samples.append(s)
                print(json.dumps({'case':case,'stage':'N24','sample':ordinal,'attention':s['attention'],'topology':s['topology'],'necessary':s['necessary_core'],'sufficient':s['sufficient_supports']},ensure_ascii=False),flush=True)
        all_samples[case]=samples
    final_maps={c:summarize_static_cognitive_map(v) for c,v in all_samples.items()}
    declared_models=sorted({s['meta'].get('model') for rows in all_samples.values() for s in rows if s.get('meta') and s['meta'].get('model')})
    declared_temps=sorted({s['meta'].get('temperature') for rows in all_samples.values() for s in rows if s.get('meta')})
    out={
        'run_version':RUN_VERSION,'status':'STATIC_BOUNDED_EPOCH_EMPIRICAL_MAP','measurement_sha':git_head(),
        'sources':{
            'phase8c8':str(SOURCE8.relative_to(ROOT)),'phase8c8_sha256':SOURCE8_SHA,
            'phase8c12':str(SOURCE12.relative_to(ROOT)),'phase8c12_sha256':SOURCE12_SHA,
            'phase8c14':str(SOURCE14.relative_to(ROOT)),'phase8c14_sha256':SOURCE14_SHA,
        },
        'sampling':{'initial_n':args.initial_n,'expanded_n':args.expanded_n,'half_width_gate':HALF_WIDTH_GATE,'expansion':expansion},
        'frozen_contract':{
            'relation_mapping_system_prompt_sha256':prompt_sha(), 'models_seen':declared_models,'temperatures_seen':declared_temps,
            'thinking':'disabled','decision_strategy':strategy.execution_snapshot(),'map_chip':map_snapshot(),
            'audited_semantic_world':'Phase8C8 exact frozen admitted units','locate':'Phase8C8 exact historical modal fixture',
        },
        'n12_maps':stage12_maps,'final_maps':final_maps,'samples':all_samples,
        'guardrails':['No Sensor or Auditor calls.','Seed six samples are exact current Relation realizations from Phase8C12/8C14.','Additional samples change only Relation Mapping realization inside the same bounded session epoch.','Expansion follows preregistered Wilson precision gate.','OPEN_NEW identity uses explicit source-unit branch signatures.','This is a static empirical map, not a temporal stochastic-process model.','Production default unchanged.'],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    for case,m in final_maps.items():
        print('\n###',case,'N=',m['n']); print('ATTN',m['attention_distribution']); print('TOPO_H',m['topology_distribution']['entropy_bits'],'CORE_H',m['load_bearing_distribution']['entropy_bits'])
        for rel,row in sorted(m['relation_map'].items(),key=lambda kv:(-kv[1]['load_bearing']['p'],-kv[1]['topology']['p'],kv[0])):
            if row['load_bearing']['p']>0: print(rel,'P(T)=',row['topology']['p'],'P(B)=',row['load_bearing']['p'],'CI=',row['load_bearing']['wilson95'])
    return 0
if __name__=='__main__': raise SystemExit(main())
