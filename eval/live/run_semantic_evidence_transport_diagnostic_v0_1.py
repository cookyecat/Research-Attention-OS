"""Transport/output observability for Semantic Sensor broadening failures.

Development-only instrumentation. This does NOT change Semantic Sensor semantics,
prompt, schema, source text, or model settings. It records raw provider completion
metadata before JSON parsing so malformed long completions remain attributable.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_source_loader_v0_1 import load_dev_manifest, load_manifest_source
from eval.live.semantic_evidence_extractor_v0_2_2 import (
    build_messages,
    prompt_sha256,
    THINKING,
    REASONING_EFFORT,
    TEMPERATURE,
    TIMEOUT_SECONDS,
)

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_transport_diagnostic_v0_1"


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def select_entries(source_ids: list[str]) -> list[dict]:
    if not source_ids:
        raise SystemExit("select at least one --source RSxx")
    entries = list(load_dev_manifest()["sources"])
    by_id = {entry["id"]: entry for entry in entries}
    unknown = [sid for sid in source_ids if sid not in by_id]
    if unknown:
        raise SystemExit(f"unknown development source id(s): {unknown}")
    seen: set[str] = set()
    out: list[dict] = []
    for sid in source_ids:
        if sid not in seen:
            out.append(by_id[sid])
            seen.add(sid)
    return out


def _thinking_fields(settings) -> dict:
    protocol = (settings.llm_thinking_protocol or "none").strip().lower()
    if protocol in {"deepseek", "thinking"}:
        payload = {"thinking": {"type": THINKING}}
        if THINKING == "enabled" and REASONING_EFFORT:
            payload["reasoning_effort"] = REASONING_EFFORT
        return payload
    return {}


def run_one(source, *, as_of: str, settings) -> dict:
    messages = build_messages(source, as_of=as_of)
    payload = {
        "model": settings.llm_model,
        "temperature": TEMPERATURE,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    payload.update(_thinking_fields(settings))
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:
        return {
            "source_id": source.source_id,
            "status": "transport_error",
            "error": str(exc)[:2000],
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }

    latency_ms = int((time.perf_counter() - started) * 1000)
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = str(message.get("content") or "")
    usage = body.get("usage") or {}

    parse_ok = True
    parse_error = None
    try:
        parsed = json.loads(content.strip())
        if not isinstance(parsed, dict):
            parse_ok = False
            parse_error = "top-level JSON is not an object"
    except Exception as exc:
        parse_ok = False
        parse_error = str(exc)

    return {
        "source_id": source.source_id,
        "status": "ok" if parse_ok else "json_parse_error",
        "latency_ms": latency_ms,
        "finish_reason": choice.get("finish_reason"),
        "actual_model": body.get("model") or settings.llm_model,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "raw_content_chars": len(content),
        "raw_content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "raw_content_tail": content[-1200:],
        "json_parse_ok": parse_ok,
        "json_parse_error": parse_error,
        "source_char_count": source.char_count,
    }


def main() -> None:
    args = parse_args()
    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    sources = [load_manifest_source(entry) for entry in select_entries(args.source)]
    rows = [run_one(source, as_of=args.as_of, settings=settings) for source in sources]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact = {
        "name": "raos-semantic-evidence-transport-diagnostic-v0.1",
        "status": "DEVELOPMENT_ONLY_INSTRUMENTATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "as_of": args.as_of,
        "sensor_prompt_sha256": prompt_sha256(),
        "model": settings.llm_model,
        "provider_base_url": settings.llm_base_url,
        "thinking": THINKING,
        "reasoning_effort": REASONING_EFFORT,
        "temperature": TEMPERATURE,
        "timeout_seconds": TIMEOUT_SECONDS,
        "results": rows,
        "methodology_note": "Raw provider completion observability only; no semantic/schema mechanism changes and no repair attempt.",
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_transport_diagnostic_v0_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing artifact: {out_path}")
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(json.dumps({
        "results": [
            {
                "source_id": row.get("source_id"),
                "status": row.get("status"),
                "finish_reason": row.get("finish_reason"),
                "prompt_tokens": row.get("prompt_tokens"),
                "completion_tokens": row.get("completion_tokens"),
                "raw_content_chars": row.get("raw_content_chars"),
                "json_parse_ok": row.get("json_parse_ok"),
            }
            for row in rows
        ]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
