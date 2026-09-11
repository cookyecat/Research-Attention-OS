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
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6f_effect_support_binding_v0_1 import (
    CONTRACT_VERSION, SYSTEM_PROMPT, SupportBoundRelationResponse, effect_key, user_prompt, validate_effect,
)
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import selected_cases
from eval.live.run_phase10d6b_prompt_reconciliation_shadow_v0_1 import reconstruct_prod_matches

RUN_VERSION='phase10d6f-effect-support-binding-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10d6f_effect_support_binding_v0_1'
CASES=('A','D','X','N4'); REPEATS=6


def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def sha256(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def forced_chat(messages,**kwargs):
    return chat_json(messages,timeout=float(kwargs.get('timeout') or 60.0),thinking=kwargs.get('thinking'),reasoning_effort=kwargs.get('reasoning_effort'),temperature=.1)


def serialize(effect,nodes):
    by_id={node.id:str((node.payload or {}).get('phase6b_fixture_code') or node.title) for node in nodes}
    return {
        'operation':effect.operation,
        'target_kernel_node_id':str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        'target':by_id.get(effect.target_kernel_node_id) if effect.target_kernel_node_id else None,
        'support_unit_ids':list(effect.support_unit_ids),
        'jurisdiction_anchor_ids':[str(x) for x in effect.jurisdiction_anchor_ids],
        'jurisdiction_anchors':[by_id.get(x,str(x)) for x in effect.jurisdiction_anchor_ids],
        'reason':effect.reason,
    }


def run_one(label,ordinal,case,nodes,matches):
    provider=ModelBackedCognitiveProvider(chat_fn=forced_chat)
    parsed:SupportBoundRelationResponse=provider._complete(
        SYSTEM_PROMPT,user_prompt(case['frozen_units'],matches,nodes),SupportBoundRelationResponse,stage='impact'
    )
    raw=[]; valid=[]; invalid=[]
    for effect in parsed.effects:
        row=serialize(effect,nodes); raw.append(row)
        ok,reason=validate_effect(effect,units=case['frozen_units'],matches=matches,nodes=nodes)
        if ok:
            valid.append({**row,'relation_key':effect_key(effect,nodes=nodes)})
        else:
            invalid.append({**row,'invalid_reason':reason})
    return {
        'sample_id':f'{label}-{ordinal}','status':'OK','raw_effects':raw,'valid_effects':valid,'invalid_effects':invalid,
        'raw_effect_count':len(raw),'valid_effect_count':len(valid),'invalid_effect_count':len(invalid),
        'topology':sorted({tuple(v['relation_key']) for v in valid},key=repr),
        'bound_support_unit_ids':sorted({uid for v in valid for uid in v['support_unit_ids']}),
        'meta':dict(provider.last_meta),
    }


def freeze(value):
    if isinstance(value,list): return tuple(freeze(v) for v in value)
    if isinstance(value,tuple): return tuple(freeze(v) for v in value)
    return value


def summarize(rows,unit_count):
    ok=[r for r in rows if r['status']=='OK']
    raw=sum(r['raw_effect_count'] for r in ok); valid=sum(r['valid_effect_count'] for r in ok)
    invalid_reasons=Counter(x['invalid_reason'] for r in ok for x in r['invalid_effects'])
    topologies=Counter(repr(freeze(r['topology'])) for r in ok)
    relation_counts=Counter(repr(freeze(v['relation_key'])) for r in ok for v in r['valid_effects'])
    support_counts=Counter(uid for r in ok for uid in set(r['bound_support_unit_ids']))
    support_sizes=[len(v['support_unit_ids']) for r in ok for v in r['valid_effects']]
    return {
        'n_ok':len(ok),'n_error':len(rows)-len(ok),'raw_effects':raw,'valid_effects':valid,
        'valid_effect_rate':valid/raw if raw else 1.0,'invalid_reason_counts':dict(invalid_reasons),
        'topology_n_unique':len(topologies),'topology_mode_rate':max(topologies.values())/len(ok) if ok and topologies else 1.0,
        'relation_occurrence_counts':dict(relation_counts),
        'mean_support_units_per_effect':sum(support_sizes)/len(support_sizes) if support_sizes else 0.0,
        'support_unit_sample_frequency':{uid:count/len(ok) for uid,count in sorted(support_counts.items())} if ok else {},
        'mean_bound_world_fraction':sum(len(r['bound_support_unit_ids'])/unit_count for r in ok)/len(ok) if ok and unit_count else 0.0,
    }


def main():
    selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); results={}
    for label in CASES:
        case=selected[label]['case']; matches=reconstruct_prod_matches(case,nodes); rows=[]
        for ordinal in range(1,REPEATS+1):
            try: row=run_one(label,ordinal,case,nodes,matches)
            except Exception as exc:
                row={'sample_id':f'{label}-{ordinal}','status':'ERROR','error_type':type(exc).__name__,'error':str(exc)[:3000]}
            rows.append(row)
            print(json.dumps({'label':label,'repeat':ordinal,'status':row['status'],'raw':row.get('raw_effect_count'),'valid':row.get('valid_effect_count'),'invalid':row.get('invalid_effect_count'),'topology':row.get('topology'),'error':row.get('error')},ensure_ascii=False),flush=True)
        summary=summarize(rows,len(case['frozen_units']))
        results[label]={'samples':rows,'summary':summary,'frozen_units_replay_sha256':case['frozen_units_replay_sha256'],'frozen_locate':case['locate']['modal']}
        print(json.dumps({'label':label,'summary':{k:v for k,v in summary.items() if k not in {'support_unit_sample_frequency','relation_occurrence_counts'}}},ensure_ascii=False),flush=True)
    out={
        'run_version':RUN_VERSION,'status':'EFFECT_SUPPORT_BINDING_MEASUREMENT','measurement_sha':git_head(),
        'relation_contract_version':CONTRACT_VERSION,'system_prompt_sha256':hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        'cases':list(CASES),'repeats_per_case':REPEATS,'results':results,
        'guardrails':[
            'Exact frozen Auditor worlds, Kernel fixtures and modal Locate are reused; no acquisition/Sensor/Auditor/Locate call occurs.',
            'Relation output contains no change_magnitude, target_importance or epistemic_strength.',
            'Unknown support, target or jurisdiction identifiers fail closed at effect level and are never rewritten.',
            'OPEN_NEW requires at least one legal frozen jurisdiction anchor.',
            'No Attention policy is evaluated or promoted in this phase.',
            'Production defaults remain unchanged.',
        ],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); return 0

if __name__=='__main__': raise SystemExit(main())
