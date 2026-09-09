from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import CognitiveEffect, CognitiveImpactAssessment
from app.services.matching import KernelMatch
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_assess
import eval.live.run_phase8c8_semantic_topology_stability_v0_1 as topo
from eval.live.run_phase8c7_real_web_magnitude_free_validation_v0_1 import _assessment, _features

RUN_VERSION = "phase8c9-anchored-open-new-admission-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c9_anchored_open_new_admission_v0_1"
SOURCE = ROOT / "eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json"
SOURCE_SHA256 = "f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216"
BASELINE_ID = "pareto-multidelta-magnitude-free"
CANDIDATE_ID = "pareto-multidelta-magnitude-free-anchored-open-new"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source() -> dict:
    actual = sha256(SOURCE)
    if actual != SOURCE_SHA256:
        raise RuntimeError(f"Phase 8C.8 artifact SHA mismatch: {actual}")
    return json.loads(SOURCE.read_text())


def _maps(nodes):
    code_to_node = {}
    for n in nodes:
        code = str((n.payload or {}).get("phase6b_fixture_code") or n.title)
        code_to_node[code] = n
    return code_to_node


def _reconstruct_matches(serialized, nodes):
    by_code = _maps(nodes)
    out = []
    for item in serialized or []:
        node = by_code[str(item["target"])]
        rel = str(item.get("relevance_type") or "TOPIC")
        out.append(KernelMatch(
            node_id=node.id,
            node_type=node.node_type,
            title=node.title,
            score=float(item.get("score") or 0.0),
            reason=str(item.get("reason") or ""),
            structural=rel.upper() == "STRUCTURAL",
            relevance_type=rel,
        ))
    return out


def _reconstruct_assessment(serialized, nodes):
    by_code = _maps(nodes)
    effects = []
    for item in serialized or []:
        op = CognitiveEffectKind(str(item["operation"]))
        target_code = item.get("target")
        target_node = by_code.get(str(target_code)) if target_code else None
        target_id = target_node.id if target_node is not None else None
        if op == CognitiveEffectKind.OPEN_NEW:
            target_id = None
        effects.append(CognitiveEffect(
            target_kernel_node_id=target_id,
            operation=op,
            change_magnitude=float(item.get("change_magnitude_debug_only") or 0.0),
            epistemic_strength=float(item.get("epistemic_strength") or 0.0),
            target_importance=float(item.get("target_importance") or 0.0),
            reason=str(item.get("reason") or ""),
            exploration_candidate=op == CognitiveEffectKind.OPEN_NEW,
            target_node_type=target_node.node_type if target_node else None,
        ))
    return CognitiveImpactAssessment(effects=effects, attention_cost=2.0)


def _plan(strategy_id, assessment, matches, features=None):
    strategy = get_decision_strategy(strategy_id)
    if features is None:
        class Parsed:
            attention_cost = 2.0
            evidence_maturity = 0.6
            threatens_active_work = False
            marketing_heavy = False
            high_quality_technical = False
            foundational_paper = False
        features = _features(Parsed())
    plan = route(features, RuntimeView(), assessment=assessment, matches=matches, decision_strategy=strategy)
    return {
        "disposition": plan.disposition.value,
        "expected_output": plan.expected_output.value,
        "strategy": strategy.execution_snapshot(),
    }


