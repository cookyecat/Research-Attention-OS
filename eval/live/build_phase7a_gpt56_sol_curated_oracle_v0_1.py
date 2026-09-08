from __future__ import annotations
import json, glob, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / 'eval/live/results/phase7a_gpt56_sol_curated_oracle_v0_1'
REF_GLOB = str(ROOT / 'eval/live/results/phase7a_gpt56_sol_reference_v0_1/*.json')

def head():
    return subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()

def latest_reference():
    paths = sorted(glob.glob(REF_GLOB))
    if not paths:
        raise SystemExit('missing GPT-5.6 one-pass reference artifact')
    return Path(paths[-1])
REVISED = {
    'G56-RS05-U03': (
        'For the 64x64 matmul+add workload, Self CPU time is 2.314 ms and GPU kernel time is under 1% of CPU time; '
        'the source explicitly says most runtime is spent on kernel preparation, GPU launch, data movement, and result collection rather than useful computation, making the workload overhead-bound.'
    ),
    'G56-RS05-U04': (
        'Increasing the workload to 4096x4096 shifts execution from overhead-bound to compute-bound: Self CPU time is 4.908 ms and the source reports that most CUDA time is now spent in the GPU kernel rather than CPU-side launch work.'
    ),
    'G56-RS05-U05': (
        'Warmup executes the target before active sampling so one-time GPU initialization work is kept out of profiling statistics; after warmup, ProfileStep#2 no longer shows the cold-start overhead.'
    ),
    'G56-RS05-U06': (
        'The profiler trace shows an Activity Buffer Request causing a gap between matmul and add CUDA kernels; with active sampling increased to 20 iterations, that buffer-allocation gap appears only once.'
    ),
    'G56-RS05-U10': (
        'Even with the same hardware, code, and inputs, GPU kernel duration is not fixed; a 20-iteration matmul trace shows run-to-run timing variation.'
    ),
}
def main():
    src_path = latest_reference()
    payload = json.loads(src_path.read_text(encoding='utf-8'))
    revised = []
    for source in payload['sources']:
        if source['source']['source_id'] != 'RS05':
            continue
        for unit in source['batch']['non_event_units']:
            uid = unit['unit_id']
            if uid in REVISED:
                unit['statement'] = REVISED[uid]
                revised.append(uid)
        source['statement_chars'] = sum(len(u['statement']) for u in source['batch']['non_event_units'])
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    payload['name'] = 'raos-phase7a-gpt56-sol-curated-oracle-v0.1'
    payload['status'] = 'DEVELOPMENT_ONLY_AUDIT_GUIDED_CURATED_ORACLE_NOT_FRESH_VALIDATION'
    payload['measurement_timestamp'] = ts
    payload['measurement_git_head'] = head()
    payload['parent_one_pass_reference'] = str(src_path)
    payload['revised_unit_ids'] = revised
    payload['methodology_note'] = (
        'Audit-guided curated oracle derived from the preserved GPT-5.6 Sol one-pass reference. '
        'Only unsupported wording identified by the same Auditor is narrowed; no outside knowledge or new source evidence is added. '
        'This estimates a strong-model-plus-review upper bound and is NOT a one-pass model-capability score.'
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f'phase7a_gpt56_sol_curated_oracle_v0_1_{ts}.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out)
    print(json.dumps({'head': payload['measurement_git_head'], 'revised': revised}, indent=2))

if __name__ == '__main__':
    main()
