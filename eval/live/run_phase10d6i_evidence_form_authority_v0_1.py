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
from eval.live.phase10d6i_evidence_form_classifier_v0_1 import (
    VERSION, SYSTEM_PROMPT, EvidenceClassificationResponse, build_user_prompt,
)
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases

RUN_VERSION='phase10d6i-evidence-form-authority-v0.1'
REFERENCE=ROOT/'eval/live/phase10d6i_evidence_form_reference_v0_1.json'
OUT_DIR=ROOT/'eval/live/results/phase10d6i_evidence_form_authority_v0_1'
REPEATS=6


def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def forced_chat(messages,**kwargs):
    return chat_json(messages,timeout=float(kwargs.get('timeout') or 60.0),thinking=kwargs.get('thinking'),reasoning_effort=kwargs.get('reasoning_effort'),temperature=.1)


def materialize_items(reference: dict) -> list[dict]:
    worlds=selected_cases()
    unit_maps={label:{str(u.get('unit_id')):u for u in worlds[label]['case']['frozen_units']} for label in worlds}
    items=[]
    for ref in reference['items']:
        case=ref['case']; uid=ref['unit_id']; unit=unit_maps[case][uid]
        supports=[]
        for s in unit.get('supports') or []:
            supports.append({
                'source_id':str(s.get('source_id') or ''),
                'support_pointer':str(s.get('support_pointer') or ''),
                'support_excerpt':str(s.get('support_excerpt') or '')[:900],
            })
        items.append({
            'item_id':f'{case}::{uid}',
            'source_context':reference['source_context'][case],
            'unit':{
                'unit_id':uid,
                'statement':str(unit.get('statement') or ''),
                'epistemic_status':str(unit.get('epistemic_status') or ''),
                'supports':supports,
            },
        })
    return items


def validate_run(parsed: EvidenceClassificationResponse, expected_ids: list[str]):
    ids=[x.item_id for x in parsed.classifications]
    if len(ids)!=len(expected_ids): return False,'COUNT_MISMATCH'
    if len(set(ids))!=len(ids): return False,'DUPLICATE_ITEM_ID'
    if set(ids)!=set(expected_ids): return False,'IDENTIFIER_SET_MISMATCH'
    return True,None


def summarize(rows,reference):
    ref={f"{x['case']}::{x['unit_id']}":x for x in reference['items']}
    ok=[r for r in rows if r['status']=='OK']
    axes={axis:{} for axis in ('provenance_role','evidence_form')}
    for item_id in ref:
        for axis in axes:
            vals=[r['by_id'][item_id][axis] for r in ok]
            c=Counter(vals); mode,count=c.most_common(1)[0] if c else (None,0)
            axes[axis][item_id]={
                'reference':ref[item_id][axis], 'counts':dict(c), 'modal':mode,
                'modal_rate':count/len(ok) if ok else 0.0,
                'modal_matches_reference':mode==ref[item_id][axis],
            }
    metrics={}
    for axis in axes:
        vals=list(axes[axis].values())
        metrics[axis]={
            'modal_exact_agreement':sum(v['modal_matches_reference'] for v in vals)/len(vals),
            'stable_5_of_6_fraction':sum(v['modal_rate']>=5/6 for v in vals)/len(vals),
        }
    critical=[]
    for item_id,v in axes['evidence_form'].items():
        pair=(v['reference'],v['modal'])
        if pair in {('MEASUREMENT_RESULT','EVALUATIVE_ASSERTION'),('EVALUATIVE_ASSERTION','MEASUREMENT_RESULT')}:
            critical.append({'item_id':item_id,'axis':'evidence_form','reference':pair[0],'modal':pair[1]})
    for item_id,v in axes['provenance_role'].items():
        pair=(v['reference'],v['modal'])
        if pair in {('PRIMARY_SOURCE','SECONDARY_SOURCE'),('SECONDARY_SOURCE','PRIMARY_SOURCE')}:
            critical.append({'item_id':item_id,'axis':'provenance_role','reference':pair[0],'modal':pair[1]})
    return {'n_ok':len(ok),'n_error':len(rows)-len(ok),'axes':axes,'metrics':metrics,'critical_confusions':critical}


def main():
    reference=json.loads(REFERENCE.read_text()); items=materialize_items(reference); expected=[x['item_id'] for x in items]
    rows=[]
    for repeat in range(1,REPEATS+1):
        provider=ModelBackedCognitiveProvider(chat_fn=forced_chat)
        try:
            parsed=provider._complete(SYSTEM_PROMPT,build_user_prompt(items),EvidenceClassificationResponse,stage='impact')
            valid,reason=validate_run(parsed,expected)
            if not valid: raise RuntimeError(reason)
            by_id={x.item_id:x.model_dump() for x in parsed.classifications}
            row={'repeat':repeat,'status':'OK','by_id':by_id,'meta':dict(provider.last_meta)}
        except Exception as exc:
            row={'repeat':repeat,'status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
        rows.append(row)
        print(json.dumps({'repeat':repeat,'status':row['status'],'error':row.get('error')},ensure_ascii=False),flush=True)
    summary=summarize(rows,reference)
    out={
      'run_version':RUN_VERSION,'status':'EVIDENCE_FORM_INSTRUMENT_MEASUREMENT','measurement_sha':git_head(),
      'reference_path':str(REFERENCE.relative_to(ROOT)),'reference_sha256':sha256(REFERENCE),
      'classifier_version':VERSION,'system_prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
      'n_reference_items':len(items),'repeats':REPEATS,'rows':rows,'summary':summary,
      'guardrails':['No numeric confidence/strength/importance is emitted.','No Attention, relation direction, truth judgment or production policy is evaluated.','Production defaults unchanged; Phase 9A paused.'],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); print(json.dumps(summary['metrics'],indent=2)); print('CRITICAL='+json.dumps(summary['critical_confusions'],ensure_ascii=False))

if __name__=='__main__': main()
