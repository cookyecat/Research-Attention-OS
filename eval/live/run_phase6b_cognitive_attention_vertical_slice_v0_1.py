from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.phase6b_cognitive_semantics_v0_1 import (
    COGNITIVE_SLICE_VERSION,
    audited_units_to_extraction,
    build_phase6b_collective_location_only_nodes,
    build_phase6b_mvp_kernel_nodes,
    build_phase6b_perf_challenge_nodes,
    fixture_code_by_id,
    render_audited_cognitive_context,
)
from eval.live.run_standing_radar_fit_eval import git_head, load_repo_env
DEFAULT_MANIFEST = ROOT / "eval/live/manifest.phase6b_cognitive_attention_vertical_slice.v0.1.yaml"
DEFAULT_AUDIT = ROOT / "eval/live/results/phase6b_epistemic_unit_audit_v0_1/phase6b_epistemic_unit_audit_v0_1_20260908T041732Z.json"
DEFAULT_AWARENESS = ROOT / "eval/live/results/phase6a_aware_drop_vertical_slice_v0_1_1/phase6a_aware_drop_vertical_slice_v0_1_1_20260908T003719Z.json"
DEFAULT_OUT_DIR = ROOT / "eval/live/results/phase6b_cognitive_attention_vertical_slice_v0_1"
RUN_VERSION = "phase6b-cognitive-attention-vertical-slice-v0.1"


def _value(value):
    return value.value if hasattr(value, "value") else value


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _kernel_nodes(name: str):
    if name == "MVP":
        return build_phase6b_mvp_kernel_nodes()
    if name == "PERF_CHALLENGE":
        return build_phase6b_perf_challenge_nodes()
    if name == "COLLECTIVE_LOCATION_ONLY":
        return build_phase6b_collective_location_only_nodes()
    raise ValueError(f"unknown kernel_fixture: {name}")


def _kernel_snapshot(nodes) -> list[dict]:
    return [
        {
            "id": str(n.id),
            "node_type": n.node_type,
            "title": n.title,
            "status": n.status,
            "payload": dict(n.payload or {}),
            "current_version": n.current_version,
        }
        for n in nodes
    ]


def _awareness_by_event(payload: dict) -> dict[str, dict]:
    return {str(row["event_id"]): row for row in payload.get("rows") or []}


def _source_by_id(payload: dict) -> dict[str, dict]:
    return {str(row["source_id"]): row for row in payload.get("sources") or []}


def _awareness_signals(row):
    if row is None:
        return None
    from app.services.scheduler import AwarenessSignals
    labels = row.get("labels") or {}
    return AwarenessSignals(
        domain_fit=labels.get("D") == "IN",
        event_significance=labels.get("S") == "MATERIAL",
        attention_momentum=labels.get("P") == "SALIENT",
    )


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


def run(manifest_path: Path, audit_path: Path, awareness_path: Path) -> dict:
    load_repo_env()
    from app.cognitive.factory import get_provider
    from app.services.cognitive_impact import canonical_delta_content, primary_update
    from app.services.scheduler import RuntimeView, route, validate_plan

    manifest = _load_yaml(manifest_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    awareness_payload = json.loads(awareness_path.read_text(encoding="utf-8"))
    sources = _source_by_id(audit)
    awareness_rows = _awareness_by_event(awareness_payload)
    rows = []
    for case in manifest.get("cases") or []:
        source_id = str(case["source_id"])
        source = sources[source_id]
        units = source.get("admitted_units") or []
        extraction = audited_units_to_extraction(units)
        context = render_audited_cognitive_context(units)
        nodes = _kernel_nodes(str(case["kernel_fixture"]))
        before = _kernel_snapshot(nodes)
        code_by_id = fixture_code_by_id(nodes)

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
        awareness_event_id = case.get("awareness_event_id")
        awareness_row = awareness_rows.get(str(awareness_event_id)) if awareness_event_id else None
        awareness = _awareness_signals(awareness_row)
        plan = route(
            assessment.features,
            RuntimeView(),
            assessment=assessment,
            matches=matches,
            awareness=awareness,
        )
        validate_plan(plan)
        after = _kernel_snapshot(nodes)

        rows.append({
            "case_id": str(case["id"]),
            "source_id": source_id,
            "kernel_fixture": str(case["kernel_fixture"]),
            "provenance": str(case["provenance"]),
            "awareness_event_id": awareness_event_id,
            "awareness_labels": awareness_row.get("labels") if awareness_row else None,
            "n_admitted_units": len(units),
            "matches": [_match_row(m, code_by_id) for m in matches],
            "assessment": assessment.as_dict(),
            "primary_delta": {
                "operation": operation,
                "target_node_id": str(target_id) if target_id else None,
                "target_fixture_code": code_by_id.get(str(target_id)) if target_id else None,
                "delta_content": canonical_delta_content(assessment),
            },
            "attention_policy": {
                "disposition": plan.disposition.value,
                "reason": plan.reason,
                "expected_output": plan.expected_output.value,
                "watch_after_processing": plan.watch_after_processing,
                "watch_triggers": list(plan.watch_triggers),
            },
            "kernel_unchanged_after_judgment": before == after,
            "stage_provenance": getattr(provider, "stage_provenance", {}),
            "retrieval": getattr(provider, "last_retrieval", None),
        })

    disposition_counts = Counter(row["attention_policy"]["disposition"] for row in rows)
    transition_counts = Counter(row["primary_delta"]["operation"] or "NONE" for row in rows)
    return {
        "name": "raos-phase6b-cognitive-attention-vertical-slice-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "run_version": RUN_VERSION,
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "cognitive_slice_version": COGNITIVE_SLICE_VERSION,
        "manifest": str(manifest_path),
        "input_audit_artifact": str(audit_path),
        "input_awareness_artifact": str(awareness_path),
        "n_cases": len(rows),
        "transition_counts": dict(sorted(transition_counts.items())),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "all_kernel_snapshots_unchanged": all(r["kernel_unchanged_after_judgment"] for r in rows),
        "rows": rows,
        "methodology_note": (
            "Development integration only. Natural cases use the fixed MVP Kernel; counterfactual cases "
            "change K_t explicitly and are not claims about the user's real cognition. Frozen Delta and "
            "production Attention Policy semantics are unchanged."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--awareness", type=Path, default=DEFAULT_AWARENESS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    payload = run(args.manifest, args.audit, args.awareness)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"phase6b_cognitive_attention_vertical_slice_v0_1_{payload['measurement_timestamp']}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "measurement_git_head": payload["measurement_git_head"],
        "transition_counts": payload["transition_counts"],
        "disposition_counts": payload["disposition_counts"],
        "all_kernel_snapshots_unchanged": payload["all_kernel_snapshots_unchanged"],
        "rows": [
            {
                "case_id": row["case_id"],
                "delta": row["primary_delta"],
                "disposition": row["attention_policy"]["disposition"],
            }
            for row in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
