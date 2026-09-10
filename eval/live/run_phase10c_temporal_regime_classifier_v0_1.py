from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from eval.live.cognitive_temporal_regime_v0_1 import classify_case, execution_snapshot
RUN_VERSION='phase10c-temporal-regime-classifier-v0.1'
SOURCE=ROOT/'eval/live/results/phase10b2_persistence_comparison_v0_1/phase10b2_persistence_comparison_v0.1_20260910T084056Z.json'
SOURCE_SHA='8ecc8cb58f252a9175818bc3c5702870035361d35c4ed1f43eabdbf05946ab40'
OUT_DIR=ROOT/'eval/live/results/phase10c_temporal_regime_classifier_v0_1'

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git_head(): return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def main():
    if sha256(SOURCE)!=SOURCE_SHA: raise RuntimeError('source SHA mismatch')
    d=json.loads(SOURCE.read_text())
    results={}
    for case,row in d['cases'].items():
        results[case]=classify_case(row['persistence'])
        print(json.dumps({'case':case,'regimes':results[case]},ensure_ascii=False),flush=True)
    out={'run_version':RUN_VERSION,'status':'DETERMINISTIC_REGIME_CLASSIFICATION_COMPLETE','measurement_sha':git_head(),'source':str(SOURCE.relative_to(ROOT)),'source_sha256':SOURCE_SHA,'classifier':execution_snapshot(),'results':results,'guardrails':['No LLM calls.','No new distance thresholds.','Each metric classified independently.','No stochastic-process fit.','Production default unchanged.']}
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    p=OUT_DIR/f'{RUN_VERSION.replace("-","_")}_{stamp}.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print('RESULT_PATH='+str(p.relative_to(ROOT))); print('RESULT_SHA256='+sha256(p)); return 0
if __name__=='__main__': raise SystemExit(main())
