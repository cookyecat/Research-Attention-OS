from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.services.cognitive_impact import legal_public_effects, normalize_frozen_transition
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess, native_locate
from eval.live.run_phase8c8_semantic_topology_stability_v0_1 import (
    _assessment, _code_maps, _features, _matches, _nodes, _forced_chat,
    match_detail_key, serialize_effect, serialize_native_matches, topology_key,
)
from eval.live.topology_stability_metrics_v0_1 import summarize_topology_stability, categorical_stability, execution_snapshot

RUN_VERSION = "phase8c10-auditor-downstream-propagation-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c10_auditor_downstream_propagation_v0_1"
GATE2A = ROOT / "eval/live/results/phase8c10_auditor_topology_stability_v0_1/phase8c10_auditor_topology_stability_v0.1_20260910T034034Z.json"
GATE2A_SHA = "bf535061ac92bec498816b932454be5bba9e4ab390e1572d88b9a68c52fcd69e"
GATE1 = ROOT / "eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json"
GATE1_SHA = "f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216"
CRITICAL = {
    "RS05": {("CHALLENGE", "CF-B-PERF")},
    "RS15": {("REINFORCE", "B2"), ("REINFORCE", "Q2")},
    "RS11": set(),
    "RS12": set(),
}


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def verify(path: Path, expected: str):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"artifact SHA mismatch {path}: {actual}")


def load_inputs():
    verify(GATE2A, GATE2A_SHA); verify(GATE1, GATE1_SHA)
    g2 = json.loads(GATE2A.read_text())
    g1 = json.loads(GATE1.read_text())
    baseline = {row["case"]: row for row in g1["results"] if row["case"] in CRITICAL}
    worlds = []
    for case in g2["results"]:
        cid = case["case"]
        reference = tuple(case["reference"]["admitted_ids"])
        seen = set()
        for run in case["runs"]:
            if run.get("status") != "OK":
                continue
            key = tuple(run["admitted_ids"])
            if key == reference or key in seen:
                continue
            seen.add(key)
            worlds.append({
                "case": cid,
                "admitted_ids": key,
                "admitted_units": run["admitted_units"],
                "source_audit_repeat": run["repeat"],
                "historical_reference_ids": reference,
            })
    return worlds, baseline


def choose_modal_locate(runs):
    ok = [r for r in runs if r["status"] == "OK"]
    counts = Counter(r["detail_key"] for r in ok)
    best = max(counts.values())
    key = sorted((k for k,v in counts.items() if v == best), key=repr)[0]
    row = next(r for r in ok if r["detail_key"] == key)
    return key, row


def anchored_attention(parsed, native_matches, nodes):
    prod_matches = _matches(native_matches, nodes)
    assessment = _assessment(parsed, nodes)
    normalized = normalize_frozen_transition(assessment, prod_matches).assessment
    legal = legal_public_effects(normalized)
    strategy = get_decision_strategy("pareto-multidelta-magnitude-free-anchored-open-new")
    plan = route(
        _features(parsed), RuntimeView(), assessment=normalized, matches=prod_matches,
        decision_strategy=strategy,
    )
    return plan.disposition.value, legal, strategy.execution_snapshot()


