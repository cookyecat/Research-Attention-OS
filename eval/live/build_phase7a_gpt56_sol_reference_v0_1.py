from __future__ import annotations
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'eval/live/results/phase7a_gpt56_sol_reference_v0_1'

def head():
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def load_source(sid):
    e=next(x for x in load_dev_manifest()['sources'] if x['id']==sid)
    return load_manifest_source(e)

def paras(source):
    lines=source.rendered_text.splitlines(); out={}
    for i,line in enumerate(lines):
        if line.startswith('[PARA ') and line.endswith(']'):
            n=int(line[6:10]); out[n]=lines[i+1] if i+1<len(lines) else ''
    return out

def unit(sid, uid, statement, ps, pd):
    return {'unit_id':uid,'statement':statement,'epistemic_status':'SOURCE_CLAIM','confidence':'HIGH','supports':[
        {'source_id':sid,'support_pointer':f'PARA {n:04d}','support_excerpt':pd[n]} for n in ps
    ],'note':''}

def source_row(sid, specs):
    s=load_source(sid); pd=paras(s)
    units=[unit(sid,*spec,pd) for spec in specs]
    return {'source':{'source_id':s.source_id,'path':s.path,'media_type':s.media_type,'git_blob_sha':s.git_blob_sha,
      'file_sha256':s.file_sha256,'text_sha256':s.text_sha256,'char_count':s.char_count,'page_count':s.page_count,
      'published_at':s.published_at,'updated_at':s.updated_at,'captured_at':s.captured_at},
      'scorable':True,'failure_kind':None,'error':None,'repair_used':False,'schema_events':[],
      'model_meta':{'model':'gpt-5.6-sol','mode':'manual-assistant-authored-reference','not_api_latency_benchmark':True},
      'n_event_frames':0,'n_non_event_units':len(units),'n_non_event_supports':sum(len(x['supports']) for x in units),
      'statement_chars':sum(len(x['statement']) for x in units),'support_excerpt_chars':sum(len(y['support_excerpt']) for x in units for y in x['supports']),
      'batch':{'interface_version':'semantic-evidence-batch-v0.2','batch_id':f'{sid}-gpt56-reference-v0.1','source_ids':[sid],
               'event_frames':[],'non_event_units':units,'notes':[]}}

