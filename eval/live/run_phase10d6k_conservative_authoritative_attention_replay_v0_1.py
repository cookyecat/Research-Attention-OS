from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.client import chat_json
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment, node_proposition
from app.services.scheduler import get_decision_strategy
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6j_relation_support_directness_v0_1 import SYSTEM_PROMPT, DirectnessResponse, build_user_prompt
from eval.live.phase10d6k_authoritative_attention_v0_1 import VERSION as AUTHORITY_VERSION, enrich_for_arm
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features

RUN_VERSION='phase10d6k-conservative-authoritative-attention-replay-v0.1'
SOURCE=ROOT/'eval/live/results/phase10d6h_cardinal_field_removal_parity_v0_1/phase10d6h_cardinal_field_removal_parity_v0.1_20260911T071632Z.json'
SOURCE_SHA='86e1dc644aa0b7a8e6f559b2fd674357268ba12ecd82b586ed626b655965e29c'
HIST=ROOT/'eval/live/results/phase10d4_real_web_basin_persistence_v0_1/phase10d4_real_web_basin_persistence_v0.1_20260910T160403Z.json'
HIST_SHA='5299cab0607779989b896148765f5c6ef9873b001449b73f51cba6b67e7438a7'
OUT_DIR=ROOT/'eval/live/results/phase10d6k_conservative_authoritative_attention_replay_v0_1'
CASES=('A','D','X','N4'); REPEATS=5
ARMS=('K0_ALL_SUPPORT_SUFFICIENT','K1_SINGLE_SOURCE_WEAK','K2_CANONICAL_AUTHORITY')
PROVENANCE={'A':'PRIMARY_SOURCE','D':'SECONDARY_REPORT','X':'PRIMARY_SOURCE','N4':'PRIMARY_SOURCE'}
FIT_SEVERITY={'DIRECT':0,'PARTIAL':1,'INSUFFICIENT':2,'CONTRADICTS_OPERATION':3}
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def forced_chat(messages,**kwargs): return chat_json(messages,timeout=float(kwargs.get('timeout') or 60.0),thinking=kwargs.get('thinking'),reasoning_effort=kwargs.get('reasoning_effort'),temperature=.1)

def signature(row): return (row['operation'],row.get('target'),tuple(sorted(row.get('support_unit_ids') or [])))
def signature_id(label,sig):
    raw=json.dumps([label,*sig[:2],list(sig[2])],ensure_ascii=False,sort_keys=False)
    return f'{label}::'+hashlib.sha256(raw.encode()).hexdigest()[:16]

def build_directness_items(label, case, hcase, nodes):
    by_code={str((n.payload or {}).get('phase6b_fixture_code') or n.title):n for n in nodes}
    units={str(u.get('unit_id')):u for u in case['frozen_units']}; first={}
    for sample in hcase['samples']:
        for row in sample['normalized_effects']:
            if row['operation']=='OPEN_NEW': continue
            sig=signature(row); first.setdefault(sig,row)
    items=[]; sig_by_id={}
    for sig,row in sorted(first.items(),key=lambda kv:repr(kv[0])):
        iid=signature_id(label,sig); sig_by_id[iid]=sig; supports=[]
        for uid in row.get('support_unit_ids') or []:
            u=units[uid]; supports.append({'unit_id':uid,'statement':str(u.get('statement') or ''),'epistemic_status':str(u.get('epistemic_status') or ''),'support_excerpts':[str(s.get('support_excerpt') or '')[:900] for s in (u.get('supports') or [])]})
        node=by_code[row['target']]
        items.append({'item_id':iid,'operation':row['operation'],'target_code':row['target'],'target_proposition':node_proposition(node),'support_units':supports,'relation_reason':row.get('reason','')})
    return items,sig_by_id

def conservative_modal(values):
    c=Counter(values); top=max(c.values()); tied=[k for k,v in c.items() if v==top]
    return max(tied,key=lambda x:FIT_SEVERITY[x]),dict(c)

def classify_case(label,items,sig_by_id):
    expected={x['item_id'] for x in items}; rows=[]
    for rep in range(1,REPEATS+1):
        provider=ModelBackedCognitiveProvider(chat_fn=forced_chat)
        parsed=provider._complete(SYSTEM_PROMPT,build_user_prompt(items),DirectnessResponse,stage='impact')
        got=[x.item_id for x in parsed.classifications]
        if len(got)!=len(expected) or len(set(got))!=len(got) or set(got)!=expected: raise RuntimeError(f'DIRECTNESS_ID_MISMATCH {label} rep={rep}')
        rows.append({'repeat':rep,'by_id':{x.item_id:x.model_dump() for x in parsed.classifications},'meta':dict(provider.last_meta)})
    modal={}; details={}
    for iid,sig in sig_by_id.items():
        fit,counts=conservative_modal([r['by_id'][iid]['fit'] for r in rows]); modal[sig]=fit; details[iid]={'signature':[sig[0],sig[1],list(sig[2])],'fit':fit,'counts':counts}
    return modal,details,rows

def make_base(row):
    tid=UUID(row['target_kernel_node_id']) if row.get('target_kernel_node_id') else None
    return CognitiveEffect(target_kernel_node_id=tid,operation=CognitiveEffectKind(row['operation']),change_magnitude=0.0,epistemic_strength=0.0,target_importance=0.0,reason=row.get('reason',''))

