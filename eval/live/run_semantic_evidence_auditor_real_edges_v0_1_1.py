"""Audit real provenance edges from a Semantic Sensor v0.2.2 development artifact.

This is development-only and intentionally has NO Human Gold. It measures what the binary
Semantic Evidence Auditor says about actual extractor-produced edges. It does not search
for replacement evidence and does not repair the extraction.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_evidence_auditor_v0_1_1 import (
    audit_semantic_evidence_v0_1_1,
    invocation_record,
)

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_auditor_real_edges_v0_1_1"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True, help="Semantic Sensor v0.2.2 JSON artifact")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-edges", type=int, default=None, help="Optional cap for development debugging")
    return parser.parse_args()


def _event_support(evidence_item: dict[str, Any]) -> dict[str, str]:
    return {
        "source_id": str(evidence_item["source_id"]),
        "support_pointer": str(evidence_item["support_pointer"]),
        "support_excerpt": str(evidence_item["support_excerpt"]),
    }


def _supports_from_ids(
    support_ids: list[str],
    evidence_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    out = []
    for support_id in support_ids:
        if support_id not in evidence_by_id:
            raise ValueError(f"support id {support_id!r} not found in event evidence")
        out.append(_event_support(evidence_by_id[support_id]))
    return out


def project_provenance_edges(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    """Project extractor output into local semantic-object <- cited-evidence audit edges."""
    if artifact.get("name") != "raos-semantic-evidence-development-run-v0.2.2":
        raise ValueError("artifact is not a Semantic Sensor v0.2.2 development run")

    edges: list[dict[str, Any]] = []
    for source_row in artifact.get("sources") or []:
        source = source_row.get("source") or {}
        source_id = str(source.get("source_id") or "unknown")
        batch = source_row.get("batch") or {}

        for frame_idx, frame in enumerate(batch.get("event_frames") or [], start=1):
            event_id = str((frame.get("event") or {}).get("event_id") or f"event-{frame_idx}")
            evidence_by_id = {
                str(item["evidence_id"]): item
                for item in frame.get("evidence") or []
                if item.get("evidence_id")
            }

            groups = [
                (
                    "actor_object",
                    frame.get("substantive_actors_objects") or [],
                    lambda obj: (
                        f"name={obj.get('name', '')}; role={obj.get('role', '')}; "
                        f"substantive_basis={obj.get('substantive_basis', '')}"
                    ),
                ),
                (
                    "action_change",
                    frame.get("actions_changes") or [],
                    lambda obj: str(obj.get("description") or ""),
                ),
                (
                    "affected_system_population",
                    frame.get("affected_systems_populations") or [],
                    lambda obj: (
                        f"description={obj.get('description', '')}; "
                        f"reference_scope={obj.get('reference_scope', '')}"
                    ),
                ),
                (
                    "uncertainty",
                    frame.get("uncertainties") or [],
                    lambda obj: (
                        f"field={obj.get('field', '')}; kind={obj.get('kind', '')}; "
                        f"note={obj.get('note', '')}"
                    ),
                ),
            ]

            for object_type, objects, render in groups:
                for object_idx, obj in enumerate(objects, start=1):
                    support_ids = [str(value) for value in obj.get("support_ids") or []]
                    edges.append(
                        {
                            "audit_id": f"{source_id}:{event_id}:{object_type}:{object_idx}",
                            "source_id": source_id,
                            "origin": "event_frame",
                            "event_id": event_id,
                            "object_type": object_type,
                            "semantic_object": render(obj),
                            "support_ids": support_ids,
                            "evidence": _supports_from_ids(support_ids, evidence_by_id),
                        }
                    )

        for unit_idx, unit in enumerate(batch.get("non_event_units") or [], start=1):
            edges.append(
                {
                    "audit_id": f"{source_id}:non_event_unit:{unit.get('unit_id') or unit_idx}",
                    "source_id": source_id,
                    "origin": "non_event_unit",
                    "event_id": None,
                    "object_type": "epistemic_unit",
                    "semantic_object": str(unit.get("statement") or ""),
                    "support_ids": [],
                    "evidence": [
                        {
                            "source_id": str(support["source_id"]),
                            "support_pointer": str(support["support_pointer"]),
                            "support_excerpt": str(support["support_excerpt"]),
                        }
                        for support in unit.get("supports") or []
                    ],
                }
            )

    return edges


def main() -> None:
    args = parse_args()
    artifact_path = args.artifact.expanduser().resolve()
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    edges = project_provenance_edges(artifact)
    if args.max_edges is not None:
        if args.max_edges <= 0:
            raise SystemExit("--max-edges must be positive")
        edges = edges[: args.max_edges]

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    rows = []
    for edge in edges:
        if not edge["evidence"]:
            rows.append(
                {
                    **edge,
                    "scorable": False,
                    "failure_kind": "no_cited_evidence",
                    "error": "edge has no cited evidence",
                    "repair_used": False,
                    "schema_events": [],
                    "model_meta": None,
                    "audit_result": None,
                }
            )
            continue

        result = audit_semantic_evidence_v0_1_1(
            audit_id=edge["audit_id"],
            object_type=edge["object_type"],
            semantic_object=edge["semantic_object"],
            evidence=edge["evidence"],
        )
        rows.append(
            {
                **edge,
                "scorable": bool(result.get("scorable")),
                "failure_kind": result.get("failure_kind"),
                "error": result.get("error"),
                "repair_used": bool(result.get("repair_used")),
                "schema_events": result.get("schema_events") or [],
                "model_meta": result.get("model_meta"),
                "audit_result": result.get("result") if result.get("scorable") else None,
            }
        )

    verdicts = Counter(
        row["audit_result"]["verdict"]
        for row in rows
        if row.get("audit_result")
    )
    reasons = Counter(
        row["audit_result"]["reason_code"]
        for row in rows
        if row.get("audit_result")
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "name": "raos-semantic-evidence-auditor-real-edges-v0.1.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "input_artifact": {
            "path": str(artifact_path),
            "name": artifact.get("name"),
            "measurement_timestamp": artifact.get("measurement_timestamp"),
            "measurement_git_head": artifact.get("measurement_git_head"),
            "prompt_sha256": (artifact.get("invocation") or {}).get("prompt_sha256"),
        },
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "n_edges": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_first_pass_valid": sum(1 for row in rows if row["scorable"] and not row["repair_used"]),
        "n_sufficient": verdicts.get("SUFFICIENT", 0),
        "n_insufficient": verdicts.get("INSUFFICIENT", 0),
        "reason_counts": dict(sorted(reasons.items())),
        "edges": rows,
        "methodology_note": (
            "No Human Gold is attached to this run. This is a development audit of real "
            "extractor-produced provenance edges, not an auditor accuracy benchmark."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_auditor_real_edges_v0_1_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite development artifact: {out_path}")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    print(
        json.dumps(
            {
                "n_edges": out["n_edges"],
                "n_scorable": out["n_scorable"],
                "n_first_pass_valid": out["n_first_pass_valid"],
                "n_sufficient": out["n_sufficient"],
                "n_insufficient": out["n_insufficient"],
                "reason_counts": out["reason_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
