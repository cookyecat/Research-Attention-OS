from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import get_decision_strategy
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.phase6b_cognitive_semantics_v0_1 import build_phase6b_mvp_kernel_nodes
from eval.live.phase10d6e_authority_enrichment_v0_1 import VERSION as AUTHORITY_VERSION, enrich_effect
from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map
from eval.live.run_phase10d3_real_web_static_cognitive_map_v0_1 import branch_relation_key
from eval.live.run_phase10d4_real_web_basin_persistence_v0_1 import reconstruct_matches, selected_cases
from eval.live.run_phase10d5_production_semantic_parity_audit_v0_1 import (
    assert_historical_replay, calibrations, reconstruct_effects, freeze,
)
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features

RUN_VERSION='phase10d6e-authority-band-calibration-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase10d6e_authority_band_calibration_v0_1'
SOURCE=ROOT/'eval/live/results/phase10d4_real_web_basin_persistence_v0_1/phase10d4_real_web_basin_persistence_v0.1_20260910T160403Z.json'
SOURCE_SHA='5299cab0607779989b896148765f5c6ef9873b001449b73f51cba6b67e7438a7'
PARITY=ROOT/'eval/live/results/phase10d5_production_semantic_parity_audit_v0_1/phase10d5_production_semantic_parity_audit_v0.1_20260911T021932Z.json'
PARITY_SHA='e2ef93617f48e8d296e63eb6b0075b00986e764f8b46a46023837b2c0e5eb6af'
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
POLICIES=('NATIVE_RAW','PRODUCTION_IMPORTANCE','C1_CONSERVATIVE','C2_AUDITOR_TRUST_UPPER_BOUND')


def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def load_verified(path,sha):
    actual=sha256(path)
    if actual!=sha: raise RuntimeError(f'artifact SHA mismatch {path}: {actual}')
    return json.loads(Path(path).read_text())


def project_effects(sample,effects,*,prod_matches,relation_key,strategy,traces=None):
    assessment=CognitiveImpactAssessment(effects=effects)
    report=analyze_decision_causal_core(
        assessment=assessment,matches=prod_matches,features=features(),
        decision_strategy=strategy,relation_key=relation_key,
    )
    return {
        'sample_id':sample.get('sample_id'),
        'topology':sorted({relation_key(e) for e in effects},key=repr),
        'necessary_core':list(report.necessary_core),
        'sufficient_supports':list(report.sufficient_supports),
        'attention':report.baseline_decision,
        'authority_trace':traces or [],
    }


def project_policy(sample,policy,*,nodes,prod_matches,units,relation_key,strategy):
    if policy=='NATIVE_RAW':
        effects=reconstruct_effects(sample,nodes,production_importance=False); traces=[]
    elif policy=='PRODUCTION_IMPORTANCE':
        effects=reconstruct_effects(sample,nodes,production_importance=True); traces=[]
    else:
        base=reconstruct_effects(sample,nodes,production_importance=False)
        effects=[]; traces=[]
        for e in base:
            enriched,trace=enrich_effect(e,nodes=nodes,matches=prod_matches,units=units,policy=policy)
            effects.append(enriched)
            traces.append({
                'operation':enriched.operation.value,
                'target_kernel_node_id':str(enriched.target_kernel_node_id) if enriched.target_kernel_node_id else None,
                **trace,
            })
    return project_effects(sample,effects,prod_matches=prod_matches,relation_key=relation_key,strategy=strategy,traces=traces)


def assert_parity_reference(label,checkpoint,projected,parity_case):
    ref_key='production_t1_samples' if checkpoint=='t1' else 'production_t2_samples'
    refs={str(r.get('sample_id')):r for r in parity_case[ref_key]}
    ref=refs[str(projected.get('sample_id'))]
    for field in ('attention','necessary_core','sufficient_supports'):
        if freeze(projected.get(field)) != freeze(ref.get(field)):
            raise RuntimeError(f'10D.5 parity replay mismatch {label}/{checkpoint}/{projected.get("sample_id")} {field}')


def summarize_policy(samples_by_checkpoint):
    t1=samples_by_checkpoint['t1']; t2=samples_by_checkpoint['t2']
    m1=summarize_static_cognitive_map(t1); m2=summarize_static_cognitive_map(t2)
    nulls=calibrations(t1,t2)
    return {
        't1_attention':dict(Counter(x['attention'] for x in t1)),
        't2_attention':dict(Counter(x['attention'] for x in t2)),
        't1_map':m1,'t2_map':m2,'permutation_null':nulls,
        'same_basin_compatible':{k:not v['drift_supported_v0_1'] for k,v in nulls.items()},
        't1_samples':t1,'t2_samples':t2,
    }


