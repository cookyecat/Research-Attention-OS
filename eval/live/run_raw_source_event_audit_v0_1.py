"""Run Phase 6A Auditor over Sensor v0.2.3 Event Frame provenance edges.

Development-only. This audits only RS11/RS12/RS15 event subobjects from a pinned
Sensor artifact, then deterministically projects SUFFICIENT objects downstream.
No retrieval, repair, D/S/P, or attention judgment occurs here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
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
from eval.live.raw_source_attention_vertical_slice_v0_1 import (
    VERTICAL_SLICE_VERSION,
    audit_event_edges,
    build_audited_event_projection,
    project_event_audit_edges,
)
from eval.live.semantic_evidence_auditor_v0_1_1 import invocation_record
DEFAULT_SENSOR_ARTIFACT = ROOT / "eval" / "live" / "results" / "semantic_evidence_dev_v0_2_3" / "semantic_evidence_dev_v0_2_3_20260907T204332Z.json"
OUT_DIR = ROOT / "eval" / "live" / "results" / "raw_source_event_audit_v0_1"
SOURCE_IDS = {"RS11", "RS12", "RS15"}
EXPECTED_SENSOR_NAME = "raos-semantic-evidence-development-run-v0.2.3-minimal-sufficient"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except Exception:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-artifact", type=Path, default=DEFAULT_SENSOR_ARTIFACT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def load_selected_frames(path: Path) -> tuple[dict, list[dict]]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("name") != EXPECTED_SENSOR_NAME:
        raise ValueError("unexpected Sensor artifact identity")
    selected = []
    for row in artifact.get("sources") or []:
        sid = str((row.get("source") or {}).get("source_id") or "")
        if sid not in SOURCE_IDS:
            continue
        if not row.get("scorable"):
            raise ValueError(f"selected Sensor source is not scorable: {sid}")
        for frame in (row.get("batch") or {}).get("event_frames") or []:
            selected.append({"source_id": sid, "frame": frame})
    if {item["source_id"] for item in selected} != SOURCE_IDS:
        raise ValueError("selected sources must all contribute at least one Event Frame")
    return artifact, selected


def main() -> None:
    args = parse_args()
    sensor_path = args.sensor_artifact.expanduser().resolve()
    sensor_artifact, selected = load_selected_frames(sensor_path)

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable")

    all_edges = []
    event_rows = []
    for item in selected:
        source_id = item["source_id"]
        frame = item["frame"]
        edges = project_event_audit_edges(source_id, frame)
        audited = audit_event_edges(edges)
        projection = build_audited_event_projection(frame, audited)
        all_edges.extend(audited)
        event_rows.append({
            "source_id": source_id,
            "event_id": projection["event_id"],
            "sensor_frame": frame,
            "audit_edges": audited,
            "audited_projection": projection,
        })
    verdicts = Counter(
        (row.get("audit_result") or {}).get("verdict")
        for row in all_edges if row.get("audit_result")
    )
    reasons = Counter(
        (row.get("audit_result") or {}).get("reason_code")
        for row in all_edges if row.get("audit_result")
    )
    models = sorted({
        str((row.get("model_meta") or {}).get("model"))
        for row in all_edges if (row.get("model_meta") or {}).get("model")
    })
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-raw-source-event-audit-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "vertical_slice_version": VERTICAL_SLICE_VERSION,
        "input_sensor_artifact": {
            "path": str(sensor_path),
            "measurement_timestamp": sensor_artifact.get("measurement_timestamp"),
            "measurement_git_head": sensor_artifact.get("measurement_git_head"),
            "prompt_sha256": (sensor_artifact.get("invocation") or {}).get("prompt_sha256"),
        },
        "auditor_invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "actual_models": models,
        "n_events": len(event_rows),
        "n_edges": len(all_edges),
        "n_scorable_edges": sum(1 for row in all_edges if row.get("scorable")),
        "n_sufficient": verdicts.get("SUFFICIENT", 0),
        "n_insufficient": verdicts.get("INSUFFICIENT", 0),
        "reason_counts": dict(sorted((k, v) for k, v in reasons.items() if k)),
        "n_routable_events": sum(
            1 for row in event_rows
            if row["audited_projection"]["routing_status"] == "ROUTABLE"
        ),
        "events": event_rows,
        "methodology_note": (
            "Development-only audit of Sensor v0.2.3 Event Frame provenance edges. "
            "Downstream projections contain only SUFFICIENT semantic subobjects; "
            "event.summary is diagnostic-only and never bypasses the Auditor."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"raw_source_event_audit_v0_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite artifact: {out_path}")
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(json.dumps({
        "n_events": artifact["n_events"],
        "n_edges": artifact["n_edges"],
        "n_scorable_edges": artifact["n_scorable_edges"],
        "n_sufficient": artifact["n_sufficient"],
        "n_insufficient": artifact["n_insufficient"],
        "n_routable_events": artifact["n_routable_events"],
        "reason_counts": artifact["reason_counts"],
        "actual_models": artifact["actual_models"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
