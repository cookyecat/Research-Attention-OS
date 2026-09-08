from __future__ import annotations

import json, subprocess, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.collective_attention_v1 import (
    ESTIMATOR_VERSION, EVIDENCE_INTERFACE_VERSION, PROMPT_VERSION,
    estimate_collective_attention_v1, prompt_sha256, validate_evidence_packet,
)
from eval.live.phase7b_dynamic_p_simulation_v0_1 import SIMULATION_VERSION, all_dynamic_p_steps
from eval.live.run_standing_radar_fit_eval import load_repo_env

OUT_DIR = ROOT / "eval/live/results/phase7b_dynamic_p_simulation_v0_1"

def git_head():
    return subprocess.check_output(["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip()
def _route_action(p_label: str) -> tuple[str, str]:
    from app.services.scheduler import AwarenessSignals, RuntimeView, SchedulerFeatures, route, validate_plan
    awareness = AwarenessSignals(
        domain_fit=False,          # controlled D=OUT
        event_significance=True,   # controlled S=MATERIAL
        attention_momentum=(p_label == "SALIENT"),
    )
    neutral = SchedulerFeatures(
        topic_relevance=0.0, structural_relevance=0.0, decision_relevance=0.0,
        novelty=0.0, credibility=0.0, kernel_delta=0.0, bottleneck_alignment=0.0,
        disagreement=0.0, actionability=0.0, temporal_value=0.0, cognitive_cost=0.0,
    )
    plan = validate_plan(route(neutral, RuntimeView(), awareness=awareness))
    return plan.disposition.value, plan.reason


def run() -> dict:
    load_repo_env()
    rows = []
    actual_models = set()
    for step in all_dynamic_p_steps():
        validate_evidence_packet(step.packet)
        result = estimate_collective_attention_v1(step.packet)
        label = result.get("collective_attention_salience")
        action = None
        action_reason = None
        if result.get("scorable") and label:
            action, action_reason = _route_action(label)
        meta = result.get("model_meta") or {}
        if meta.get("model"):
            actual_models.add(str(meta["model"]))
        rows.append({
            "scenario_id": step.scenario_id,
            "step_id": step.step_id,
            "event_as_of": step.packet["event"]["as_of"],
            "expected_p": step.expected_p,
            "actual_p": label,
            "p_match": label == step.expected_p,
            "expected_action": step.expected_action,
            "actual_action": action,
            "action_match": action == step.expected_action,
            "p_result": result,
            "action_reason": action_reason,
            "packet": step.packet,
        })

    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario_id"]].append(row)
    return {
        "name": "raos-phase7b-dynamic-p-simulation-v0.1",
        "status": "DEVELOPMENT_SIMULATION_NOT_REAL_WORLD_SALIENCE",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "simulation_version": SIMULATION_VERSION,
        "p_estimator_version": ESTIMATOR_VERSION,
        "p_prompt_version": PROMPT_VERSION,
        "p_prompt_sha256": prompt_sha256(),
        "p_evidence_interface": EVIDENCE_INTERFACE_VERSION,
        "actual_models": sorted(actual_models),
        "controlled_awareness": {"D": "OUT", "S": "MATERIAL", "P": "dynamic estimator output"},
        "n_steps": len(rows),
        "n_scorable": sum(bool(r["p_result"].get("scorable")) for r in rows),
        "n_p_match": sum(bool(r["p_match"]) for r in rows),
        "n_action_match": sum(bool(r["action_match"]) for r in rows),
        "scenario_paths": {
            sid: [
                {"step_id": r["step_id"], "p": r["actual_p"], "action": r["actual_action"]}
                for r in seq
            ]
            for sid, seq in by_scenario.items()
        },
        "rows": rows,
        "methodology_note": (
            "All attention evidence is simulated development evidence. The run tests dynamic state-estimation and "
            "P→frozen no-Delta AWARE wiring only; it does not claim any current real-world salience and does not retune P v1."
        ),
    }
def main() -> int:
    payload = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"phase7b_dynamic_p_simulation_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "head": payload["measurement_git_head"],
        "actual_models": payload["actual_models"],
        "n_steps": payload["n_steps"],
        "n_scorable": payload["n_scorable"],
        "n_p_match": payload["n_p_match"],
        "n_action_match": payload["n_action_match"],
        "scenario_paths": payload["scenario_paths"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
