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
    COGNITIVE_SLICE_VERSION,
    audited_units_to_extraction,
    build_phase6b_mvp_kernel_nodes,
    render_audited_cognitive_context,
)
from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env

DEFAULT_AUDIT = ROOT / "eval/live/results/phase6b_epistemic_unit_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T041732Z.json"
DEFAULT_OUT_DIR = ROOT / "eval/live/results/phase6b_natural_delta_v0_1"


def _value(x):
    return x.value if hasattr(x, "value") else x


def _match_row(match, code_by_id):
    return {
        "node_id": str(match.node_id),
        "fixture_code": code_by_id.get(str(match.node_id)),
        "node_type": match.node_type,
        "title": match.title,
        "score": match.score,
        "reason": match.reason,
        "structural": match.structural,
        "relevance_type": match.relevance_type,
    }


def run(audit_path: Path) -> dict:
    load_repo_env()
    from app.cognitive.factory import get_provider
    from app.services.cognitive_impact import canonical_delta_content, primary_update
    from app.services.scheduler import RuntimeView, route, validate_plan

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    nodes = build_phase6b_mvp_kernel_nodes()
    code_by_id = {str(n.id): (n.payload or {}).get("phase6b_fixture_code") for n in nodes}
    rows = []
    for source in audit["sources"]:
        source_id = source["source_id"]
        units = source.get("admitted_units") or []
        extraction = audited_units_to_extraction(units)
        context = render_audited_cognitive_context(units)
        provider = get_provider()
        matches = provider.match_kernel(extraction, nodes, extra_text=context)
        assessment = provider.assess_cognitive_impact(
            context,
            extraction,
            matches,
            independent_source_count=1,
            nodes=nodes,
        )
        update = primary_update(assessment)
        operation = _value(update.get("operation"))
        target_id = update.get("target_node_id")
        plan = route(
            assessment.features,
            RuntimeView(),
            assessment=assessment,
            matches=matches,
        )
        validate_plan(plan)
        rows.append({
            "source_id": source_id,
            "n_admitted_units": len(units),
            "audited_context": context,
            "matches": [_match_row(m, code_by_id) for m in matches],
            "assessment": assessment.as_dict(),
            "primary_delta": {
                "operation": operation,
                "target_node_id": target_id,
                "target_fixture_code": code_by_id.get(str(target_id)) if target_id else None,
                "delta_content": canonical_delta_content(assessment),
            },
            "policy_without_awareness": {
                "disposition": plan.disposition.value,
                "reason": plan.reason,
                "expected_output": plan.expected_output.value,
            },
            "positive_delta_policy_complete": operation is not None,
            "stage_provenance": getattr(provider, "stage_provenance", {}),
            "retrieval": getattr(provider, "last_retrieval", None),
        })
    return {
        "name": "raos-phase6b-natural-delta-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "cognitive_slice_version": COGNITIVE_SLICE_VERSION,
        "input_audit_artifact": str(audit_path),
        "kernel_fixture": "phase6b-mvp-in-memory-copy",
        "kernel_nodes": [
            {
                "id": str(n.id),
                "fixture_code": (n.payload or {}).get("phase6b_fixture_code"),
                "node_type": n.node_type,
                "title": n.title,
            }
            for n in nodes
        ],
        "n_sources": len(rows),
        "n_positive_delta": sum(r["primary_delta"]["operation"] is not None for r in rows),
        "rows": rows,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    payload = run(args.audit)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase6b_natural_delta_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "n_sources": payload["n_sources"],
        "n_positive_delta": payload["n_positive_delta"],
        "rows": [
            {
                "source_id": r["source_id"],
                "n_admitted_units": r["n_admitted_units"],
                "matches": [m["fixture_code"] for m in r["matches"]],
                "delta": r["primary_delta"],
                "disposition_without_awareness": r["policy_without_awareness"]["disposition"],
                "complete": r["positive_delta_policy_complete"],
            }
            for r in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