def project_sample(label,sample,arm,*,nodes,matches,fit_map,relation_key,strategy):
    effects=[]; traces=[]; rejected=[]
    for row in sample['normalized_effects']:
        base=make_base(row); fit=None if row['operation']=='OPEN_NEW' else fit_map[signature(row)]
        enriched,trace=enrich_for_arm(base,arm=arm,nodes=nodes,matches=matches,fit=fit,provenance_role=PROVENANCE[label],support_bound=bool(row.get('support_unit_ids')))
        trace={**trace,'operation':row['operation'],'target':row.get('target'),'support_unit_ids':row.get('support_unit_ids') or []}
        traces.append(trace)
        if enriched is None: rejected.append(trace)
        else: effects.append(enriched)
    assessment=CognitiveImpactAssessment(effects=effects)
    report=analyze_decision_causal_core(assessment=assessment,matches=matches,features=features(),decision_strategy=strategy,relation_key=relation_key)
    return {'sample_id':sample['sample_id'],'attention':report.baseline_decision,'necessary_core':list(report.necessary_core),'sufficient_supports':list(report.sufficient_supports),'n_pre_grounding':len(sample['normalized_effects']),'n_grounded':len(effects),'n_rejected':len(rejected),'rejected':rejected,'authority_trace':traces}

def hist_counts(hist,label):
    row=hist['cases'][label]
    return {k:dict(Counter(x['attention'] for x in row[k])) for k in ('t1_samples','t2_samples')}

def main():
    if sha256(SOURCE)!=SOURCE_SHA: raise RuntimeError('SOURCE_SHA_MISMATCH')
    if sha256(HIST)!=HIST_SHA: raise RuntimeError('HIST_SHA_MISMATCH')
    src=json.loads(SOURCE.read_text()); hist=json.loads(HIST.read_text()); selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); strategy=get_decision_strategy(STRATEGY_ID)
    out_cases={}; global_changes=Counter()
    for label in CASES:
        case=selected[label]['case']; hcase=src['results'][label]; matches=reconstruct_prod_matches(case,nodes); relation_key=branch_relation_key(nodes,case['frozen_units'])
        items,sig_by_id=build_directness_items(label,case,hcase,nodes); fit_map,fit_details,directness_rows=classify_case(label,items,sig_by_id)
        arm_samples={arm:[] for arm in ARMS}
        for sample in hcase['samples']:
            for arm in ARMS:
                arm_samples[arm].append(project_sample(label,sample,arm,nodes=nodes,matches=matches,fit_map=fit_map,relation_key=relation_key,strategy=strategy))
        summaries={arm:{'attention':dict(Counter(x['attention'] for x in rows)),'grounded_effects':sum(x['n_grounded'] for x in rows),'rejected_effects':sum(x['n_rejected'] for x in rows),'samples':rows} for arm,rows in arm_samples.items()}
        for k1,k2 in zip(arm_samples['K1_SINGLE_SOURCE_WEAK'],arm_samples['K2_CANONICAL_AUTHORITY']):
            if k1['attention']!=k2['attention']: global_changes['K2_changed_vs_K1']+=1
            if k2['attention']=='ENGAGE' and k1['attention']!='ENGAGE': global_changes['K2_new_engage_vs_K1']+=1
            if k2['attention']=='DROP' and k1['attention']!='DROP': global_changes['K2_new_drop_vs_K1']+=1
        out_cases[label]={'provenance_role':PROVENANCE[label],'n_unique_targeted_signatures':len(items),'directness':fit_details,'directness_repeats':directness_rows,'arms':summaries,'historical_10d4_attention_context':hist_counts(hist,label)}
        print(json.dumps({'label':label,'attention':{a:summaries[a]['attention'] for a in ARMS},'rejected_K2':summaries['K2_CANONICAL_AUTHORITY']['rejected_effects']},ensure_ascii=False),flush=True)
    out={'run_version':RUN_VERSION,'status':'CONSERVATIVE_AUTHORITATIVE_ATTENTION_SHADOW','measurement_sha':git_head(),'source_phase10d6h':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,'historical_context_phase10d4':str(HIST.relative_to(ROOT)),'historical_context_sha256':HIST_SHA,'authority_version':AUTHORITY_VERSION,'decision_strategy':strategy.execution_snapshot(),'directness_repeats_per_case':REPEATS,'arms':list(ARMS),'cases':out_cases,'paired_sensitivity':dict(global_changes),'guardrails':['No acquisition, Sensor, Auditor, Locate or Relation-Mapping call occurs.','Directness classifier sees only target proposition, exact support evidence and relation reason; no provenance prestige or Attention.','10D.6J classifier is used conservatively only; it is not promoted as truth oracle.','Ordinal 0/1 values only bridge authoritative bands into the existing Magnitude-Free interface.','Anchored admission, Magnitude-Free channel policy, Pareto frontier, article-level join and runtime semantics are unchanged.','Historical 10D.4 frequencies are context, not Gold.','Production defaults unchanged; Phase 9A paused.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('PAIRED='+json.dumps(dict(global_changes),ensure_ascii=False)); print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
if __name__=='__main__': main()
