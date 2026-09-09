from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json
from pathlib import Path
import subprocess, sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT/'backend'):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.pipeline import _active_kernel
from app.services.scheduler import RuntimeView, SchedulerFeatures, get_decision_strategy, route
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.db import Base

RUN_VERSION='phase8c7-real-web-magnitude-perturbation-v0.1'
SOURCE=ROOT/'eval/live/results/phase8c7_real_web_magnitude_free_validation_v0_1/phase8c7_real_web_magnitude_free_validation_v0.1_20260909T185631Z.json'
SOURCE_SHA='db24df43e836f91cd76767b838e21af67a377b61d69a5801bbb5c6695a135ae1'
OUT=ROOT/'eval/live/results/phase8c7_real_web_magnitude_perturbation_v0_1'
VARIANTS=('original','all_low','all_high','inverse')

def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def features():
    return SchedulerFeatures(topic_relevance=.5,structural_relevance=.2,decision_relevance=.2,novelty=.5,credibility=.6,kernel_delta=.2,bottleneck_alignment=.1,disagreement=0,actionability=.3,temporal_value=.3,cognitive_cost=2,evidence_maturity=.6,threatens_active_work=False)

def mag(v,m):
    if v=='original': return m
    if v=='all_low': return .01
    if v=='all_high': return .99
    if v=='inverse': return 1.0-m
    raise KeyError(v)

def setup():
    eng=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool,future=True)
    Base.metadata.create_all(eng); db=Session(eng,autoflush=False,expire_on_commit=False)
    for n in build_phase6b_mvp_kernel_nodes(): db.add(n)
    db.flush(); nodes=_active_kernel(db)
    by_code={str((n.payload or {}).get('phase6b_fixture_code') or n.title):n for n in nodes}
    return eng,db,by_code

def reconstruct(row,by_code,variant):
    effects=[]; matches={}
    for e in row.get('effects') or []:
        op=CognitiveEffectKind(str(e['operation'])); code=e.get('target'); node=by_code.get(code) if code else None
        target=node.id if node else None
        effects.append(CognitiveEffect(target_kernel_node_id=target,operation=op,change_magnitude=mag(variant,float(e['change_magnitude'])),epistemic_strength=float(e['epistemic_strength']),target_importance=float(e['target_importance']),reason=str(e.get('reason') or ''),exploration_candidate=op==CognitiveEffectKind.OPEN_NEW,target_node_type=node.node_type if node else None))
        if node and node.id not in matches:
            matches[node.id]=KernelMatch(node_id=node.id,node_type=node.node_type,title=node.title,score=.8,reason='frozen real-web topology',structural=False,relevance_type='TOPIC')
    return CognitiveImpactAssessment(effects=effects,attention_cost=2),list(matches.values())

def decide(strategy_id,a,matches):
    plan=route(features(),RuntimeView(),assessment=a,matches=matches,decision_strategy=get_decision_strategy(strategy_id))
    return plan.disposition.value

def main():
    raw=SOURCE.read_bytes(); actual=hashlib.sha256(raw).hexdigest()
    if actual!=SOURCE_SHA: raise RuntimeError(actual)
    src=json.loads(raw); eng,db,by_code=setup(); rows=[]
    try:
        for base in src['rows']:
            if base.get('status')!='OK': continue
            label=base['label']
            for variant in VARIANTS:
                a,matches=reconstruct(base,by_code,variant)
                r={'label':label,'variant':variant,'n_effects':len(a.effects),'raw_cardinal':decide('pareto-multidelta',a,matches),'magnitude_free':decide('pareto-multidelta-magnitude-free',a,matches)}
                rows.append(r); print(json.dumps(r),flush=True)
        summary={}
        for label in ('A','C','D','X'):
            rr=[r for r in rows if r['label']==label]
            rawset={r['raw_cardinal'] for r in rr}; mfset={r['magnitude_free'] for r in rr}
            summary[label]={'n_effects':rr[0]['n_effects'] if rr else 0,'raw_decisions':dict(Counter(r['raw_cardinal'] for r in rr)),'magnitude_free_decisions':dict(Counter(r['magnitude_free'] for r in rr)),'raw_invariant':len(rawset)<=1,'magnitude_free_invariant':len(mfset)<=1}
        output={'run_version':RUN_VERSION,'status':'FROZEN_REAL_WEB_MAGNITUDE_PERTURBATION','measurement_sha':git_head(),'source_artifact':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,'variants':VARIANTS,'summary':summary,'rows':rows}
        OUT.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); path=OUT/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; path.write_text(json.dumps(output,indent=2)+'\n')
        print('RESULT_PATH='+str(path.relative_to(ROOT))); print('RESULT_SHA256='+hashlib.sha256(path.read_bytes()).hexdigest()); print(json.dumps(summary,indent=2))
    finally: db.close(); eng.dispose()
if __name__=='__main__': main()