RS15=[
('G56-RS15-U01','Zeno-1 is presented as a 3B physical-intelligence foundation model designed for decentralized multi-robot collaboration, running local closed-loop visual-motor reasoning at 30 Hz; the demo robots run copies of the same policy and decide from their own observations.',[12,17]),
('G56-RS15-U02','The source describes four progressive training stages: large-scale video pretraining for physical priors, single-robot embodied training, closed-loop partner interaction (CPI) for collaboration, and targeted correction of collaboration failures.',[27,31,36,42]),
('G56-RS15-U03','CPI trains independently acting robots as one another\'s partners through a shared physical environment; because partners are themselves imperfect learners, the training exposes the policy to timing/behavior variation, and the source reports emergent adaptation behaviors such as slowing, waiting, yielding, maintaining contact, and resynchronizing.',[38,39,41]),
('G56-RS15-U04','Zeno-1 uses a learnable persistent-interaction memory that maintains a compressed interaction history; the source reports an ablation in which removing it substantially degrades collaboration tasks longer than three minutes.',[57,61]),
('G56-RS15-U05','Predictive introspection evaluates how candidate actions may affect the partner; on the cited held-out evaluation, Zeno-1 chose actions leading to better subsequent partner behavior 87% of the time, versus 61% when partner-behavior prediction was removed.',[66,67,68]),
('G56-RS15-U06','An action-conditioned latent world model predicts how shared physical state will evolve after an action and is used to identify possible contact failures before execution; across 200 real-robot experiments the source reports 0.94 AUC for 0.5-second-ahead contact-failure prediction versus 0.81 from current observation alone.',[70,71,72]),
('G56-RS15-U07','The source argues for decentralization on scalability and robustness grounds: adding robots loads another policy copy with linear computation rather than an exponentially growing joint action space, and a single robot failure does not propagate as a centralized-controller single point of failure would.',[77,78]),
('G56-RS15-U08','Zeno-1 treats the shared physical world itself as a coordination interface: each robot observes the environment and other robots and adjusts its next action, so coordination need not rely completely on explicit communication or unified scheduling.',[81,82]),
('G56-RS15-U09','The article places Zeno-1 in a broader move toward multi-robot collaboration, citing Stanford CHORUS and collaboration capabilities emphasized by Figure Helix 02 and Google DeepMind Gemini Robotics 2.',[83,84]),
]
RS05=[
('G56-RS05-U01','The tutorial uses a matrix multiplication followed by bias addition as a beginner workload for learning torch.profiler, with the scripts run on an NVIDIA A100-SXM4-80GB GPU and profiled through torch.profiler.',[12,16,20,22]),
('G56-RS05-U02','The profiler statistics view is used to find costly or frequently called events, and its Self columns exclude nested child-event time while total columns include the event plus all nested children.',[26,32,33]),
('G56-RS05-U03','For the 64x64 matmul+add workload, Self CPU time is 2.314 ms while Self CUDA time is 23.104 us; GPU kernel time is under 1% of CPU time, so kernel preparation/launch and related CPU-side overhead dominate useful computation, making the workload overhead-bound.',[28,31,35,36]),
('G56-RS05-U04','Increasing the workload to 4096x4096 raises useful GPU computation: Self CPU time is 4.908 ms and CUDA time is of the same millisecond scale, shifting the workload from overhead-bound to compute-bound.',[38,39,40,41]),
('G56-RS05-U05','Warmup is measurement isolation rather than an optimization of recurring work: it executes the target before active sampling so one-time GPU initialization costs fall outside the measured window, and after warmup ProfileStep#2 no longer shows the cold-start overhead.',[54,57]),
('G56-RS05-U06','A one-time Activity Buffer Request can create profiler-induced gaps between GPU kernels; increasing active sampling to 20 iterations shows the gap occurs only once, supporting profiler buffer allocation rather than recurring application work as the cause.',[61,62,63,64]),
('G56-RS05-U07','The trace exposes a layered dispatch path in which the custom matmul_add region contains matrix multiplication and addition, aten::matmul dispatches to aten::mm for ordinary 2D matrices, and adding a batch dimension changes the backend operation to aten::bmm.',[66,67,68,71]),
('G56-RS05-U08','cudaOccupancyMaxActiveBlocksPerMultiprocessor is a CPU-side resource-planning query; the tutorial contrasts resource-heavy/adaptively scheduled kernels with lightweight add and notes that seeing this query is a diagnostic clue for resource-intensive kernels such as GEMM or convolution.',[74,76,78,79]),
('G56-RS05-U09','The small-workload trace pairs only about 26 us of useful GPU work with roughly 1.78 ms of cudaDeviceSynchronize time, corresponding to about 98% idle time and another direct symptom of overhead-dominated execution.',[80,81]),
('G56-RS05-U10','Even with the same hardware, code, and inputs, GPU kernel duration is not fixed; a 20-iteration trace shows runtime variation, and the source identifies GPU clock-state variation as one contributing factor.',[86,90,91]),
('G56-RS05-U11','Compiled execution retains runtime machinery: Dynamo performs a cache/guard lookup on every call, AOTDispatcher remains in the runtime stack, and the cached CompiledFxGraph executes the generated code when guards match.',[103,104,105,106]),
('G56-RS05-U12','For this matmul-plus-bias example, Inductor rewrites the graph to aten::addmm at the operator/scheduling level but does not produce one new fused CUDA kernel; generated execution still performs a DtoD bias-buffer copy followed by GEMM, so it is not a single zero-extra-memory fused kernel.',[100,111,112,113]),
]

def main():
    rows=[source_row('RS15',RS15),source_row('RS05',RS05)]
    ts=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    payload={'name':'raos-phase7a-gpt56-sol-reference-v0.1','status':'DEVELOPMENT_ONLY_MANUAL_MODEL_CAPABILITY_REFERENCE_NOT_FRESH_VALIDATION',
      'measurement_timestamp':ts,'measurement_git_head':head(),'authoring_model':'GPT-5.6 Sol',
      'methodology_note':'Assistant-authored semantic reference from the full pinned sources. Not an API latency/cost benchmark and not Human Gold. Evaluated by the same Auditor and downstream Delta probes as DeepSeek candidates.',
      'n_sources':len(rows),'n_scorable':len(rows),'n_first_pass_valid':len(rows),'sources':rows}
    OUT.mkdir(parents=True,exist_ok=True); p=OUT/f'phase7a_gpt56_sol_reference_v0_1_{ts}.json'
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(p)
    print(json.dumps({'head':payload['measurement_git_head'],'sources':[(r['source']['source_id'],r['n_non_event_units'],r['n_non_event_supports']) for r in rows]},indent=2))
if __name__=='__main__': main()
