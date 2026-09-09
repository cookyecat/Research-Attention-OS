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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.client import chat_json
from app.services.pipeline import _active_kernel
from eval.live.phase6b_cognitive_semantics_v0_1 import admitted_epistemic_units
from eval.live.phase8c3_native_cognitive_interface_v0_1 import native_locate, native_assess
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _base_world, _load_manifest

RUN_VERSION = "phase8c3-native-interface-probe-v0.1"
CASES = ("RS05", "RS15", "RS11", "RS12")
HIST_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
REGRESSION_AUDIT = ROOT / "eval/live/results/phase7a_v0_2_6_regression_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T094903Z.json"
OUT_DIR = ROOT / "eval/live/results/phase8c3_native_interface_probe_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _forced_chat(messages, **kwargs):
    return chat_json(
        messages,
        timeout=float(kwargs.get("timeout") or 45.0),
        thinking=kwargs.get("thinking"),
        reasoning_effort=kwargs.get("reasoning_effort"),
        temperature=0.1,
    )


def _load_units(case_id: str):
    path = HIST_AUDIT if case_id in {"RS05", "RS15"} else REGRESSION_AUDIT
    raw = path.read_bytes()
    data = json.loads(raw)
    row = next(x for x in data["sources"] if x.get("source_id") == case_id)
    return admitted_epistemic_units(list(row.get("audits") or [])), hashlib.sha256(raw).hexdigest()

def _effect_key(effect, code_by_id):
    target = None
    if effect.target_kernel_node_id is not None:
        target = code_by_id.get(effect.target_kernel_node_id, str(effect.target_kernel_node_id))
    return (effect.operation, target)


def _one(case_id: str, case: dict, repeat: int):
    engine, db, source, code_by_id = _base_world(case_id, case)
    try:
        units, audit_sha = _load_units(case_id)
        nodes = _active_kernel(db)
        matches, match_meta, match_events = native_locate(units, nodes, chat_fn=_forced_chat)
        impact, impact_meta, impact_events = native_assess(units, nodes, matches, chat_fn=_forced_chat)
        effects = [
            {
                "operation": e.operation,
                "target": _effect_key(e, code_by_id)[1],
                "change_magnitude": e.change_magnitude,
                "epistemic_strength": e.epistemic_strength,
                "target_importance": e.target_importance,
                "reason": e.reason,
                "exploration_candidate": e.exploration_candidate,
            }
            for e in impact.effects
        ]
        return {"status": "OK", "repeat": repeat, "n_units": len(units), "audit_sha256": audit_sha,
                "matches": [{"target": code_by_id.get(m.kernel_node_id, str(m.kernel_node_id)), "score": m.score, "relevance_type": m.relevance_type, "reason": m.reason} for m in matches],
                "effects": effects, "match_meta": match_meta, "impact_meta": impact_meta,
                "schema_events": [*match_events, *impact_events]}
    except Exception as exc:
        return {"status": "ERROR", "repeat": repeat, "error_type": type(exc).__name__, "error": str(exc)[:3000]}
    finally:
        db.close(); engine.dispose()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    manifest = _load_manifest()
    rows = []
    for case_id in CASES:
        case = dict(manifest["cases"][case_id])
        for repeat in range(1, args.repeats + 1):
            row = _one(case_id, case, repeat)
            row["case"] = case_id
            rows.append(row)
            print(json.dumps({"case": case_id, "repeat": repeat, "status": row.get("status"), "effects": row.get("effects"), "error": row.get("error")}, ensure_ascii=False), flush=True)
    summary = {}
    for case_id in CASES:
        ok = [r for r in rows if r["case"] == case_id and r["status"] == "OK"]
        keys = [tuple((e["operation"], e["target"]) for e in r["effects"]) for r in ok]
        summary[case_id] = {"n_runs": args.repeats, "n_ok": len(ok), "n_errors": args.repeats-len(ok),
                            "effect_set_counts": dict(Counter(str(k) for k in keys)),
                            "n_unique_effect_sets": len(set(keys))}
    output = {"run_version": RUN_VERSION, "status": "DEVELOPMENT_NATIVE_INTERFACE_ONLY", "measurement_sha": git_head(),
              "historical_audit_artifact": str(HIST_AUDIT.relative_to(ROOT)), "summary": summary, "runs": rows}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
