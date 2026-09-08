"""Run Semantic Evidence Extractor v0.2.6 minimal-sufficient candidate.

Development-only. Uses the preregistered text sources to measure representation cost
and prepare Human Semantic Sufficiency inspection. Does not score D/S/P/A and does not
create fresh validation evidence.
"""

from __future__ import annotations

import argparse
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
from eval.live.semantic_evidence_extractor_v0_2_6 import (
    build_messages,
    estimate_semantic_evidence_v0_2_6,
    invocation_record,
    prompt_sha256,
)

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_dev_v0_2_6"
DEFAULT_SOURCES = ["RS11", "RS05", "RS06", "RS12"]


def git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", default=[], help="Development source id such as RS11")
    parser.add_argument("--preregistered-round", action="store_true", help="Use RS11, RS05, RS06, RS12 in frozen order")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def select_entries(args: argparse.Namespace) -> list[dict]:
    entries = list(load_dev_manifest()["sources"])
    by_id = {entry["id"]: entry for entry in entries}
    if args.preregistered_round and args.source:
        raise SystemExit("use either --preregistered-round or --source, not both")
    selected = DEFAULT_SOURCES if args.preregistered_round else args.source
    if not selected:
        raise SystemExit("select --preregistered-round or at least one --source RSxx")
    unknown = [sid for sid in selected if sid not in by_id]
    if unknown:
        raise SystemExit(f"unknown development source id(s): {unknown}")
    seen = set()
    out = []
    for sid in selected:
        if sid not in seen:
            out.append(by_id[sid])
            seen.add(sid)
    return out


def source_metadata(source) -> dict:
    return {
        "source_id": source.source_id,
        "path": source.path,
        "media_type": source.media_type,
        "git_blob_sha": source.git_blob_sha,
        "file_sha256": source.file_sha256,
        "text_sha256": source.text_sha256,
        "char_count": source.char_count,
        "page_count": source.page_count,
        "published_at": source.published_at,
        "updated_at": source.updated_at,
        "captured_at": source.captured_at,
    }


def representation_metrics(batch: dict | None) -> dict[str, int]:
    if not batch:
        return {
            "n_event_frames": 0,
            "n_non_event_units": 0,
            "n_non_event_supports": 0,
            "statement_chars": 0,
            "support_excerpt_chars": 0,
        }
    units = batch.get("non_event_units", []) or []
    supports = [support for unit in units for support in (unit.get("supports", []) or [])]
    return {
        "n_event_frames": len(batch.get("event_frames", []) or []),
        "n_non_event_units": len(units),
        "n_non_event_supports": len(supports),
        "statement_chars": sum(len(str(unit.get("statement") or "")) for unit in units),
        "support_excerpt_chars": sum(len(str(support.get("support_excerpt") or "")) for support in supports),
    }


def main() -> None:
    args = parse_args()
    sources = [load_manifest_source(entry) for entry in select_entries(args)]

    if args.dry_run:
        rows = []
        for source in sources:
            messages = build_messages(source, as_of=args.as_of)
            message_chars = sum(len(m["content"]) for m in messages)
            rows.append({
                **source_metadata(source),
                "message_chars": message_chars,
                "rough_token_estimate_chars_div_4": round(message_chars / 4),
            })
        print(json.dumps({
            "dry_run": True,
            "n_sources": len(rows),
            "as_of": args.as_of,
            "prompt_sha256": prompt_sha256(),
            "sources": rows,
            "note": "No source truncated; no model called.",
        }, ensure_ascii=False, indent=2))
        return

    load_repo_env()
    from app.config import settings
    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY unavailable after repo .env bootstrap")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = []
    for source in sources:
        result = estimate_semantic_evidence_v0_2_6(source, as_of=args.as_of)
        batch = result.get("batch") if result.get("scorable") else None
        metrics = representation_metrics(batch)
        rows.append({
            "source": source_metadata(source),
            "scorable": bool(result.get("scorable")),
            "failure_kind": result.get("failure_kind"),
            "error": result.get("error"),
            "repair_used": bool(result.get("repair_used")),
            "schema_events": result.get("schema_events") or [],
            "invalid_raw": result.get("invalid_raw"),
            "model_meta": result.get("model_meta"),
            **metrics,
            "batch": batch,
        })

    artifact = {
        "name": "raos-semantic-evidence-development-run-v0.2.6-evidence-complete-cohesion",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": git_head(),
        "as_of": args.as_of,
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "n_sources": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "n_first_pass_valid": sum(1 for row in rows if row["scorable"] and not row["repair_used"]),
        "sources": rows,
        "methodology_note": (
            "Development-only minimal-sufficient semantic compression study. "
            "Same candidate policy across all selected sources; no Auditor scoring and no fresh validation claim."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_dev_v0_2_6_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing development artifact: {out_path}")
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(json.dumps({
        "n_sources": len(rows),
        "n_scorable": artifact["n_scorable"],
        "n_first_pass_valid": artifact["n_first_pass_valid"],
        "results": [{
            "source_id": row["source"]["source_id"],
            "scorable": row["scorable"],
            "failure_kind": row["failure_kind"],
            "repair_used": row["repair_used"],
            "n_event_frames": row["n_event_frames"],
            "n_non_event_units": row["n_non_event_units"],
            "n_non_event_supports": row["n_non_event_supports"],
            "statement_chars": row["statement_chars"],
            "support_excerpt_chars": row["support_excerpt_chars"],
            "completion_tokens": (row.get("model_meta") or {}).get("completion_tokens"),
            "actual_model": (row.get("model_meta") or {}).get("model"),
        } for row in rows],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
