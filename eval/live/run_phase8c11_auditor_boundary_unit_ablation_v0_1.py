from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
import subprocess, sys

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.services.cognitive_impact import legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess, native_locate
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import (
    _assessment,_code_maps,_features,_matches,_nodes,_forced_chat,
    match_detail_key,serialize_effect,serialize_native_matches,topology_key,
)
from eval.live.topology_stability_metrics_v0_1 import summarize_topology_stability,categorical_stability,execution_snapshot

RUN_VERSION='phase8c11-auditor-boundary-unit-ablation-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase8c11_auditor_boundary_unit_ablation_v0_1'
SOURCE=ROOT/'eval/live/results/phase8c10_auditor_topology_stability_v0_1/phase8c10_auditor_topology_stability_v0.1_20260910T034034Z.json'
SOURCE_SHA='bf535061ac92bec498816b932454be5bba9e4ab390e1572d88b9a68c52fcd69e'
SPECS={
 'RS05': {'full_requires':{'RS05-U06','RS05-U08'}, 'remove':{'RS05-U06','RS05-U08'}, 'critical':{('CHALLENGE','CF-B-PERF')}},
 'RS15': {'full_requires':{'RS15-NEU4'}, 'remove':{'RS15-NEU4'}, 'critical':{('REINFORCE','B2'),('REINFORCE','Q2')}},
 'RS11': {'full_requires':{'RS11-N1'}, 'remove':{'RS11-N1'}, 'critical':set()},
 'RS12': {'full_requires':{'RS12-N11'}, 'remove':{'RS12-N11'}, 'critical':set()},
}

def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def verify():
    d=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if d!=SOURCE_SHA: raise RuntimeError(f'source sha mismatch {d}')

def load_worlds():
    verify(); data=json.loads(SOURCE.read_text()); out={}
    for case in data['results']:
        cid=case['case']
        if cid not in SPECS: continue
        req=SPECS[cid]['full_requires']
        candidates=[r for r in case['runs'] if r.get('status')=='OK' and req.issubset(set(r['admitted_ids']))]
        if not candidates: raise RuntimeError(f'no full world for {cid}')
        # Prefer the modal fresh world when several satisfy the requirement.
        counts=Counter(tuple(r['admitted_ids']) for r in candidates); key=counts.most_common(1)[0][0]
        full=next(r for r in candidates if tuple(r['admitted_ids'])==key)
        full_units=list(full['admitted_units']); remove=SPECS[cid]['remove']
        ablated=[u for u in full_units if str(u['unit_id']) not in remove]
        out[cid]={
            'full':full_units,'ablated':ablated,
            'full_ids':tuple(sorted(str(u['unit_id']) for u in full_units)),
            'ablated_ids':tuple(sorted(str(u['unit_id']) for u in ablated)),
            'removed_ids':tuple(sorted(remove)),
        }
    return out

def modal_locate(units,nodes,code_by_uuid,repeats,cid,arm):
    rows=[]; objs={}
    for i in range(1,repeats+1):
        try:
            matches,meta,events=native_locate(units,nodes,chat_fn=_forced_chat)
            key=match_detail_key(matches,code_by_uuid)
            row={'repeat':i,'status':'OK','detail_key':key,'matches':serialize_native_matches(matches,code_by_uuid),'meta':meta,'schema_events':events}; objs[i]=matches
        except Exception as exc: row={'repeat':i,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
        rows.append(row); print(json.dumps({'case':cid,'arm':arm,'stage':'LOCATE','repeat':i,'status':row['status'],'detail':row.get('detail_key')},ensure_ascii=False),flush=True)
    ok=[r for r in rows if r['status']=='OK']; counts=Counter(r['detail_key'] for r in ok); best=max(counts.values()); key=sorted((k for k,v in counts.items() if v==best),key=repr)[0]; rep=next(r for r in ok if r['detail_key']==key)
    return rows,key,objs[rep['repeat']]

def impact_once(units,nodes,code_by_str,matches):
    parsed,meta,events=native_assess(units,nodes,matches,chat_fn=_forced_chat)
    prod=_matches(matches,nodes); ass=_assessment(parsed,nodes); norm=normalize_frozen_transition(ass,prod).assessment; legal=legal_public_effects(norm)
    strategy=get_decision_strategy('pareto-multidelta-magnitude-free-anchored-open-new')
    plan=route(_features(parsed),RuntimeView(),assessment=norm,matches=prod,decision_strategy=strategy)
    return {'status':'OK','topology_key':topology_key(legal,code_by_str),'effects':[serialize_effect(e,code_by_str) for e in legal],'attention':plan.disposition.value,'meta':meta,'schema_events':events},strategy.execution_snapshot()

def summarize_arm(rows,critical):
    ok=[r for r in rows if r['status']=='OK']; tops=[r['topology_key'] for r in ok]; at=[r['attention'] for r in ok]
    rep=summarize_topology_stability(tops,critical_relations=critical)
    return {'topology':rep.as_dict(),'attention_counts':dict(Counter(at)),'attention_stability':categorical_stability(at)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--locate-repeats',type=int,default=3); ap.add_argument('--impact-repeats',type=int,default=6); args=ap.parse_args()
    worlds=load_worlds(); results=[]; strategy_snapshot=None
    for cid,w in worlds.items():
        nodes=_nodes(cid); code_by_uuid,code_by_str=_code_maps(nodes)
        loc={}; frozen={}
        for arm in ('full','ablated'):
            rows,key,matches=modal_locate(w[arm],nodes,code_by_uuid,args.locate_repeats,cid,arm); loc[arm]={'modal_detail_key':key,'runs':rows}; frozen[arm]=matches
        impacts={'full':[],'ablated':[]}
        for repeat in range(1,args.impact_repeats+1):
            for arm in ('full','ablated'):
                try:
                    row,strategy_snapshot=impact_once(w[arm],nodes,code_by_str,frozen[arm]); row['repeat']=repeat
                except Exception as exc: row={'repeat':repeat,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
                impacts[arm].append(row); print(json.dumps({'case':cid,'arm':arm,'stage':'IMPACT','repeat':repeat,'status':row['status'],'topology':row.get('topology_key'),'attention':row.get('attention')},ensure_ascii=False),flush=True)
        results.append({'case':cid,**{k:v for k,v in w.items() if k.endswith('_ids')},'locate':loc,'impact':impacts,'summary':{arm:summarize_arm(impacts[arm],SPECS[cid]['critical']) for arm in ('full','ablated')}})
    summary={r['case']:{'removed_ids':r['removed_ids'],'full':r['summary']['full'],'ablated':r['summary']['ablated']} for r in results}
    output={'run_version':RUN_VERSION,'status':'BOUNDARY_UNIT_CAUSAL_ABLATION','measurement_sha':git_head(),'source_artifact':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,'locate_repeats':args.locate_repeats,'impact_repeats':args.impact_repeats,'metrics_chip':execution_snapshot(),'decision_strategy':strategy_snapshot,'results':results,'summary':summary}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); path=OUT_DIR/f"{RUN_VERSION.replace('-','_')}_{stamp}.json"; path.write_text(json.dumps(output,ensure_ascii=False,indent=2,default=str)+'\n')
    print(f'RESULT_PATH={path.relative_to(ROOT)}'); print(f'RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}'); print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
