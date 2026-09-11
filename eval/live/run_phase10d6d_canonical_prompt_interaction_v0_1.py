from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.prompts import IMPACT_SYSTEM, IMPACT_SYSTEM_VNEXT
from app.services.cognitive_impact import CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import audited_units_to_extraction, build_phase6b_mvp_kernel_nodes
from eval.live.phase8c2_production_sensor_bridge_v0_1 import _project_production_separations
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches, effect_row
from eval.live.run_phase10d6c_canonical_input_reconciliation_v0_1 import canonical_assess

RUN_VERSION='phase10d6d-canonical-prompt-interaction-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10d6d_canonical_prompt_interaction_v0_1'
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
CASES=('A','D','X','N4')
REPEATS=6


def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_one(label,arm,ordinal,case,nodes,matches,strategy):
    extraction=_project_production_separations(audited_units_to_extraction(deepcopy(case['frozen_units'])))
    system=IMPACT_SYSTEM if arm=='C0' else IMPACT_SYSTEM_VNEXT
    version='production-impact-v2.1-legacy' if arm=='C0' else 'canonical-impact-vnext-v0.1'
    provider=ModelBackedCognitiveProvider(impact_system_prompt=system,impact_contract_version=version)
    assessment=canonical_assess(provider,case['frozen_units'],extraction,matches,nodes,system_prompt=system)
    normalized=normalize_frozen_transition(assessment,matches).assessment
    legal=legal_public_effects(normalized)
    final=CognitiveImpactAssessment(effects=legal,attention_cost=assessment.attention_cost,
        exploration_candidate=assessment.exploration_candidate,features=assessment.features,raw_effects=assessment.raw_effects)
    plan=route(assessment.features,RuntimeView(),assessment=final,matches=matches,decision_strategy=strategy)
    key=branch_relation_key(nodes,case['frozen_units'])
    report=analyze_decision_causal_core(assessment=final,matches=matches,features=assessment.features,
        decision_strategy=strategy,relation_key=key)
    if report.baseline_decision!=plan.disposition.value: raise RuntimeError(f'causal baseline mismatch {label}/{arm}/{ordinal}')
    return {'sample_id':f'{arm}-{ordinal}','arm':arm,'status':'OK',
        'raw_effects':[effect_row(e,nodes) for e in provider.last_raw_effects],
        'grounded_effects':[effect_row(e,nodes) for e in legal],
        'raw_effect_count':len(provider.last_raw_effects),'grounded_effect_count':len(legal),
        'topology':sorted({key(e) for e in legal},key=repr),'necessary_core':report.necessary_core,
        'sufficient_supports':report.sufficient_supports,'attention':plan.disposition.value,
        'causal_profile':report.as_dict(),'meta':dict(provider.last_meta),'impact_contract_version':version}


def summarize(rows):
    ok=[r for r in rows if r.get('status')=='OK']
    samples=[{k:r[k] for k in ('sample_id','topology','necessary_core','sufficient_supports','attention')} for r in ok]
    return {'n_ok':len(ok),'n_error':len(rows)-len(ok),'attention_counts':dict(sorted(Counter(r['attention'] for r in ok).items())),
        'raw_effect_count_mean':sum(r['raw_effect_count'] for r in ok)/len(ok) if ok else 0,
        'grounded_effect_count_mean':sum(r['grounded_effect_count'] for r in ok)/len(ok) if ok else 0,
        'map':summarize_static_cognitive_map(samples) if ok else None}


def main():
    selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); strategy=get_decision_strategy(STRATEGY_ID); results={}
    for label in CASES:
        case=selected[label]['case']; matches=reconstruct_prod_matches(case,nodes); arms={'C0':[],'C1':[]}
        for ordinal in range(1,REPEATS+1):
            for arm in ('C0','C1'):
                try: row=run_one(label,arm,ordinal,case,nodes,matches,strategy)
                except Exception as exc: row={'sample_id':f'{arm}-{ordinal}','arm':arm,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
                arms[arm].append(row)
                print(json.dumps({'label':label,'arm':arm,'repeat':ordinal,'status':row['status'],'raw':row.get('raw_effect_count'),
                    'grounded':row.get('grounded_effect_count'),'attention':row.get('attention'),'topology':row.get('topology'),'error':row.get('error')},ensure_ascii=False),flush=True)
        results[label]={'arms':arms,'summary':{a:summarize(v) for a,v in arms.items()},
            'frozen_units_replay_sha256':case['frozen_units_replay_sha256'],'frozen_locate':case['locate']['modal']}
        print(json.dumps({'label':label,'summary':{a:{k:v for k,v in results[label]['summary'][a].items() if k!='map'} for a in arms}},ensure_ascii=False),flush=True)
    out={'run_version':RUN_VERSION,'status':'CANONICAL_PROMPT_INTERACTION_SHADOW','measurement_sha':git_head(),
        'repeats_per_arm':REPEATS,'cases':list(CASES),'controlled_variable':'impact_system_prompt_on_canonical_input',
        'decision_strategy':strategy.execution_snapshot(),'results':results,
        'guardrails':['Both arms consume identical canonical audited units directly.','Same Kernel, Locate, model path, importance resolver, grounding, features, runtime and decision strategy.',
                      'Only the Impact system prompt differs.','Raw and grounded effects are both persisted.','No expansion or prompt editing.','Production default unchanged.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); return 0
if __name__=='__main__': raise SystemExit(main())
