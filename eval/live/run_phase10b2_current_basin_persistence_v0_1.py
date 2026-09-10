from __future__ import annotations

from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()
from app.config import settings
from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import get_decision_strategy
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase8c3_native_cognitive_interface_v0_1 import NATIVE_IMPACT_SYSTEM, native_assess
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, execution_snapshot as map_snapshot
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import _forced_chat, _nodes, load_units, serialize_effect
from eval.live.run_phase8c12_locate_relation_longitudinal_v0_1 import reconstruct_historical_modal_matches, current_attention, load_verified
from eval.live.run_phase8c14_open_new_branch_causal_attribution_v0_1 import branch_relation_key
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _features, _matches

RUN_VERSION='phase10b2-current-basin-persistence-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10b2_current_basin_persistence_v0_1'
SOURCE8=ROOT/'eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json'
SOURCE8_SHA='f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216'
CASES=('RS05','RS15','RS11','RS12')
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
N=12

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def prompt_sha(): return hashlib.sha256(NATIVE_IMPACT_SYSTEM.encode()).hexdigest()

def collect(case, ordinal, hist_case, strategy):
    units,_=load_units(case); nodes=_nodes(case)
    native_matches=reconstruct_historical_modal_matches(hist_case,nodes)
    prod_matches=_matches(native_matches,nodes)
    parsed,meta,events=native_assess(units,nodes,native_matches,chat_fn=_forced_chat)
    disposition,legal=current_attention(parsed,native_matches,nodes)
    key=branch_relation_key(case,nodes)
    report=analyze_decision_causal_core(
        assessment=CognitiveImpactAssessment(effects=legal), matches=prod_matches,
        features=_features(parsed), decision_strategy=strategy, relation_key=key)
    if report.baseline_decision != disposition:
        raise RuntimeError(f'causal baseline mismatch {case} {ordinal}')
    _,code_by_str=__import__('eval.live.run_phase8c8_semantic_topology_stability_v0_1',fromlist=['_code_maps'])._code_maps(nodes)
    return {
        'sample_id':f't2-{ordinal}',
        'topology':sorted({key(e) for e in legal},key=repr),
        'necessary_core':report.necessary_core,
        'sufficient_supports':report.sufficient_supports,
        'attention':disposition,
        'effects':[serialize_effect(e,code_by_str) for e in legal],
        'causal_profile':report.as_dict(), 'meta':meta, 'schema_events':events,
    }

def main():
    started=datetime.now(timezone.utc)
    d8=load_verified(SOURCE8,SOURCE8_SHA); hist={r['case']:r for r in d8['cases']}
    strategy=get_decision_strategy(STRATEGY_ID)
    samples={}; maps={}
    for case in CASES:
        rows=[]
        for i in range(1,N+1):
            s=collect(case,i,hist[case],strategy); rows.append(s)
            print(json.dumps({'case':case,'sample':i,'attention':s['attention'],'topology':s['topology'],'necessary':s['necessary_core'],'sufficient':s['sufficient_supports'],'requested_model':s['meta'].get('requested_model'),'response_model':s['meta'].get('response_model')},ensure_ascii=False),flush=True)
        samples[case]=rows; maps[case]=summarize_static_cognitive_map(rows)
    finished=datetime.now(timezone.utc)
    requested=sorted({s['meta'].get('requested_model') for rows in samples.values() for s in rows if s.get('meta')})
    response=sorted({s['meta'].get('response_model') for rows in samples.values() for s in rows if s.get('meta')})
    temps=sorted({s['meta'].get('temperature') for rows in samples.values() for s in rows if s.get('meta')})
    out={
      'run_version':RUN_VERSION,'status':'INDEPENDENT_CURRENT_CHECKPOINT','measurement_sha':git_head(),
      'epoch':{'started_at':started.isoformat(),'finished_at':finished.isoformat(),'n_per_case':N},
      'source_phase8c8':str(SOURCE8.relative_to(ROOT)),'source_phase8c8_sha256':SOURCE8_SHA,
      'frozen_contract':{
        'relation_mapping_system_prompt_sha256':prompt_sha(),
        'configured_requested_model':settings.llm_model,
        'requested_models_seen':requested,'response_models_seen':response,'temperatures_seen':temps,
        'thinking':'disabled','decision_strategy':strategy.execution_snapshot(),'map_chip':map_snapshot(),
        'audited_semantic_world':'Phase8C8 exact frozen admitted units','locate':'Phase8C8 exact historical modal fixture'},
      'maps':maps,'samples':samples,
      'guardrails':['No Sensor or Auditor calls.','All twelve samples per case are fresh Relation Mapping realizations in this checkpoint.','No adaptive expansion.','Production default unchanged.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=finished.strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    for c,m in maps.items(): print(c,m['attention_distribution'])
    return 0
if __name__=='__main__': raise SystemExit(main())
