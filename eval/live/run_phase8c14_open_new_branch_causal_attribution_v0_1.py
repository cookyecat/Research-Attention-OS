from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from app.services.cognitive_impact import CognitiveImpactAssessment
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.decision_causal_core_v0_1 import analyze_decision_causal_core
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import _code_maps, _nodes
from eval.live.run_phase8c12_locate_relation_longitudinal_v0_1 import reconstruct_historical_modal_matches
from eval.live.run_phase8c13_decision_causal_core_v0_1 import features, reconstruct_effects
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _matches
from eval.live.topology_stability_metrics_v0_1 import summarize_topology_stability

RUN_VERSION='phase8c14-open-new-branch-causal-attribution-v0.1'
OUT_DIR=ROOT/'eval/live/results/phase8c14_open_new_branch_causal_attribution_v0_1'
SOURCE12=ROOT/'eval/live/results/phase8c12_locate_relation_longitudinal_v0_1/phase8c12_locate_relation_longitudinal_v0.1_20260910T072032Z.json'
SOURCE12_SHA='a67d7e40e403c7ad9bd7dd6a82312fd5c720ada0f2bf683b506475eb3d92e8be'
SOURCE8=ROOT/'eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json'
SOURCE8_SHA='f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216'
STRATEGY_ID='pareto-multidelta-magnitude-free-anchored-open-new'
CASES=('RS05','RS15','RS11','RS12')


def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verified(p,h):
    a=sha256(p)
    if a!=h: raise RuntimeError(f'SHA mismatch {p}: {a}')
    return json.loads(Path(p).read_text())
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def explicit_unit_signature(case_id: str, reason: str) -> tuple[str,...]:
    prefix=case_id+'-'
    tokens=[]
    # Explicit full IDs first.
    for m in re.findall(r'RS\d+-(?:NEU\d+|N\d+|U\d+)', reason or '', flags=re.I):
        tokens.append(m.upper())
    # Then shorthand local IDs not already part of a full ID.
    stripped=re.sub(r'RS\d+-(?:NEU\d+|N\d+|U\d+)', ' ', reason or '', flags=re.I)
    for m in re.findall(r'\b(?:NEU\d+|N\d+|U\d+)\b', stripped, flags=re.I):
        tokens.append((prefix+m).upper())
    return tuple(sorted(set(tokens)))


def branch_relation_key(case_id, nodes):
    _, code_by_str=_code_maps(nodes)
    def key(effect):
        op=effect.operation.value if hasattr(effect.operation,'value') else str(effect.operation)
        if op=='OPEN_NEW':
            sig=explicit_unit_signature(case_id, effect.reason)
            return ('OPEN_NEW', sig if sig else ('UNRESOLVED',))
        target=code_by_str.get(str(effect.target_kernel_node_id)) if effect.target_kernel_node_id else None
        return (op,target)
    return key


def main():
    d12=verified(SOURCE12,SOURCE12_SHA); d8=verified(SOURCE8,SOURCE8_SHA)
    by12={r['case']:r for r in d12['cases']}; by8={r['case']:r for r in d8['cases']}
    strategy=get_decision_strategy(STRATEGY_ID)
    results={}
    for case in CASES:
        nodes=_nodes(case); native=reconstruct_historical_modal_matches(by8[case],nodes); prod=_matches(native,nodes)
        key=branch_relation_key(case,nodes)
        occurrence=Counter(); necessary=Counter(); sufficient=Counter(); classes=defaultdict(Counter)
        core_sets=[]; support_sets=[]; rows=[]
        source_runs=[r for r in by12[case]['gate12b_relation']['current']['runs'] if r['status']=='OK']
        for run in source_runs:
            effects=reconstruct_effects(run['effects'],nodes)
            ass=CognitiveImpactAssessment(effects=effects)
            base=route(features(),RuntimeView(),assessment=ass,matches=prod,decision_strategy=strategy).disposition.value
            if base!=run['attention']: raise RuntimeError(f'baseline mismatch {case} r{run["repeat"]}: {base}!={run["attention"]}')
            report=analyze_decision_causal_core(assessment=ass,matches=prod,features=features(),decision_strategy=strategy,relation_key=key)
            present={key(e) for e in effects}
            for rel in present: occurrence[rel]+=1
            for rel in report.necessary_core: necessary[rel]+=1
            for rel in report.sufficient_supports: sufficient[rel]+=1
            for rr in report.relations: classes[rr.relation][rr.classification]+=1
            core_sets.append(report.necessary_core); support_sets.append(report.sufficient_supports)
            rows.append({'repeat':run['repeat'],'attention':base,'branch_topology':sorted(present,key=repr),'causal_profile':report.as_dict()})
            print(json.dumps({'case':case,'repeat':run['repeat'],'attention':base,'necessary':report.necessary_core,'sufficient':report.sufficient_supports},ensure_ascii=False),flush=True)
        n=len(rows); stats={}
        for rel in sorted(occurrence,key=repr):
            p=occurrence[rel]
            stats[str(rel)]={
                'occurrence_frequency':p/n,
                'necessary_frequency':necessary[rel]/n,
                'sufficient_frequency':sufficient[rel]/n,
                'necessary_given_present':necessary[rel]/p,
                'sufficient_given_present':sufficient[rel]/p,
                'classification_counts':dict(classes[rel]),
            }
        results[case]={
            'n_samples':n,'branch_relation_stats':stats,
            'necessary_core_stability':summarize_topology_stability(core_sets).as_dict(),
            'sufficient_support_stability':summarize_topology_stability(support_sets).as_dict(),
            'samples':rows,
        }
    out={'run_version':RUN_VERSION,'status':'DETERMINISTIC_BRANCH_COUNTERFACTUAL_REPLAY','measurement_sha':git_head(),
         'source_phase8c12':str(SOURCE12.relative_to(ROOT)),'source_phase8c12_sha256':SOURCE12_SHA,
         'branch_identity':'explicit-source-unit-support-signature-v0.1','decision_strategy':strategy.execution_snapshot(),
         'results':results,
         'guardrails':['No LLM calls.','OPEN_NEW branch signature is measurement-only and source-reference based.','Same source-unit signature does not prove semantic identity.','UNRESOLVED is preserved rather than inferred from free-text similarity.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    for case,r in results.items():
        print('\n###',case)
        for k,v in r['branch_relation_stats'].items():
            if k.startswith("('OPEN_NEW'"): print(k,v)
    return 0
if __name__=='__main__': raise SystemExit(main())
