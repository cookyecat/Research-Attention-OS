from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.phase6b_cognitive_semantics_v0_1 import (
    audited_units_to_extraction,
    build_phase6b_mvp_kernel_nodes,
    build_phase6b_perf_challenge_nodes,
    fixture_code_by_id,
    render_audited_cognitive_context,
)
from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env

DEFAULT_AUDIT = ROOT / "eval/live/results/phase6b_epistemic_unit_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T041732Z.json"
DEFAULT_OUT_DIR = ROOT / "eval/live/results/phase7a_external_world_model_fidelity_ab_v0_1"

def _value(x):
    return x.value if hasattr(x, "value") else x


def _sensor_units(sensor: dict, source_id: str) -> list[dict]:
    for row in sensor["sources"]:
        if row["source"]["source_id"] == source_id:
            return list((row.get("batch") or {}).get("non_event_units") or [])
    raise KeyError(source_id)


def _kernel_for(source_id: str):
    if source_id == "RS05":
        return "phase6b-perf-challenge-counterfactual", build_phase6b_perf_challenge_nodes()
    return "phase6b-mvp-in-memory-copy", build_phase6b_mvp_kernel_nodes()


def _condition(provider, units, nodes):
    from app.services.cognitive_impact import canonical_delta_content, primary_update
    from app.services.scheduler import RuntimeView, route, validate_plan

    extraction = audited_units_to_extraction(units)
    context = render_audited_cognitive_context(units)
    matches = provider.match_kernel(extraction, nodes, extra_text=context)
    assessment = provider.assess_cognitive_impact(
        context, extraction, matches,
        independent_source_count=1, nodes=nodes,
    )
    update = primary_update(assessment)
    op = _value(update.get("operation"))
    target = update.get("target_node_id")
    code_by_id = fixture_code_by_id(nodes)
    plan = validate_plan(route(
        assessment.features, RuntimeView(), assessment=assessment, matches=matches,
    ))
    return {
        "n_units": len(units),
        "matches": [
            {
                "fixture_code": code_by_id.get(str(m.node_id)),
                "node_type": m.node_type,
                "title": m.title,
                "score": m.score,
            }
            for m in matches
        ],
        "primary_delta": {
            "operation": op,
            "target_fixture_code": code_by_id.get(str(target)) if target else None,
            "delta_content": canonical_delta_content(assessment),
        },
        "attention_without_awareness": plan.disposition.value,
        "features": assessment.features.as_dict(),
        "stage_provenance": getattr(provider, "stage_provenance", {}),
    }


def run(audit_path: Path) -> dict:
    load_repo_env()
    from app.cognitive.factory import get_provider

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    sensor_path = Path(audit["input_sensor_artifact"])
    sensor = json.loads(sensor_path.read_text(encoding="utf-8"))
    rows = []
    for source in audit["sources"]:
        source_id = source["source_id"]
        admitted = list(source.get("admitted_units") or [])
        full = _sensor_units(sensor, source_id)
        fixture_name, nodes = _kernel_for(source_id)

        audited_result = _condition(get_provider(), admitted, nodes)
        full_result = _condition(get_provider(), full, nodes)
        delta_same = (
            audited_result["primary_delta"]["operation"] == full_result["primary_delta"]["operation"]
            and audited_result["primary_delta"]["target_fixture_code"] == full_result["primary_delta"]["target_fixture_code"]
        )
        action_same = audited_result["attention_without_awareness"] == full_result["attention_without_awareness"]
        rows.append({
            "source_id": source_id,
            "kernel_fixture": fixture_name,
            "sensor_units": len(full),
            "auditor_admitted_units": len(admitted),
            "admission_rate": round(len(admitted) / len(full), 4) if full else None,
            "A_production_valid_audited": audited_result,
            "B_diagnostic_pre_audit_sensor": full_result,
            "delta_preserved": delta_same,
            "attention_preserved": action_same,
        })

    return {
        "name": "raos-phase7a-external-world-model-fidelity-ab-v0.1",
        "status": "DEVELOPMENT_ATTRIBUTION_NOT_FRESH_VALIDATION",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "input_sensor_artifact": str(sensor_path),
        "input_audit_artifact": str(audit_path),
        "conditions": {
            "A": "production-valid Auditor-admitted semantics",
            "B": "diagnostic pre-audit Sensor semantics; attribution only, never production truth",
        },
        "n_sources": len(rows),
        "n_delta_preserved": sum(r["delta_preserved"] for r in rows),
        "n_attention_preserved": sum(r["attention_preserved"] for r in rows),
        "rows": rows,
        "methodology_note": (
            "Condition B is an information-availability ablation, not an oracle. "
            "Differences show that Auditor/Sensor provenance admission can causally alter downstream judgment; "
            "agreement does not prove semantic completeness."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    payload = run(args.audit)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase7a_external_world_model_fidelity_ab_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "measurement_git_head": payload["measurement_git_head"],
        "n_delta_preserved": payload["n_delta_preserved"],
        "n_attention_preserved": payload["n_attention_preserved"],
        "rows": [
            {
                "source_id": r["source_id"],
                "admission": f"{r['auditor_admitted_units']}/{r['sensor_units']}",
                "A_delta": r["A_production_valid_audited"]["primary_delta"],
                "B_delta": r["B_diagnostic_pre_audit_sensor"]["primary_delta"],
                "A_attention": r["A_production_valid_audited"]["attention_without_awareness"],
                "B_attention": r["B_diagnostic_pre_audit_sensor"]["attention_without_awareness"],
                "delta_preserved": r["delta_preserved"],
                "attention_preserved": r["attention_preserved"],
            }
            for r in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())