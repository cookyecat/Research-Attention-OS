"""Phase 6A v0.1.1: preserve evidence context from SUFFICIENT Auditor edges.

Controlled interface repair over v0.1. Frozen D/S/P and Attention Policy semantics are unchanged.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.raw_source_attention_vertical_slice_v0_1 import render_audited_event_with_support_context
from eval.live.run_phase6a_aware_drop_vertical_slice_v0_1 import (
    AUDIT_ARTIFACT,
    P_MANIFEST,
    _load_yaml,
    _model_chat,
    _validate_inputs,
    build_controlled_p_packet,
    git_head,
)
from eval.live.no_delta_awareness_integration_v2 import estimate_integrated_no_delta_awareness_v2

OUT_DIR = ROOT / "eval/live/results/phase6a_aware_drop_vertical_slice_v0_1_1"
RUN_VERSION = "phase6a-aware-drop-vertical-slice-v0.1.1-context-envelope"


def run() -> dict[str, Any]:
    audit = json.loads(AUDIT_ARTIFACT.read_text(encoding="utf-8"))
    manifest = _load_yaml(P_MANIFEST)
    events = _validate_inputs(audit, manifest)
    as_of = str(manifest["as_of"])
    d_chat = _model_chat("deepseek-v4-pro")
    flash_chat = _model_chat("deepseek-v4-flash")
    rows = []

    for event in events:
        projection = event["audited_projection"]
        event_id = str(event["event_id"])
        event_text = render_audited_event_with_support_context(projection, event["audit_edges"])
        p_case = manifest["cases"][event_id]
        p_packet = build_controlled_p_packet(event_id, event_text, p_case, as_of=as_of)
        result = estimate_integrated_no_delta_awareness_v2(
            event_text,
            p_packet,
            d_chat_fn=d_chat,
            s_chat_fn=flash_chat,
            p_chat_fn=flash_chat,
        )
        rows.append({
            "source_id": event["source_id"],
            "event_id": event_id,
            "event_text": event_text,
            "p_condition": p_case["condition"],
            "scorable": bool(result.get("scorable")),
            "labels": result.get("labels"),
            "disposition": result.get("disposition"),
            "policy_reason": result.get("reason"),
            "gate_wiring_matches": result.get("gate_wiring_matches"),
            "component_scorable": result.get("component_scorable"),
            "D": result.get("D"),
            "S": result.get("S"),
            "P": result.get("P"),
        })

    dispositions = Counter(row.get("disposition") for row in rows if row.get("disposition"))
    return {
        "name": "raos-phase6a-aware-drop-vertical-slice-v0.1.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "run_version": RUN_VERSION,
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "input_audit_artifact": str(AUDIT_ARTIFACT),
        "p_manifest": str(P_MANIFEST),
        "model_policy": {
            "D": "deepseek-v4-pro",
            "S": "deepseek-v4-flash",
            "P": "deepseek-v4-flash",
            "attention_policy": "production Scheduler via no_delta_awareness_integration_v2",
        },
        "interface_change": (
            "Downstream audited representation now preserves support excerpts from SUFFICIENT edges only. "
            "Rejected semantic objects remain excluded; no retrieval or provenance repair is performed."
        ),
        "n_events": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_gate_wiring_matches": sum(1 for row in rows if row.get("gate_wiring_matches") is True),
        "disposition_counts": dict(sorted(dispositions.items())),
        "rows": rows,
    }


def main() -> None:
    payload = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"phase6a_aware_drop_vertical_slice_v0_1_1_{payload['measurement_timestamp']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps({
        "n_events": payload["n_events"],
        "n_scorable": payload["n_scorable"],
        "n_gate_wiring_matches": payload["n_gate_wiring_matches"],
        "disposition_counts": payload["disposition_counts"],
        "rows": [
            {"event_id": r["event_id"], "labels": r["labels"], "disposition": r["disposition"]}
            for r in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
