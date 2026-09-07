"""Controlled A/B: baseline real-edge audit vs bounded Evidence Packet v0.1.

The Auditor itself remains v0.1.1. Only the explicitly supplied evidence dossier changes:
primary excerpt -> primary excerpt + full already-cited container + deterministic source metadata.

Development-only; no fresh-validation claim.
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

from eval.live.run_semantic_evidence_auditor_real_edges_v0_1_1 import project_provenance_edges
from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_evidence_auditor_v0_1_1 import (
    audit_semantic_evidence_v0_1_1,
    invocation_record,
)
from eval.live.semantic_evidence_packet_v0_1 import (
    PACKET_VERSION,
    build_evidence_packet_v0_1,
    packet_kind_counts,
    packet_to_auditor_evidence,
)
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_packet_ab_v0_1"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-artifact", type=Path, required=True)
    parser.add_argument("--baseline-audit-artifact", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-edges", type=int, default=None)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))


def _load_pinned_sources(sensor_artifact: dict[str, Any]):
    manifest = load_dev_manifest()
    entries = {str(item["id"]): item for item in manifest["sources"]}
    loaded = {}
    for row in sensor_artifact.get("sources") or []:
        source_meta = row.get("source") or {}
        source_id = str(source_meta.get("source_id") or "")
        if source_id not in entries:
            raise ValueError(f"source {source_id!r} not found in development manifest")
        source = load_manifest_source(entries[source_id])
        if source.path != str(source_meta.get("path") or ""):
            raise ValueError(f"source path mismatch for {source_id}")
        if source.git_blob_sha != str(source_meta.get("git_blob_sha") or ""):
            raise ValueError(f"source git blob mismatch for {source_id}")
        loaded[source_id] = source
    return loaded


def _baseline_by_id(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if baseline.get("name") != "raos-semantic-evidence-auditor-real-edges-v0.1.1":
        raise ValueError("baseline artifact is not the v0.1.1 real-edge audit")
    return {str(row["audit_id"]): row for row in baseline.get("edges") or []}


def main() -> None:
    args = parse_args()
    sensor_path = args.sensor_artifact.expanduser().resolve()
    baseline_path = args.baseline_audit_artifact.expanduser().resolve()
    sensor = _load_json(sensor_path)
    baseline = _load_json(baseline_path)

    if sensor.get("name") != "raos-semantic-evidence-development-run-v0.2.2":
        raise SystemExit("sensor artifact is not v0.2.2")

    edges = project_provenance_edges(sensor)
    baseline_by_id = _baseline_by_id(baseline)
    sources = _load_pinned_sources(sensor)

    if args.max_edges is not None:
        if args.max_edges <= 0:
            raise SystemExit("--max-edges must be positive")
        edges = edges[: args.max_edges]

    missing_baseline = [edge["audit_id"] for edge in edges if edge["audit_id"] not in baseline_by_id]
    if missing_baseline:
        raise SystemExit(f"baseline missing audit ids: {missing_baseline[:5]}")

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    rows = []
    transitions = Counter()
    reason_transitions = Counter()
    packet_totals = Counter()

    for edge in edges:
        source = sources[edge["source_id"]]
        packet, packet_notes = build_evidence_packet_v0_1(
            source=source,
            primary_evidence=edge["evidence"],
        )
        kind_counts = packet_kind_counts(packet)
        packet_totals.update(kind_counts)
        auditor_evidence = packet_to_auditor_evidence(packet)

        result = audit_semantic_evidence_v0_1_1(
            audit_id=edge["audit_id"],
            object_type=edge["object_type"],
            semantic_object=edge["semantic_object"],
            evidence=auditor_evidence,
        )
        audit_result = result.get("result") if result.get("scorable") else None

        base_row = baseline_by_id[edge["audit_id"]]
        base_result = base_row.get("audit_result") or {}
        base_verdict = base_result.get("verdict")
        base_reason = base_result.get("reason_code")
        packet_verdict = audit_result.get("verdict") if audit_result else None
        packet_reason = audit_result.get("reason_code") if audit_result else None

        transitions[f"{base_verdict}->{packet_verdict}"] += 1
        reason_transitions[f"{base_reason}->{packet_reason}"] += 1

        rows.append(
            {
                **edge,
                "baseline_verdict": base_verdict,
                "baseline_reason_code": base_reason,
                "packet_version": PACKET_VERSION,
                "packet_kind_counts": kind_counts,
                "packet_notes": packet_notes,
                "evidence_packet": [item.as_dict() for item in packet],
                "scorable": bool(result.get("scorable")),
                "failure_kind": result.get("failure_kind"),
                "repair_used": bool(result.get("repair_used")),
                "schema_events": result.get("schema_events") or [],
                "model_meta": result.get("model_meta"),
                "audit_result": audit_result,
                "verdict_transition": f"{base_verdict}->{packet_verdict}",
                "reason_transition": f"{base_reason}->{packet_reason}",
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "name": "raos-semantic-evidence-packet-ab-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "sensor_artifact": str(sensor_path),
        "baseline_audit_artifact": str(baseline_path),
        "packet_version": PACKET_VERSION,
        "auditor_invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "n_edges": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_first_pass_valid": sum(1 for row in rows if row["scorable"] and not row["repair_used"]),
        "verdict_transitions": dict(sorted(transitions.items())),
        "reason_transitions": dict(sorted(reason_transitions.items())),
        "packet_item_totals": dict(sorted(packet_totals.items())),
        "edges": rows,
        "methodology_note": (
            "Controlled development A/B. Auditor v0.1.1 is unchanged. Only the explicit evidence "
            "packet changes by adding full already-cited containers and deterministic source metadata. "
            "No adjacent source retrieval, semantic repair, or Human-Gold accuracy claim."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_packet_ab_v0_1_{timestamp}.json"
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
                "verdict_transitions": out["verdict_transitions"],
                "reason_transitions": out["reason_transitions"],
                "packet_item_totals": out["packet_item_totals"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
