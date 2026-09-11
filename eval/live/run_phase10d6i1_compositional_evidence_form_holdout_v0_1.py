from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()
from app.cognitive.client import chat_json
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from eval.live.phase10d6i1_compositional_evidence_classifier_v0_1 import VERSION,SYSTEM_PROMPT,CompositionalEvidenceResponse,build_user_prompt

RUN_VERSION='phase10d6i1-compositional-evidence-form-holdout-v0.1'
REFERENCE=ROOT/'eval/live/phase10d6i1_compositional_evidence_form_holdout_v0_1.json'
SOURCE=ROOT/'eval/live/results/phase10d3_real_web_static_cognitive_map_v0_1/phase10d3_real_web_static_cognitive_map_v0.1_20260910T151143Z.json'
SOURCE_SHA='a40f2a6e4690a34552232c7e63c473e87ad7d5b846304a5a89108544b8b63f89'
OUT_DIR=ROOT/'eval/live/results/phase10d6i1_compositional_evidence_form_holdout_v0_1'
REPEATS=6

def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def forced_chat(messages,**kwargs): return chat_json(messages,timeout=float(kwargs.get('timeout') or 60.0),thinking=kwargs.get('thinking'),reasoning_effort=kwargs.get('reasoning_effort'),temperature=.1)

def materialize(reference):
    if sha256(SOURCE)!=SOURCE_SHA: raise RuntimeError('SOURCE_SHA_MISMATCH')
    src=json.loads(SOURCE.read_text()); unit_maps={label:{str(u.get('unit_id')):u for u in src['cases'][label]['frozen_units']} for label in ('B3','B4','F3','F4')}
    out=[]
    for ref in reference['items']:
        c=ref['case']; uid=ref['unit_id']; u=unit_maps[c][uid]
        out.append({'item_id':f'{c}::{uid}','source_context':reference['source_context'][c],'unit':{'unit_id':uid,'statement':str(u.get('statement') or ''),'epistemic_status':str(u.get('epistemic_status') or ''),'supports':[{'source_id':str(s.get('source_id') or ''),'support_pointer':str(s.get('support_pointer') or ''),'support_excerpt':str(s.get('support_excerpt') or '')[:900]} for s in (u.get('supports') or [])]}})
    return out

def validate(parsed,expected):
    ids=[x.item_id for x in parsed.classifications]
    if len(ids)!=len(expected): return False,'COUNT_MISMATCH'
    if len(set(ids))!=len(ids): return False,'DUPLICATE_ID'
    if set(ids)!=set(expected): return False,'ID_SET_MISMATCH'
    return True,None

def jaccard(a,b):
    a=set(a); b=set(b); return len(a&b)/len(a|b) if a|b else 1.0

def summarize(rows,reference):
    ref={f"{x['case']}::{x['unit_id']}":x for x in reference['items']}; ok=[r for r in rows if r['status']=='OK']; details={}; prov_exact=0; form_exact=0; jacc=[]; stable=0; critical=[]
    for item_id,gold in ref.items():
        prov=Counter(r['by_id'][item_id]['provenance_role'] for r in ok); pm,pc=prov.most_common(1)[0]
        forms=Counter(tuple(sorted(r['by_id'][item_id]['evidence_forms'])) for r in ok); fm,fc=forms.most_common(1)[0]
        gforms=tuple(sorted(gold['evidence_forms'])); jac=jaccard(fm,gforms)
        prov_exact += pm==gold['provenance_role']; form_exact += fm==gforms; jacc.append(jac); stable += fc/len(ok)>=5/6
        if (gold['provenance_role'],pm) in {('PRIMARY_SOURCE','SECONDARY_SOURCE'),('SECONDARY_SOURCE','PRIMARY_SOURCE')}:
            critical.append({'item_id':item_id,'kind':'PROVENANCE_FLIP','gold':gold['provenance_role'],'modal':pm})
        if gforms==('MEASUREMENT_RESULT',) and 'MEASUREMENT_RESULT' not in fm and set(fm)<={'EVALUATIVE_ASSERTION'}:
            critical.append({'item_id':item_id,'kind':'MEASUREMENT_TO_ASSERTION','gold':gforms,'modal':fm})
        details[item_id]={'reference_provenance':gold['provenance_role'],'modal_provenance':pm,'provenance_counts':dict(prov),'reference_forms':gforms,'modal_forms':fm,'form_counts':{repr(k):v for k,v in forms.items()},'modal_form_rate':fc/len(ok),'jaccard':jac}
    n=len(ref)
    return {'n_ok':len(ok),'n_error':len(rows)-len(ok),'provenance_modal_exact':prov_exact/n,'evidence_form_modal_exact_set':form_exact/n,'mean_modal_jaccard':sum(jacc)/n,'stable_5_of_6_fraction':stable/n,'critical_confusions':critical,'details':details}

def main():
    ref=json.loads(REFERENCE.read_text()); items=materialize(ref); expected=[x['item_id'] for x in items]; rows=[]
    for rep in range(1,REPEATS+1):
        provider=ModelBackedCognitiveProvider(chat_fn=forced_chat)
        try:
            parsed=provider._complete(SYSTEM_PROMPT,build_user_prompt(items),CompositionalEvidenceResponse,stage='impact'); good,why=validate(parsed,expected)
            if not good: raise RuntimeError(why)
            by_id={x.item_id:{**x.model_dump(),'evidence_forms':sorted(x.evidence_forms)} for x in parsed.classifications}; row={'repeat':rep,'status':'OK','by_id':by_id,'meta':dict(provider.last_meta)}
        except Exception as exc: row={'repeat':rep,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
        rows.append(row); print(json.dumps({'repeat':rep,'status':row['status'],'error':row.get('error')},ensure_ascii=False),flush=True)
    summary=summarize(rows,ref)
    out={'run_version':RUN_VERSION,'status':'COMPOSITIONAL_FRESH_HOLDOUT_MEASUREMENT','measurement_sha':git_head(),'reference_path':str(REFERENCE.relative_to(ROOT)),'reference_sha256':sha256(REFERENCE),'source_path':str(SOURCE.relative_to(ROOT)),'source_sha256':sha256(SOURCE),'classifier_version':VERSION,'system_prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),'n_items':len(items),'repeats':REPEATS,'rows':rows,'summary':summary,'guardrails':['Fresh B3/B4/F3/F4 units only; none were in 10D.6I reference.','No numeric authority fields or Attention decisions.','Production defaults unchanged; Phase 9A paused.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); print(json.dumps({k:v for k,v in summary.items() if k not in {'details'}},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
