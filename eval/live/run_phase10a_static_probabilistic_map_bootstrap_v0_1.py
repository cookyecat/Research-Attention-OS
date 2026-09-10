from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
for p in (ROOT,BACKEND):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from eval.live.probabilistic_cognitive_map_v0_1 import summarize_static_cognitive_map, execution_snapshot

RUN_VERSION='phase10a-static-probabilistic-map-bootstrap-v0.1'
SOURCE=ROOT/'eval/live/results/phase8c14_open_new_branch_causal_attribution_v0_1/phase8c14_open_new_branch_causal_attribution_v0.1_20260910T073517Z.json'
SOURCE_SHA='1327abc2899acf7c93a936dd824c2ea139ae17e6b081fb9057678bdc342583f2'
OUT_DIR=ROOT/'eval/live/results/phase10a_static_probabilistic_map_bootstrap_v0_1'
CASES=('RS05','RS15','RS11','RS12')

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def freeze(x):
    if isinstance(x,list): return tuple(freeze(v) for v in x)
    if isinstance(x,dict): return tuple(sorted((k,freeze(v)) for k,v in x.items()))
    return x

def main():
    if sha256(SOURCE)!=SOURCE_SHA: raise RuntimeError('source SHA mismatch')
    src=json.loads(SOURCE.read_text())
    maps={}
    for case in CASES:
        samples=[]
        for row in src['results'][case]['samples']:
            cp=row['causal_profile']
            samples.append({
                'topology':[freeze(r) for r in row['branch_topology']],
                'necessary_core':[freeze(r) for r in cp['necessary_core']],
                'sufficient_supports':[freeze(r) for r in cp['sufficient_supports']],
                'attention':row['attention'],
            })
        maps[case]=summarize_static_cognitive_map(samples)
    out={
        'run_version':RUN_VERSION,
        'status':'ENGINEERING_BOOTSTRAP_NOT_CANONICAL_N12',
        'measurement_sha':git_head(),
        'source':str(SOURCE.relative_to(ROOT)),
        'source_sha256':SOURCE_SHA,
        'map_chip':execution_snapshot(),
        'maps':maps,
        'guardrails':['No LLM calls.','N=6 bootstrap validates the measurement chip only.','Do not treat Wilson intervals from this bootstrap as final Phase10A evidence.'],
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p))
    for case,m in maps.items():
        print('\n'+case)
        print(' attention',m['attention_distribution']['counts'],'H=',round(m['attention_distribution']['entropy_bits'],4),'conc=',round(m['attention_distribution']['concentration'],4))
        print(' topology H=',round(m['topology_distribution']['entropy_bits'],4),'core H=',round(m['load_bearing_distribution']['entropy_bits'],4))
        rows=sorted(m['relation_map'].items(), key=lambda kv:(-kv[1]['load_bearing']['p'],-kv[1]['topology']['p'],kv[0]))
        for k,v in rows[:8]:
            if v['load_bearing']['p']>0:
                print(' ',k,'P(T)=',round(v['topology']['p'],3),'P(B)=',round(v['load_bearing']['p'],3),'CI=',[round(x,3) for x in v['load_bearing']['wilson95']])
    return 0
if __name__=='__main__': raise SystemExit(main())
