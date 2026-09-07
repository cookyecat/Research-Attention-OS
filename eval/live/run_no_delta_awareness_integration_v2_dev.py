"""Post-calibration development regression for no-Delta integration v2.

Uses already-consumed IA1-IA12 cases. This is NOT fresh validation: D v4/profile v4
was calibrated after inspecting the earlier integrated result. The purpose is only to
check that the user-profile uplift behaves as intended before raw-source integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env
from eval.live.run_no_delta_awareness_integration_v1_eval import (
    DEFAULT_GOLD,
    DEFAULT_TEMPLATE,
    compute_integrated_metrics,
    load_joined_cases,
)
from eval.live.no_delta_awareness_integration_v2 import (
    INTEGRATION_VERSION,
    estimate_integrated_no_delta_awareness_v2,
    expected_gate_disposition,
)
from eval.live.standing_radar_fit_v4 import (
    ESTIMATOR_VERSION as D_ESTIMATOR_VERSION,
    PROFILE_ID as D_PROFILE_ID,
    load_standing_radar_profile,
    prompt_sha256 as d_prompt_sha256,
)
from eval.live.material_consequence_v1 import (
    ESTIMATOR_VERSION as S_ESTIMATOR_VERSION,
    load_material_consequence_profile,
)
from eval.live.collective_attention_v1 import (
    ESTIMATOR_VERSION as P_ESTIMATOR_VERSION,
    load_collective_attention_profile,
)

OUT_DIR = ROOT / "eval" / "live" / "results" / "no_delta_awareness_integration_v2_dev"


def main() -> None:
    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable")

    _, _, joined = load_joined_cases(DEFAULT_TEMPLATE, DEFAULT_GOLD)
    d_profile = load_standing_radar_profile()
    s_profile = load_material_consequence_profile()
    p_profile = load_collective_attention_profile()

    rows = []
    actual_models = {"D": set(), "S": set(), "P": set()}
    for item in joined:
        case = item["template"]
        gold = item["gold"]
        cid = str(case["id"])
        out = estimate_integrated_no_delta_awareness_v2(
            str(case["event"]),
            case["p_packet"],
            d_profile=d_profile,
            s_profile=s_profile,
            p_profile=p_profile,
        )
        d_out = out.get("D") or {}
        s_out = out.get("S") or {}
        p_out = out.get("P") or {}
        for name, comp in (("D", d_out), ("S", s_out), ("P", p_out)):
            model = (comp.get("model_meta") or {}).get("model")
            if model:
                actual_models[name].add(str(model))

        pred_d = d_out.get("standing_radar_fit") if d_out.get("scorable") else None
        pred_s = s_out.get("material_consequence") if s_out.get("scorable") else None
        pred_p = p_out.get("collective_attention_salience") if p_out.get("scorable") else None
        pred_final = out.get("disposition") if out.get("scorable") else None
        human_gate_final = expected_gate_disposition(gold["D"], gold["S"], gold["P"]).value
        row = {
            "case_id": cid,
            "gold_D": gold["D"], "pred_D": pred_d,
            "gold_S": gold["S"], "pred_S": pred_s,
            "gold_P": gold["P"], "pred_P": pred_p,
            "gold_final": gold["final"], "pred_final": pred_final,
            "human_gate_final": human_gate_final,
            "D_correct": pred_d == gold["D"] if pred_d else None,
            "S_correct": pred_s == gold["S"] if pred_s else None,
            "P_correct": pred_p == gold["P"] if pred_p else None,
            "final_correct": pred_final == gold["final"] if pred_final else None,
            "any_component_error": None,
            "gate_wiring_matches": out.get("gate_wiring_matches"),
            "scorable": bool(out.get("scorable")),
            "D": d_out, "S": s_out, "P": p_out,
        }
        if row["scorable"]:
            row["any_component_error"] = not (
                row["D_correct"] and row["S_correct"] and row["P_correct"]
            )
        rows.append(row)

    metrics = compute_integrated_metrics(rows)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-no-delta-awareness-integration-v2-post-calibration-dev",
        "status": "DEVELOPMENT_ONLY_POST_CALIBRATION_NOT_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "integration_version": INTEGRATION_VERSION,
        "source_cases": "IA1-IA12 already-consumed integrated Human Gold",
        "component_identity": {
            "D": {"estimator_version": D_ESTIMATOR_VERSION, "profile_id": D_PROFILE_ID, "prompt_sha256": d_prompt_sha256()},
            "S": {"estimator_version": S_ESTIMATOR_VERSION},
            "P": {"estimator_version": P_ESTIMATOR_VERSION},
        },
        "actual_models": {k: sorted(v) for k, v in actual_models.items()},
        "n_cases": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "metrics": metrics,
        "cases": rows,
        "methodology_note": (
            "Not fresh validation. D v4/profile v4 was calibrated after inspection of the earlier IA run. "
            "This measurement only checks expected post-calibration behavior before raw-source integration."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"no_delta_awareness_integration_v2_dev_{timestamp}.json"
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(json.dumps({
        "n_scorable": artifact["n_scorable"],
        "metrics": metrics,
        "actual_models": artifact["actual_models"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