def evaluate_world(world, locate_repeats, impact_repeats):
    cid = world["case"]
    units = world["admitted_units"]
    nodes = _nodes(cid)
    code_by_uuid, code_by_str = _code_maps(nodes)
    locate_runs = []
    locate_objects = {}
    for repeat in range(1, locate_repeats + 1):
        try:
            matches, meta, events = native_locate(units, nodes, chat_fn=_forced_chat)
            dkey = match_detail_key(matches, code_by_uuid)
            row = {"repeat": repeat, "status": "OK", "detail_key": dkey, "matches": serialize_native_matches(matches, code_by_uuid), "meta": meta, "schema_events": events}
            locate_objects[repeat] = matches
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        locate_runs.append(row)
        print(json.dumps({"case":cid,"world":world["admitted_ids"],"stage":"LOCATE","repeat":repeat,"status":row["status"],"detail":row.get("detail_key")},ensure_ascii=False),flush=True)
    modal_key, modal_row = choose_modal_locate(locate_runs)
    frozen_matches = locate_objects[modal_row["repeat"]]

    impact_runs=[]
    topology_keys=[]
    attentions=[]
    for repeat in range(1, impact_repeats + 1):
        try:
            parsed, meta, events = native_assess(units, nodes, frozen_matches, chat_fn=_forced_chat)
            attention, legal, strategy = anchored_attention(parsed, frozen_matches, nodes)
            tkey = topology_key(legal, code_by_str)
            row = {"repeat":repeat,"status":"OK","topology_key":tkey,"effects":[serialize_effect(e,code_by_str) for e in legal],"attention":attention,"meta":meta,"schema_events":events}
            topology_keys.append(tkey); attentions.append(attention)
        except Exception as exc:
            row={"repeat":repeat,"status":"ERROR","error_type":type(exc).__name__,"error":str(exc)[:3000]}
        impact_runs.append(row)
        print(json.dumps({"case":cid,"world":world["admitted_ids"],"stage":"IMPACT","repeat":repeat,"status":row["status"],"topology":row.get("topology_key"),"attention":row.get("attention")},ensure_ascii=False),flush=True)

    report=summarize_topology_stability(topology_keys,critical_relations=CRITICAL[cid])
    return {
        **world,
        "locate":{"modal_detail_key":modal_key,"runs":locate_runs},
        "impact":{"metrics":report.as_dict(),"attention_counts":dict(Counter(attentions)),"attention_stability":categorical_stability(attentions),"runs":impact_runs},
        "decision_strategy":strategy if impact_runs and topology_keys else None,
    }


def baseline_summary(row):
    return {
        "impact_metrics": row["impact"]["topology_metrics"],
        "critical_recall": row["impact"]["critical_recall"],
        "attention": row["impact"]["magnitude_free_attention"],
        "attention_stability": row["impact"]["attention_stability"],
    }


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--locate-repeats",type=int,default=3); parser.add_argument("--impact-repeats",type=int,default=4); args=parser.parse_args()
    worlds, baseline=load_inputs()
    results=[evaluate_world(w,args.locate_repeats,args.impact_repeats) for w in worlds]
    summary={}
    for cid in CRITICAL:
        changed=[r for r in results if r["case"]==cid]
        summary[cid]={
            "historical":baseline_summary(baseline[cid]),
            "changed_worlds":[{
                "admitted_ids":r["admitted_ids"],
                "critical_recall":r["impact"]["metrics"]["critical_relation_recall"],
                "topology_exact_mode_rate":r["impact"]["metrics"]["exact_mode_rate"],
                "topology_jaccard":r["impact"]["metrics"]["mean_pairwise_jaccard"],
                "attention_counts":r["impact"]["attention_counts"],
                "attention_stability":r["impact"]["attention_stability"],
            } for r in changed],
        }
    output={
        "run_version":RUN_VERSION,"status":"AUDITOR_GATE2B_DOWNSTREAM_PROPAGATION","measurement_sha":git_head(),
        "gate2a_artifact":str(GATE2A.relative_to(ROOT)),"gate2a_sha256":GATE2A_SHA,
        "gate1_baseline_artifact":str(GATE1.relative_to(ROOT)),"gate1_baseline_sha256":GATE1_SHA,
        "locate_repeats":args.locate_repeats,"impact_repeats":args.impact_repeats,"metrics_chip":execution_snapshot(),
        "decision_stack":"anchored-open-new + magnitude-free + pareto",
        "results":results,"summary":summary,
    }
    OUT_DIR.mkdir(parents=True,exist_ok=True); stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path=OUT_DIR/f"{RUN_VERSION.replace('-','_')}_{stamp}.json"; path.write_text(json.dumps(output,ensure_ascii=False,indent=2,default=str)+"\n")
    print(f"RESULT_PATH={path.relative_to(ROOT)}"); print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}"); print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