def main():
    source=load_verified(SOURCE,SOURCE_SHA); parity=load_verified(PARITY,PARITY_SHA)
    selected=selected_cases(); nodes=build_phase6b_mvp_kernel_nodes(); strategy=get_decision_strategy(STRATEGY_ID)
    results={}; totals={p:Counter() for p in POLICIES}; replayed=0
    for label,row in selected.items():
        source_case=row['case']; stored=source['cases'][label]
        native_matches=reconstruct_matches(source_case); prod_matches=_matches(native_matches,nodes)
        relation_key=branch_relation_key(nodes,source_case['frozen_units'])
        policy_samples={p:{'t1':[],'t2':[]} for p in POLICIES}
        for checkpoint,key in (('t1','t1_samples'),('t2','t2_samples')):
            for sample in stored[key]:
                native=project_policy(sample,'NATIVE_RAW',nodes=nodes,prod_matches=prod_matches,units=source_case['frozen_units'],relation_key=relation_key,strategy=strategy)
                assert_historical_replay(sample,native,label)
                policy_samples['NATIVE_RAW'][checkpoint].append(native)
                prod=project_policy(sample,'PRODUCTION_IMPORTANCE',nodes=nodes,prod_matches=prod_matches,units=source_case['frozen_units'],relation_key=relation_key,strategy=strategy)
                assert_parity_reference(label,checkpoint,prod,parity['results'][label])
                policy_samples['PRODUCTION_IMPORTANCE'][checkpoint].append(prod)
                for policy in ('C1_CONSERVATIVE','C2_AUDITOR_TRUST_UPPER_BOUND'):
                    candidate=project_policy(sample,policy,nodes=nodes,prod_matches=prod_matches,units=source_case['frozen_units'],relation_key=relation_key,strategy=strategy)
                    policy_samples[policy][checkpoint].append(candidate)
                    if candidate['attention']!=native['attention']: totals[policy]['changed_vs_native']+=1
                    if candidate['attention']=='DROP' and native['attention']!='DROP': totals[policy]['new_drop_vs_native']+=1
                    if candidate['attention']=='ENGAGE' and native['attention']!='ENGAGE': totals[policy]['new_engage_vs_native']+=1
                replayed+=1
        results[label]={p:summarize_policy(policy_samples[p]) for p in POLICIES}
        print(json.dumps({'label':label,'attention':{p:{'t1':results[label][p]['t1_attention'],'t2':results[label][p]['t2_attention']} for p in POLICIES}},ensure_ascii=False),flush=True)
    if replayed!=168: raise RuntimeError(f'expected 168 replayed semantic realizations, got {replayed}')
    out={
        'run_version':RUN_VERSION,'status':'OFFLINE_AUTHORITY_BAND_CALIBRATION','measurement_sha':git_head(),
        'authority_enrichment_version':AUTHORITY_VERSION,'source_phase10d4':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,
        'parity_reference_phase10d5':str(PARITY.relative_to(ROOT)),'parity_sha256':PARITY_SHA,'n_replayed_samples':replayed,
        'policies':list(POLICIES),'decision_strategy':strategy.execution_snapshot(),'relative_sensitivity_totals':{p:dict(v) for p,v in totals.items()},
        'results':results,
        'guardrails':[
            'No LLM, acquisition, Sensor, Auditor, Locate, Relation Mapping, or grounding call is made.',
            'NATIVE_RAW must reproduce all 168 historical Phase10D.4 outcomes exactly.',
            'PRODUCTION_IMPORTANCE must reproduce all 168 Phase10D.5 production-importance outcomes exactly.',
            'C1/C2 modify authority bands only; operation, target, reason, topology, Kernel, Locate and Pareto aggregation are frozen.',
            '0/1 floats are compatibility encodings of ordinal authority bands, not cardinal estimates.',
            'C2 is sensitivity-only and is not a promotion candidate.',
            'Relative new DROP/ENGAGE counts are diagnostics against the historical native arm, not human-gold error labels.',
            'Production default remains unchanged.',
        ],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('SENSITIVITY='+json.dumps(out['relative_sensitivity_totals'],ensure_ascii=False))
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); return 0

if __name__=='__main__': raise SystemExit(main())
