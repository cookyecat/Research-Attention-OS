"""Run Semantic Evidence Extractor v0.1 on the pinned development corpus.

Development-only. This runner does not score D/S/P/A and does not create fresh
validation evidence. Sources must be selected explicitly unless --all-development
is provided.
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

# Important: load .env before importing app.config/settings or app.cognitive.*.
from eval.live.run_standing_radar_fit_eval import load_repo_env
from eval.live.semantic_source_loader_v0_1 import (
    load_dev_manifest,
    load_manifest_source,
)
from eval.live.semantic_evidence_extractor_v0_1 import (
    build_messages,
    estimate_semantic_evidence_v0_1,
    invocation_record,
    prompt_sha256,
)

DEFAULT_OUT_DIR = ROOT / "eval" / "live" / "results" / "semantic_evidence_dev_v0_1"


def git_head() -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.strip() or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Development source id such as RS02. Repeat for multiple sources.",
    )
    parser.add_argument(
        "--all-development",
        action="store_true",
        help="Explicitly run all 12 development sources.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone.utc).date().isoformat(),
        help="Measurement as-of date/time recorded in output frames.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def select_entries(args: argparse.Namespace) -> list[dict]:
    manifest = load_dev_manifest()
    entries = list(manifest["sources"])
    by_id = {entry["id"]: entry for entry in entries}

    if args.all_development and args.source:
        raise SystemExit("use either --source or --all-development, not both")
    if args.all_development:
        return entries
    if not args.source:
        raise SystemExit("select at least one --source RSxx or use --all-development")

    unknown = [source_id for source_id in args.source if source_id not in by_id]
    if unknown:
        raise SystemExit(f"unknown development source id(s): {unknown}")
    # Preserve caller order but avoid duplicate model calls.
    seen: set[str] = set()
    selected: list[dict] = []
    for source_id in args.source:
        if source_id not in seen:
            selected.append(by_id[source_id])
            seen.add(source_id)
    return selected


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
    }


def main() -> None:
    args = parse_args()
    entries = select_entries(args)
    sources = [load_manifest_source(entry) for entry in entries]

    if args.dry_run:
        rows = []
        for source in sources:
            messages = build_messages(source, as_of=args.as_of)
            message_chars = sum(len(message["content"]) for message in messages)
            rows.append(
                {
                    **source_metadata(source),
                    "message_chars": message_chars,
                    "rough_token_estimate_chars_div_4": round(message_chars / 4),
                }
            )
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "n_sources": len(rows),
                    "as_of": args.as_of,
                    "prompt_sha256": prompt_sha256(),
                    "sources": rows,
                    "note": "Token estimate is only a rough sizing aid; no source was truncated and no model was called.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    load_repo_env()
    from app.config import settings

    if not settings.llm_api_key:
        raise SystemExit(
            "RAOS_LLM_API_KEY is unavailable after repo .env bootstrap; refusing to create a false extraction run."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    measurement_head = git_head()
    rows = []
    for source in sources:
        result = estimate_semantic_evidence_v0_1(source, as_of=args.as_of)
        batch = result.get("batch") if result.get("scorable") else None
        rows.append(
            {
                "source": source_metadata(source),
                "scorable": bool(result.get("scorable")),
                "failure_kind": result.get("failure_kind"),
                "error": result.get("error"),
                "transport_retries": result.get("transport_retries", 0),
                "model_meta": result.get("model_meta"),
                "n_event_frames": len(batch.get("event_frames", [])) if batch else 0,
                "n_non_event_units": len(batch.get("non_event_units", [])) if batch else 0,
                "batch": batch,
            }
        )

    artifact = {
        "name": "raos-semantic-evidence-development-run-v0.1",
        "status": "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION",
        "measurement_timestamp": timestamp,
        "measurement_git_head": measurement_head,
        "as_of": args.as_of,
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
        ),
        "n_sources": len(rows),
        "n_scorable": sum(1 for row in rows if row["scorable"]),
        "sources": rows,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / f"semantic_evidence_dev_v0_1_{timestamp}.json"
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing development artifact: {out_path}")
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    print(
        json.dumps(
            {
                "n_sources": len(rows),
                "n_scorable": artifact["n_scorable"],
                "results": [
                    {
                        "source_id": row["source"]["source_id"],
                        "scorable": row["scorable"],
                        "failure_kind": row["failure_kind"],
                        "n_event_frames": row["n_event_frames"],
                        "n_non_event_units": row["n_non_event_units"],
                        "actual_model": (row.get("model_meta") or {}).get("model"),
                    }
                    for row in rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
