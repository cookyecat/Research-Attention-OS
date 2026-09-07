"""Targeted component/stability study for Semantic Evidence Auditor v0.1.1.

Development-only. Repeats only three diagnostic real RS02 edges to separate:
- irrelevant metadata effects on an obvious positive control;
- metadata utility on a metadata-dependent temporal edge;
- same-container context utility on a discourse-sensitive edge.

No Sensor change. No semantic-object change. No Auditor change. No Human-Gold accuracy claim.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.run_semantic_evidence_auditor_real_edges_v0_1_1 import project_provenance_edges
from eval.live.semantic_evidence_auditor_v0_1_1 import (
    audit_semantic_evidence_v0_1_1,
    invocation_record,
)
from eval.live.semantic_evidence_packet_v0_1 import (
    resolve_cited_container,
    source_metadata_excerpt,
)
from eval.live.semantic_source_loader_v0_1 import load_development_corpus

OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_auditor_component_stability_v0_1"

Condition = Literal["BASELINE", "METADATA_ONLY", "CONTEXT_ONLY"]

TARGETS: dict[str, dict[str, Any]] = {
    "positive_pr_count": {
        "audit_id": "RS02:evt-rs02-001:action_change:1",
        "conditions": ["BASELINE", "METADATA_ONLY"],
        "purpose": "obvious positive control; test irrelevant-metadata stability",
    },
    "temporal_uncertainty": {
        "audit_id": "RS02:evt-rs02-001:uncertainty:1",
        "conditions": ["BASELINE", "METADATA_ONLY"],
        "purpose": "metadata-dependent edge; test reproducible metadata benefit",
    },
    "workflow_context": {
        "audit_id": "RS02:non_event_unit:neu-rs02-005",
        "conditions": ["BASELINE", "CONTEXT_ONLY"],
        "purpose": "discourse-sensitive edge; isolate same-container context effect",
    },
}


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-artifact", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def _primary_item(raw: dict[str, Any]) -> dict[str, str]:
    return {
        "source_id": str(raw["source_id"]),
        "support_pointer": str(raw["support_pointer"]),
        "support_excerpt": str(raw["support_excerpt"]),
    }


def build_condition_evidence(
    *,
    condition: Condition,
    edge: dict[str, Any],
    source,
) -> list[dict[str, str]]:
    """Build exactly one controlled evidence condition without adjacent retrieval."""
    evidence = [_primary_item(item) for item in edge.get("evidence") or []]
    if not evidence:
        raise ValueError("target edge has no primary evidence")

    if condition == "BASELINE":
        return evidence

    if condition == "METADATA_ONLY":
        return evidence + [
            {
                "source_id": source.source_id,
                "support_pointer": "TRUSTED_SOURCE_METADATA",
                "support_excerpt": source_metadata_excerpt(source),
            }
        ]

    if condition == "CONTEXT_ONLY":
        out = list(evidence)
        seen = {(item["support_pointer"], item["support_excerpt"]) for item in out}
        for item in evidence:
            container = resolve_cited_container(source, item["support_pointer"])
            if not container or container == item["support_excerpt"]:
                continue
            if len(container) > 1600:
                continue
            context = {
                "source_id": source.source_id,
                "support_pointer": f"{item['support_pointer']} [FULL CITED CONTAINER]",
                "support_excerpt": container,
            }
            key = (context["support_pointer"], context["support_excerpt"])
            if key not in seen:
                out.append(context)
                seen.add(key)
        return out

    raise ValueError(f"unknown condition: {condition}")


def summarize_trials(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["case"], row["condition"])].append(row)

    summary: dict[str, Any] = {}
    for (case, condition), items in sorted(grouped.items()):
        verdicts = Counter(
            item["audit_result"]["verdict"]
            for item in items
            if item.get("audit_result")
        )
        reasons = Counter(
            item["audit_result"]["reason_code"]
            for item in items
            if item.get("audit_result")
        )
        summary.setdefault(case, {})[condition] = {
            "n": len(items),
            "n_scorable": sum(1 for item in items if item["scorable"]),
            "n_first_pass_valid": sum(
                1 for item in items if item["scorable"] and not item["repair_used"]
            ),
            "verdict_counts": dict(sorted(verdicts.items())),
            "reason_counts": dict(sorted(reasons.items())),
        }
    return summary


def main() -> None:
    args = parse_args()
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    artifact_path = args.sensor_artifact.expanduser().resolve()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    edges = {edge["audit_id"]: edge for edge in project_provenance_edges(artifact)}
    source_map = {source.source_id: source for source in load_development_corpus()}

    for spec in TARGETS.values():
        if spec["audit_id"] not in edges:
            raise SystemExit(f"target edge missing: {spec['audit_id']}")

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    rows: list[dict[str, Any]] = []
    for case, spec in TARGETS.items():
        edge = edges[spec["audit_id"]]
        source = source_map[edge["source_id"]]
        for condition in spec["conditions"]:
            evidence = build_condition_evidence(
                condition=condition,
                edge=edge,
                source=source,
            )
            for repeat_idx in range(1, args.repeats + 1):
                result = audit_semantic_evidence_v0_1_1(
                    audit_id=edge["audit_id"],
                    object_type=edge["object_type"],
                    semantic_object=edge["semantic_object"],
                    evidence=evidence,
                )
                rows.append(
                    {
                        "case": case,
                        "purpose": spec["purpose"],
                        "condition": condition,
                        "repeat": repeat_idx,
                        "audit_id": edge["audit_id"],
                        "object_type": edge["object_type"],
                        "semantic_object": edge["semantic_object"],
                        "evidence": evidence,
                        "scorable": bool(result.get("scorable")),
                        "failure_kind": result.get("failure_kind"),
                        "repair_used": bool(result.get("repair_used")),
                        "schema_events": result.get("schema_events") or [],
                        "model_meta": result.get("model_meta"),
                        "audit_result": result.get("result") if result.get("scorable") else None,
                    }
                )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "name": "raos-semantic-evidence-auditor-component-stability-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "sensor_artifact": str(artifact_path),
        "repeats": args.repeats,
        "auditor_invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "targets": TARGETS,
        "summary": summarize_trials(rows),
        "trials": rows,
        "methodology_note": (
            "Targeted repeated development study. No Human Gold. Sensor, semantic objects, and "
            "Auditor v0.1.1 are fixed. Only BASELINE vs METADATA_ONLY or CONTEXT_ONLY changes."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_auditor_component_stability_v0_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite development artifact: {out_path}")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