def replay_gate1(data: dict):
    rows = []
    for case in data["cases"]:
        case_id = case["case"]
        if "error" in case:
            continue
        nodes = topo._nodes(case_id)
        modal_repeat = int(case["locate"]["modal_representative_repeat"])
        locate_row = next(r for r in case["locate"]["runs"] if int(r["repeat"]) == modal_repeat)
        matches = _reconstruct_matches(locate_row.get("matches") or [], nodes)
        for run in case["impact"]["runs"]:
            if run.get("status") != "OK":
                continue
            assessment = _reconstruct_assessment(run.get("effects") or [], nodes)
            baseline = _plan(BASELINE_ID, assessment, matches)
            candidate = _plan(CANDIDATE_ID, assessment, matches)
            n_open = sum(1 for e in assessment.effects if e.operation == CognitiveEffectKind.OPEN_NEW)
            rows.append({
                "case": case_id,
                "repeat": int(run["repeat"]),
                "n_open_new": n_open,
                "has_modal_locate_matches": bool(matches),
                "baseline": baseline,
                "candidate": candidate,
            })
    summary = {}
    for case_id in topo.CASES:
        rr = [r for r in rows if r["case"] == case_id]
        if not rr:
            continue
        summary[case_id] = {
            "n": len(rr),
            "baseline_attention": dict(Counter(r["baseline"]["disposition"] for r in rr)),
            "candidate_attention": dict(Counter(r["candidate"]["disposition"] for r in rr)),
            "n_runs_with_open_new": sum(r["n_open_new"] > 0 for r in rr),
            "attention_changed_repeats": [r["repeat"] for r in rr if r["baseline"]["disposition"] != r["candidate"]["disposition"]],
        }
    return rows, summary


def stress_d(repeats: int):
    case_id = "D"
    units, source_meta = topo.load_units(case_id)
    nodes = topo._nodes(case_id)
    matches = []  # Phase 8C.8 modal Locate for D is exactly empty.
    rows = []
    for repeat in range(1, repeats + 1):
        try:
            parsed, meta, events = native_assess(units, nodes, matches, chat_fn=topo._forced_chat)
            assessment = _assessment(parsed, nodes)
            baseline = _plan(BASELINE_ID, assessment, matches, _features(parsed))
            candidate = _plan(CANDIDATE_ID, assessment, matches, _features(parsed))
            opens = [e for e in assessment.effects if e.operation == CognitiveEffectKind.OPEN_NEW]
            row = {
                "repeat": repeat,
                "status": "OK",
                "n_effects": len(assessment.effects),
                "n_open_new": len(opens),
                "open_new_reasons": [str(e.reason or "") for e in opens],
                "baseline": baseline,
                "candidate": candidate,
                "meta": meta,
                "schema_events": events,
            }
        except Exception as exc:
            row = {"repeat": repeat, "status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000]}
        rows.append(row)
        print(json.dumps({
            "case": "D", "stress_repeat": repeat, "status": row["status"],
            "n_open_new": row.get("n_open_new"),
            "baseline": (row.get("baseline") or {}).get("disposition"),
            "candidate": (row.get("candidate") or {}).get("disposition"),
            "error": row.get("error"),
        }, ensure_ascii=False), flush=True)
    ok = [r for r in rows if r["status"] == "OK"]
    return {
        "source": source_meta,
        "frozen_locate": [],
        "rows": rows,
        "summary": {
            "n": repeats,
            "n_ok": len(ok),
            "n_open_new_bursts": sum(r["n_open_new"] > 0 for r in ok),
            "baseline_attention": dict(Counter(r["baseline"]["disposition"] for r in ok)),
            "candidate_attention": dict(Counter(r["candidate"]["disposition"] for r in ok)),
            "candidate_stability": (max(Counter(r["candidate"]["disposition"] for r in ok).values()) / len(ok)) if ok else 0.0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stress-repeats", type=int, default=12)
    args = parser.parse_args()
    source = _load_source()
    replay_rows, replay_summary = replay_gate1(source)
    print("REPLAY_SUMMARY=" + json.dumps(replay_summary, ensure_ascii=False), flush=True)
    stress = stress_d(args.stress_repeats)
    output = {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_OPEN_NEW_ADMISSION_REPLAY_AND_STRESS",
        "measurement_sha": git_head(),
        "source_artifact": str(SOURCE.relative_to(ROOT)),
        "source_sha256": SOURCE_SHA256,
        "baseline_strategy": get_decision_strategy(BASELINE_ID).execution_snapshot(),
        "candidate_strategy": get_decision_strategy(CANDIDATE_ID).execution_snapshot(),
        "replay_summary": replay_summary,
        "replay_rows": replay_rows,
        "d_empty_locate_stress": stress,
        "interpretation_boundary": "v0.1 tests only jurisdiction anchoring; it does not prove semantic novelty/source-grounding sufficiency for anchored OPEN_NEW.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={sha256(path)}")
    print(json.dumps({"replay": replay_summary, "stress": stress["summary"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
