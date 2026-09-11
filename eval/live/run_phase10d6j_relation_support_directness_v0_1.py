from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()
from app.cognitive.client import chat_json
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.services.cognitive_impact import node_proposition
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6j_relation_support_directness_v0_1 import VERSION,SYSTEM_PROMPT,DirectnessResponse,build_user_prompt
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases

RUN_VERSION='phase10d6j-relation-support-directness-v0.1'
REFERENCE=ROOT/'eval/live/phase10d6j_relation_support_directness_reference_v0_1.json'
SOURCE=ROOT/'eval/live/results/phase10d6h_cardinal_field_removal_parity_v0_1/phase10d6h_cardinal_field_removal_parity_v0.1_20260911T071632Z.json'
SOURCE_SHA='86e1dc644aa0b7a8e6f559b2fd674357268ba12ecd82b586ed626b655965e29c'
OUT_DIR=ROOT/'eval/live/results/phase10d6j_relation_support_directness_v0_1'
REPEATS=6

def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def forced_chat(messages,**kwargs): return chat_json(messages,timeout=float(kwargs.get('timeout') or 60.0),thinking=kwargs.get('thinking'),reasoning_effort=kwargs.get('reasoning_effort'),temperature=.1)

def materialize(reference):
    if sha256(SOURCE)!=SOURCE_SHA: raise RuntimeError('SOURCE_SHA_MISMATCH')
    src=json.loads(SOURCE.read_text()); worlds=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); code_to_prop={str((n.payload or {}).get('phase6b_fixture_code') or n.title):node_proposition(n) for n in nodes}
    unit_maps={c:{str(u.get('unit_id')):u for u in worlds[c]['case']['frozen_units']} for c in ('A','D','X','N4')}; out=[]
    sample_maps={c:{r['sample_id']:r for r in src['results'][c]['samples']} for c in ('A','D','X','N4')}
    for ref in reference['items']:
        row=sample_maps[ref['case']][ref['sample_id']]; effect=row['valid_effects'][ref['effect_index']]
        if effect['operation']!=ref['operation'] or effect.get('target')!=ref['target']: raise RuntimeError('REFERENCE_EFFECT_MISMATCH')
        supports=[]
        for uid in effect.get('support_unit_ids') or []:
            u=unit_maps[ref['case']][uid]
            supports.append({'unit_id':uid,'statement':str(u.get('statement') or ''),'epistemic_status':str(u.get('epistemic_status') or ''),'support_excerpts':[str(s.get('support_excerpt') or '')[:900] for s in (u.get('supports') or [])]})
        out.append({'item_id':f"{ref['case']}::{ref['sample_id']}::{ref['effect_index']}",'operation':effect['operation'],'target_code':effect.get('target'),'target_proposition':code_to_prop[effect.get('target')],'support_units':supports,'relation_reason':effect.get('reason','')})
    return out

def validate(parsed,expected):
    ids=[x.item_id for x in parsed.classifications]
    if len(ids)!=len(expected):return False,'COUNT_MISMATCH'
    if len(set(ids))!=len(ids):return False,'DUPLICATE_ID'
    if set(ids)!=set(expected):return False,'ID_SET_MISMATCH'
    return True,None

def summarize(rows,reference):
    ref={f"{x['case']}::{x['sample_id']}::{x['effect_index']}":x for x in reference['items']}; ok=[r for r in rows if r['status']=='OK']; details={}; exact=0; stable=0; critical=[]
    for iid,g in ref.items():
        c=Counter(r['by_id'][iid]['fit'] for r in ok); modal,count=c.most_common(1)[0]; rate=count/len(ok); exact+=modal==g['fit']; stable+=rate>=5/6
        if g['fit']=='DIRECT' and modal in {'INSUFFICIENT','CONTRADICTS_OPERATION'}:critical.append({'item_id':iid,'kind':'DIRECT_LOST','reference':g['fit'],'modal':modal})
        if g['fit']=='CONTRADICTS_OPERATION' and modal=='DIRECT':critical.append({'item_id':iid,'kind':'CONTRADICTION_PROMOTED','reference':g['fit'],'modal':modal})
        details[iid]={'reference':g['fit'],'modal':modal,'counts':dict(c),'modal_rate':rate,'matches_reference':modal==g['fit']}
    n=len(ref); return {'n_ok':len(ok),'n_error':len(rows)-len(ok),'modal_exact':exact/n,'stable_5_of_6_fraction':stable/n,'critical_confusions':critical,'details':details}

def main():
    ref=json.loads(REFERENCE.read_text()); items=materialize(ref); expected=[x['item_id'] for x in items]; rows=[]
    for rep in range(1,REPEATS+1):
        provider=ModelBackedCognitiveProvider(chat_fn=forced_chat)
        try:
            parsed=provider._complete(SYSTEM_PROMPT,build_user_prompt(items),DirectnessResponse,stage='impact'); good,why=validate(parsed,expected)
            if not good: raise RuntimeError(why)
            by_id={x.item_id:x.model_dump() for x in parsed.classifications}; row={'repeat':rep,'status':'OK','by_id':by_id,'meta':dict(provider.last_meta)}
        except Exception as exc: row={'repeat':rep,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
        rows.append(row); print(json.dumps({'repeat':rep,'status':row['status'],'error':row.get('error')},ensure_ascii=False),flush=True)
    summary=summarize(rows,ref)
    out={'run_version':RUN_VERSION,'status':'RELATION_SUPPORT_DIRECTNESS_MEASUREMENT','measurement_sha':git_head(),'reference_path':str(REFERENCE.relative_to(ROOT)),'reference_sha256':sha256(REFERENCE),'source_path':str(SOURCE.relative_to(ROOT)),'source_sha256':sha256(SOURCE),'classifier_version':VERSION,'system_prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),'n_items':len(items),'repeats':REPEATS,'rows':rows,'summary':summary,'guardrails':['No source prestige/provenance is shown to directness classifier.','No numeric epistemic/confidence/importance score or Attention decision.','Production defaults unchanged; Phase 9A paused.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT)));print('RESULT_SHA256='+sha256(p));print(json.dumps({k:v for k,v in summary.items() if k!='details'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
