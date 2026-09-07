"""Run the DeepSeek Pro RS05 open-semantic-stop upper-bound probe.

Development-only. This is a diagnostic capability experiment, not a production Sensor
revision and not fresh validation evidence.
"""
from __future__ import annotations

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
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source
from eval.live.semantic_evidence_open_stop_probe_v0_1 import (
    estimate_open_stop,
    invocation_record,
)
from eval.live.open_stop_chat_transport_v0_1 import chat_json_with_max_tokens

OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_open_stop_probe_v0_1"
SOURCE_ID = "RS05"
REQUIRED_MODEL = "deepseek-v4-pro"
AS_OF = "2026-09-07"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except Exception:
        return None


def representation_metrics(batch: dict | None) -> dict[str, int]:
    if not batch:
        return {"n_event_frames": 0, "n_non_event_units": 0, "n_non_event_supports": 0, "statement_chars": 0, "support_excerpt_chars": 0}
    units = batch.get("non_event_units", []) or []
    supports = [s for u in units for s in (u.get("supports", []) or [])]
    return {
        "n_event_frames": len(batch.get("event_frames", []) or []),
        "n_non_event_units": len(units),
        "n_non_event_supports": len(supports),
        "statement_chars": sum(len(str(u.get("statement") or "")) for u in units),
        "support_excerpt_chars": sum(len(str(s.get("support_excerpt") or "")) for s in supports),
    }


def main() -> None:
    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")
    if settings.llm_model != REQUIRED_MODEL:
        raise SystemExit(
            f"this preregistered probe requires RAOS_LLM_MODEL={REQUIRED_MODEL}; got {settings.llm_model!r}"
        )

    entries = {e["id"]: e for e in load_dev_manifest()["sources"]}
    source = load_manifest_source(entries[SOURCE_ID])
    result = estimate_open_stop(source, as_of=AS_OF, chat_fn=chat_json_with_max_tokens)
    batch = result.get("batch") if result.get("scorable") else None
    metrics = representation_metrics(batch)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-semantic-evidence-open-stop-upper-bound-probe-v0.1",
        "status": "DEVELOPMENT_ONLY_MODEL_CAPABILITY_PROBE",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "source_id": SOURCE_ID,
        "as_of": AS_OF,
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "scorable": bool(result.get("scorable")),
        "failure_kind": result.get("failure_kind"),
        "error": result.get("error"),
        "repair_used": bool(result.get("repair_used")),
        "schema_events": result.get("schema_events") or [],
        "model_meta": result.get("model_meta"),
        **metrics,
        "batch": batch,
        "methodology_note": (
            "RS05 DeepSeek Pro open-stop capability probe. Numeric semantic-unit target/cap removed; "
            "transport max_tokens raised to 16384 only to avoid censoring the upper-bound measurement. "
            "No repair is attempted, preserving first-pass diagnostic purity."
        ),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"semantic_evidence_open_stop_probe_v0_1_{timestamp}.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "source_id": SOURCE_ID,
        "scorable": artifact["scorable"],
        "failure_kind": artifact["failure_kind"],
        "n_event_frames": artifact["n_event_frames"],
        "n_non_event_units": artifact["n_non_event_units"],
        "n_non_event_supports": artifact["n_non_event_supports"],
        "statement_chars": artifact["statement_chars"],
        "support_excerpt_chars": artifact["support_excerpt_chars"],
        "completion_tokens": (artifact.get("model_meta") or {}).get("completion_tokens"),
        "finish_reason": (artifact.get("model_meta") or {}).get("finish_reason"),
        "max_tokens": (artifact.get("model_meta") or {}).get("max_tokens"),
        "actual_model": (artifact.get("model_meta") or {}).get("model"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
