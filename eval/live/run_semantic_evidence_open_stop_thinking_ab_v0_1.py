"""Run explicit wire-level DeepSeek Pro thinking A/B on RS05 open semantic stop.

Development-only diagnostic. Both conditions use the same RS05 source, open-stop prompt,
schema, provenance rules, and 16K transport headroom. The only intended semantic-model
variable is explicit thinking disabled vs enabled/high. Temperature=0.1 is sent in both
conditions, but DeepSeek documents that temperature is ignored when thinking is enabled.
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
    MAX_TOKENS,
    SemanticExtractionOpenStopBatchV0_1,
    _validate_candidate,
    build_messages,
    prompt_sha256,
)
from eval.live.deepseek_explicit_thinking_transport_v0_1 import chat_json_deepseek_explicit_thinking

OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_open_stop_thinking_ab_v0_1"
SOURCE_ID = "RS05"
REQUIRED_MODEL = "deepseek-v4-pro"
AS_OF = "2026-09-07"
CONDITIONS = [
    {"name": "EXPLICIT_DISABLED", "thinking": "disabled", "reasoning_effort": None},
    {"name": "EXPLICIT_ENABLED_HIGH", "thinking": "enabled", "reasoning_effort": "high"},
]


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except Exception:
        return None


def metrics(batch: dict | None) -> dict[str, int]:
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


def run_condition(source, condition: dict, model: str) -> dict:
    messages = build_messages(source, as_of=AS_OF)
    try:
        parsed, meta = chat_json_deepseek_explicit_thinking(
            messages,
            model=model,
            timeout=180.0,
            thinking=condition["thinking"],
            reasoning_effort=condition["reasoning_effort"],
            max_tokens=MAX_TOKENS,
        )
        obj = SemanticExtractionOpenStopBatchV0_1.model_validate(parsed)
        _validate_candidate(obj, source, as_of=AS_OF)
        batch = obj.model_dump(mode="json")
        return {
            "condition": condition,
            "scorable": True,
            "failure_kind": None,
            "error": None,
            "model_meta": meta,
            **metrics(batch),
            "batch": batch,
        }
    except Exception as exc:
        return {
            "condition": condition,
            "scorable": False,
            "failure_kind": "model_or_schema",
            "error": str(exc)[:2000],
            "model_meta": None,
            **metrics(None),
            "batch": None,
        }


def main() -> None:
    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")
    if settings.llm_model != REQUIRED_MODEL:
        raise SystemExit(f"requires RAOS_LLM_MODEL={REQUIRED_MODEL}; got {settings.llm_model!r}")

    entries = {e["id"]: e for e in load_dev_manifest()["sources"]}
    source = load_manifest_source(entries[SOURCE_ID])
    rows = [run_condition(source, condition, settings.llm_model) for condition in CONDITIONS]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-semantic-evidence-open-stop-thinking-ab-v0.1",
        "status": "DEVELOPMENT_ONLY_MODEL_CAPABILITY_PROBE",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "source_id": SOURCE_ID,
        "as_of": AS_OF,
        "prompt_sha256": prompt_sha256(),
        "model": settings.llm_model,
        "max_tokens": MAX_TOKENS,
        "conditions": rows,
        "methodology_note": (
            "Explicit wire-level thinking A/B. Bypasses RAOS_LLM_THINKING_PROTOCOL so prior configuration ambiguity cannot affect this run. "
            "No prompt/schema/provenance/stopping change between conditions. DeepSeek documents temperature as ignored in thinking mode."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"semantic_evidence_open_stop_thinking_ab_v0_1_{timestamp}.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps({
        "source_id": SOURCE_ID,
        "results": [
            {
                "condition": row["condition"]["name"],
                "scorable": row["scorable"],
                "n_non_event_units": row["n_non_event_units"],
                "n_non_event_supports": row["n_non_event_supports"],
                "statement_chars": row["statement_chars"],
                "support_excerpt_chars": row["support_excerpt_chars"],
                "completion_tokens": (row.get("model_meta") or {}).get("completion_tokens"),
                "finish_reason": (row.get("model_meta") or {}).get("finish_reason"),
                "reasoning_content_present": (row.get("model_meta") or {}).get("reasoning_content_present"),
                "reasoning_content_chars": (row.get("model_meta") or {}).get("reasoning_content_chars"),
            }
            for row in rows
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
