from __future__ import annotations

from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.services.cognitive_impact import CognitiveImpactAssessment, legal_public_effects, normalize_frozen_transition
from app.services.effect_calibration import MAGNITUDE_FREE_CALIBRATION, RAW_CARDINAL_CALIBRATION
from app.services.pareto_decision_strategy import pareto_frontier
from app.services.scheduler import RuntimeView, get_decision_strategy, route
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _base_world, _load_manifest
from eval.live.run_phase8c6_magnitude_free_calibration_ab_v0_1 import (
    CASES,
    STEP2,
    STEP2_SHA256,
    _features,
    _load_frozen,
    _reconstruct_effects,
    _reconstruct_matches,
)

RUN_VERSION = "phase8c6-magnitude-perturbation-invariance-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c6_magnitude_perturbation_invariance_v0_1"
VARIANTS = ("original", "all_low", "all_high", "complement")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _perturb(effects, variant: str):
    out = []
    for effect in effects:
        if variant == "original":
            value = float(effect.change_magnitude)
        elif variant == "all_low":
            value = 0.01
        elif variant == "all_high":
            value = 0.99
        elif variant == "complement":
            value = max(0.01, min(0.99, 1.0 - float(effect.change_magnitude)))
        else:
            raise ValueError(variant)
        out.append(replace(effect, change_magnitude=value))
    return out


def _frontier_signature(assessment, matches, calibration):
    normalized = normalize_frozen_transition(assessment, matches).assessment
    frontier = pareto_frontier(
        legal_public_effects(normalized), matches, calibration_strategy=calibration
    )
    return tuple(
        sorted(
            (effect.operation.value, str(effect.target_kernel_node_id) if effect.target_kernel_node_id else None)
            for effect in frontier
        )
    )


def _decision(strategy_id: str, assessment, matches):
    plan = route(
        _features(), RuntimeView(), assessment=assessment, matches=matches,
        decision_strategy=get_decision_strategy(strategy_id),
    )
    return (plan.disposition.value, plan.expected_output.value, plan.reason)


def main() -> int:
    raw = STEP2.read_bytes()
    if hashlib.sha256(raw).hexdigest() != STEP2_SHA256:
        raise RuntimeError("Frozen Phase8C.3 artifact SHA mismatch")
    frozen = _load_frozen()
    manifest = _load_manifest()
    rows = []
    for case_id in CASES:
        for run in frozen.get("runs") or []:
            if run.get("case") != case_id or run.get("status") != "OK":
                continue
            engine, db, _source, _codes = _base_world(case_id, dict(manifest["cases"][case_id]))
            try:
                from app.services.pipeline import _active_kernel
                nodes = _active_kernel(db)
                matches = _reconstruct_matches(run, nodes)
                source_effects = _reconstruct_effects(run, nodes)
                variants = {}
                for variant in VARIANTS:
                    assessment = CognitiveImpactAssessment(effects=_perturb(source_effects, variant), attention_cost=2.0)
                    variants[variant] = {
                        "raw_cardinal": _decision("pareto-multidelta", assessment, matches),
                        "magnitude_free": _decision("pareto-multidelta-magnitude-free", assessment, matches),
                        "raw_frontier": _frontier_signature(assessment, matches, RAW_CARDINAL_CALIBRATION),
                        "magnitude_free_frontier": _frontier_signature(assessment, matches, MAGNITUDE_FREE_CALIBRATION),
                    }
                mf_decisions = {v["magnitude_free"] for v in variants.values()}
                mf_frontiers = {v["magnitude_free_frontier"] for v in variants.values()}
                raw_decisions = {v["raw_cardinal"] for v in variants.values()}
                row = {
                    "case": case_id,
                    "repeat": int(run["repeat"]),
                    "magnitude_free_decision_invariant": len(mf_decisions) == 1,
                    "magnitude_free_frontier_invariant": len(mf_frontiers) == 1,
                    "raw_cardinal_decision_changed": len(raw_decisions) > 1,
                    "variants": variants,
                }
                rows.append(row)
                print(json.dumps({k: row[k] for k in row if k != "variants"}, ensure_ascii=False), flush=True)
            finally:
                db.close(); engine.dispose()

    summary = {}
    for case_id in CASES:
        cr = [r for r in rows if r["case"] == case_id]
        summary[case_id] = {
            "runs": len(cr),
            "magnitude_free_decision_invariant": sum(r["magnitude_free_decision_invariant"] for r in cr),
            "magnitude_free_frontier_invariant": sum(r["magnitude_free_frontier_invariant"] for r in cr),
            "raw_cardinal_decision_changed": sum(r["raw_cardinal_decision_changed"] for r in cr),
        }
    output = {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_MAGNITUDE_PERTURBATION_INVARIANCE",
        "measurement_sha": git_head(),
        "source_artifact": str(STEP2.relative_to(ROOT)),
        "source_artifact_sha256": STEP2_SHA256,
        "perturbations": list(VARIANTS),
        "frozen": "operation/target/epistemic/importance/Kernel/matches/runtime/Pareto policy",
        "summary": summary,
        "rows": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=list) + "\n")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
