"""Phase 6A: audited raw-source events -> D/S/P -> production Attention Policy.

Development-only vertical slice. No Human Gold accuracy claim.
P observations are controlled synthetic sensor inputs, never inferred from article wording.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
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
load_repo_env()

from app.cognitive.client import chat_json
from app.config import settings
from eval.live.no_delta_awareness_integration_v2 import estimate_integrated_no_delta_awareness_v2
AUDIT_ARTIFACT = ROOT / "eval/live/results/raw_source_event_audit_v0_1/raw_source_event_audit_v0_1_20260907T205418Z.json"
P_MANIFEST = ROOT / "eval/live/manifest.phase6a_controlled_p_packets.v0.1.yaml"
OUT_DIR = ROOT / "eval/live/results/phase6a_aware_drop_vertical_slice_v0_1"
RUN_VERSION = "phase6a-aware-drop-vertical-slice-v0.1"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"manifest must be a mapping: {path}")
    return data


def _model_chat(model_name: str):
    def _call(messages, **kwargs):
        kwargs.pop("model", None)
        return chat_json(messages, model=model_name, **kwargs)
    return _call


def build_controlled_p_packet(event_id: str, event_text: str, case: dict[str, Any], *, as_of: str) -> dict[str, Any]:
    constituency = dict(case["constituency"])
    condition = str(case["condition"])
    prior = {
        "description": constituency["description"],
        "scope": constituency["scope"],
        "reference_scale": constituency["reference_scale"],
        "reference_size_hint": "controlled-development prior",
        "basis": constituency["basis"],
        "provenance": "Phase 6A controlled development packet",
    }
    common = {
        "event": {"event_id": event_id, "as_of": as_of, "semantic_summary": event_text},
        "constituency_prior": prior,
        "collection_context": {
            "channels_checked": ["controlled_discussion", "controlled_search"],
            "channels_unavailable": [],
            "notes": "Synthetic attention observations for wiring only; not real-world claims.",
        },
        "recent_attention_history": [],
    }
    if condition == "strong_salience":
        observations = _strong_attention_observations(as_of)
    elif condition == "low_salience":
        observations = _low_attention_observations(as_of)
    else:
        raise ValueError(f"unknown P condition: {condition}")
    common["current_attention_evidence"] = observations
    return common


def _strong_attention_observations(as_of: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "human_discussion",
            "window": "last 24h",
            "observation": "Independent discussion is widespread across the controlled constituency and materially above its normal baseline.",
            "source": "phase6a controlled sensor",
            "observed_at": as_of,
            "independence_group": "controlled_humans",
            "quality": "direct",
            "contamination": [],
        },
        {
            "kind": "active_search",
            "window": "last 24h",
            "observation": "Voluntary search activity is several times the constituency's ordinary baseline.",
            "source": "phase6a controlled sensor",
            "observed_at": as_of,
            "independence_group": "controlled_search",
            "quality": "direct",
            "contamination": [],
        },
    ]


def _low_attention_observations(as_of: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "human_discussion",
            "window": "last 24h",
            "observation": "Checked discussion channels show only sparse isolated mentions, far below normal constituency-wide attention levels.",
            "source": "phase6a controlled sensor",
            "observed_at": as_of,
            "independence_group": "controlled_humans",
            "quality": "direct",
            "contamination": [],
        },
        {
            "kind": "active_search",
            "window": "last 24h",
            "observation": "Search activity remains near ordinary baseline with no clear emerging spike.",
            "source": "phase6a controlled sensor",
            "observed_at": as_of,
            "independence_group": "controlled_search",
            "quality": "direct",
            "contamination": [],
        },
    ]


def _validate_inputs(audit: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    events = list(audit.get("events") or [])
    routable = [e for e in events if (e.get("audited_projection") or {}).get("routing_status") == "ROUTABLE"]
    case_ids = set((manifest.get("cases") or {}).keys())
    event_ids = {str(e["event_id"]) for e in routable}
    if case_ids != event_ids:
        raise ValueError(f"P manifest/event mismatch: manifest={sorted(case_ids)} events={sorted(event_ids)}")
    return routable


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
        event_text = str(projection["rendered_event_text"])
        p_case = manifest["cases"][event_id]
        p_packet = build_controlled_p_packet(event_id, event_text, p_case, as_of=as_of)
        result = estimate_integrated_no_delta_awareness_v2(
            event_text,
            p_packet,
            d_chat_fn=d_chat,
            s_chat_fn=flash_chat,
            p_chat_fn=flash_chat,
        )
        rows.append(_row(event, p_case, p_packet, result))
    return _artifact(audit, manifest, rows)


def _row(event: dict[str, Any], p_case: dict[str, Any], p_packet: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    projection = event["audited_projection"]
    return {
        "source_id": event["source_id"],
        "event_id": event["event_id"],
        "routing_status": projection["routing_status"],
        "rendered_event_text": projection["rendered_event_text"],
        "sensor_event_summary_diagnostic_only": projection["sensor_event_summary_diagnostic_only"],
        "admitted_counts": {
            "actors": len(projection.get("actor_objects") or []),
            "actions": len(projection.get("actions_changes") or []),
            "systems": len(projection.get("affected_systems_populations") or []),
            "uncertainties": len(projection.get("uncertainties") or []),
        },
        "rejected_object_count": len(projection.get("rejected_or_unscorable_objects") or []),
        "p_condition": p_case["condition"],
        "p_packet": p_packet,
        "scorable": bool(result.get("scorable")),
        "labels": result.get("labels"),
        "disposition": result.get("disposition"),
        "policy_reason": result.get("reason"),
        "gate_wiring_matches": result.get("gate_wiring_matches"),
        "component_scorable": result.get("component_scorable"),
        "D": result.get("D"),
        "S": result.get("S"),
        "P": result.get("P"),
    }


def _artifact(audit: dict[str, Any], manifest: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    dispositions = Counter(row.get("disposition") for row in rows if row.get("disposition"))
    return {
        "name": "raos-phase6a-aware-drop-vertical-slice-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "run_version": RUN_VERSION,
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "measurement_git_head": git_head(),
        "input_audit_artifact": str(AUDIT_ARTIFACT),
        "input_audit_measurement_head": audit.get("measurement_git_head"),
        "p_manifest": str(P_MANIFEST),
        "p_manifest_name": manifest.get("name"),
        "model_policy": {
            "D": "deepseek-v4-pro",
            "S": "deepseek-v4-flash",
            "P": "deepseek-v4-flash",
            "attention_policy": "production Scheduler via no_delta_awareness_integration_v2",
        },
        "n_events": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_gate_wiring_matches": sum(1 for row in rows if row.get("gate_wiring_matches") is True),
        "disposition_counts": dict(sorted(dispositions.items())),
        "rows": rows,
        "methodology_note": (
            "Development-only end-to-end wiring study. P evidence is synthetic controlled input; "
            "no final action is treated as real-world truth or fresh validation evidence."
        ),
    }


def main() -> None:
    payload = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"phase6a_aware_drop_vertical_slice_v0_1_{payload['measurement_timestamp']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps({
        "n_events": payload["n_events"],
        "n_scorable": payload["n_scorable"],
        "n_gate_wiring_matches": payload["n_gate_wiring_matches"],
        "disposition_counts": payload["disposition_counts"],
        "rows": [
            {
                "event_id": row["event_id"],
                "labels": row["labels"],
                "disposition": row["disposition"],
                "scorable": row["scorable"],
                "gate_wiring_matches": row["gate_wiring_matches"],
                "D_model": ((row.get("D") or {}).get("model_meta") or {}).get("model"),
                "S_model": ((row.get("S") or {}).get("model_meta") or {}).get("model"),
                "P_model": ((row.get("P") or {}).get("model_meta") or {}).get("model"),
            }
            for row in payload["rows"]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
