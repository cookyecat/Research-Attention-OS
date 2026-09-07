"""Run RS05 DeepSeek Pro open-stop high-thinking probe with full raw observability.

Development-only capability probe. This supersedes the unscorable high-thinking branch of
v0.1 by preserving DeepSeek usage/cache/reasoning diagnostics before final JSON parsing.
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
    SemanticExtractionOpenStopBatchV0_1,
    _validate_candidate,
    build_messages,
    prompt_sha256,
)
from eval.live.deepseek_raw_observability_transport_v0_2 import chat_deepseek_raw_observable

OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_open_stop_thinking_high_v0_2"
SOURCE_ID = "RS05"
REQUIRED_MODEL = "deepseek-v4-pro"
AS_OF = "2026-09-07"
MAX_TOKENS = 32768


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except Exception:
        return None


def metrics(batch: dict | None) -> dict[str, int]:
    if not batch:
        return {
            "n_event_frames": 0,
            "n_non_event_units": 0,
            "n_non_event_supports": 0,
            "statement_chars": 0,
            "support_excerpt_chars": 0,
        }
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
        raise SystemExit(f"requires RAOS_LLM_MODEL={REQUIRED_MODEL}; got {settings.llm_model!r}")

    entries = {entry["id"]: entry for entry in load_dev_manifest()["sources"]}
    source = load_manifest_source(entries[SOURCE_ID])
    messages = build_messages(source, as_of=AS_OF)

    raw = chat_deepseek_raw_observable(
        messages,
        model=settings.llm_model,
        timeout=300.0,
        thinking="enabled",
        reasoning_effort="high",
        max_tokens=MAX_TOKENS,
        response_format="json_object",
    )

    parsed = raw.get("parsed_json")
    batch = None
    schema_valid = False
    schema_error = None
    if parsed is not None:
        try:
            obj = SemanticExtractionOpenStopBatchV0_1.model_validate(parsed)
            _validate_candidate(obj, source, as_of=AS_OF)
            batch = obj.model_dump(mode="json")
            schema_valid = True
        except Exception as exc:
            schema_error = str(exc)[:4000]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    observability = {key: value for key, value in raw.items() if key != "parsed_json"}
    artifact = {
        "name": "raos-semantic-evidence-open-stop-thinking-high-v0.2",
        "status": "DEVELOPMENT_ONLY_MODEL_CAPABILITY_PROBE",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "source_id": SOURCE_ID,
        "as_of": AS_OF,
        "prompt_sha256": prompt_sha256(),
        "model": settings.llm_model,
        "condition": {
            "thinking": "enabled",
            "reasoning_effort": "high",
            "max_tokens": MAX_TOKENS,
            "semantic_stopping": "coverage-complete-open-stop",
        },
        "provider_observability": observability,
        "json_parse_success": parsed is not None,
        "schema_valid": schema_valid,
        "schema_error": schema_error,
        "scorable": bool(schema_valid),
        **metrics(batch),
        "batch": batch,
        "methodology_note": (
            "RS05 DeepSeek Pro explicit high-thinking upper-bound probe. Same open-stop semantic prompt as v0.1; "
            "completion headroom raised to 32768 only to avoid censoring reasoning + final structured output. "
            "Provider usage/cache/reasoning metadata is captured before JSON parsing. Reasoning text is not persisted."
        ),
        "comparison_reference": {
            "artifact": "semantic_evidence_open_stop_thinking_ab_v0_1_20260907T190134Z.json",
            "explicit_disabled_units": 36,
            "explicit_disabled_completion_tokens": 8917,
            "explicit_disabled_finish_reason": "stop",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"semantic_evidence_open_stop_thinking_high_v0_2_{timestamp}.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    provider = observability.get("provider_response") or {}
    usage = observability.get("usage") or {}
    reasoning = observability.get("reasoning_observability") or {}
    final = observability.get("final_content_observability") or {}
    summary = {
        "source_id": SOURCE_ID,
        "scorable": artifact["scorable"],
        "json_parse_success": artifact["json_parse_success"],
        "schema_valid": artifact["schema_valid"],
        "finish_reason": provider.get("finish_reason"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "prompt_cache_hit_tokens": usage.get("prompt_cache_hit_tokens"),
        "prompt_cache_miss_tokens": usage.get("prompt_cache_miss_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": usage.get("reasoning_tokens"),
        "visible_output_tokens_derived": usage.get("visible_output_tokens_derived"),
        "reasoning_content_chars": reasoning.get("chars"),
        "final_content_chars": final.get("chars"),
        "n_non_event_units": artifact["n_non_event_units"],
        "n_non_event_supports": artifact["n_non_event_supports"],
        "statement_chars": artifact["statement_chars"],
        "support_excerpt_chars": artifact["support_excerpt_chars"],
        "latency_ms": observability.get("latency_ms"),
    }
    print(f"wrote {out}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
