"""Run Live Eval against a real OpenAI-compatible model. Not part of ordinary CI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.report import compute_metrics, render_markdown
from eval.live.schema import LiveCase, LiveManifest, gold_status_of


def load_manifest(path: Path) -> LiveManifest:
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("PyYAML is required to load YAML manifests. pip install pyyaml") from exc
        data = yaml.safe_load(raw) or {}
    else:
        data = json.loads(raw)
    return LiveManifest.model_validate(data)


def run_case(case: LiveCase, *, dry_run: bool) -> dict[str, Any]:
    status = gold_status_of(case)
    row: dict[str, Any] = {
        "id": case.id,
        "gold_status": status,
        "source_kind": case.source_kind,
        "cognitive_tasks": case.cognitive_tasks,
        "human_gold": case.human_gold.model_dump() if case.human_gold else None,
        "dry_run": dry_run,
        "model": None,
        "provider_versions": None,
        "prompt_version": None,
        "embedding_model": None,
        "latency_ms": None,
        "tokens": None,
        "cost": None,
        "fallback": None,
        "attention_state": None,
        "kernel_matches": [],
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "match_relevance_types": [],
        "delta_summary": None,
        "claim_texts": [],
        "observation_texts": [],
        "inference_texts": [],
        "delta_rubric": (case.human_gold.delta_rubric if case.human_gold else None),
        "error": None,
    }
    if dry_run or not (case.source.text or case.source.local_file or case.source.url):
        row["skipped"] = True
        row["skip_reason"] = "dry-run or empty source (UNLABELED slot)"
        return row
    # Live path: import backend only when executing for real.
    from app.config import settings
    from app.cognitive.factory import get_provider
    from app.cognitive.versions import (
        EXTRACTOR_VERSION,
        MATCHER_VERSION,
        PIPELINE_VERSION,
        PROMPT_VERSION,
        PROVIDER_VERSION,
    )

    text = case.source.text or ""
    if case.source.local_file:
        text = Path(case.source.local_file).read_text(encoding="utf-8")
    provider = get_provider()
    extraction = provider.extract_information(text, case.source.type or "TEXT", case.source.title)
    row.update(
        {
            "model": settings.llm_model,
            "provider_versions": {
                "extractor": EXTRACTOR_VERSION,
                "matcher": MATCHER_VERSION,
                "provider": PROVIDER_VERSION,
                "pipeline": PIPELINE_VERSION,
            },
            "prompt_version": PROMPT_VERSION,
            "embedding_model": settings.embedding_model,
            "latency_ms": getattr(provider, "last_meta", {}).get("latency_ms"),
            "tokens": {
                "prompt": getattr(provider, "last_meta", {}).get("prompt_tokens"),
                "completion": getattr(provider, "last_meta", {}).get("completion_tokens"),
            },
            "cost": getattr(provider, "last_meta", {}).get("estimated_cost_usd"),
            "fallback": getattr(provider, "fallback_used", False),
            "claim_texts": [c.text for c in extraction.claims],
            "observation_texts": [o.text for o in extraction.observations],
            "inference_texts": [i.text for i in extraction.inferences],
            "skipped": False,
        }
    )
    return row


def write_report(out_dir: Path, summary: dict, rows: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    with (out_dir / "cases.jsonl").open("w", encoding="utf-8") as fh:
        for row in sorted(rows, key=lambda r: r["id"]):
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAOS Live Eval (real model; not CI)")
    parser.add_argument("--manifest", type=Path, default=ROOT / "eval" / "live" / "manifest.example.yaml")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--timestamp", default=None, help="Stable stamp for reproducible reports")
    parser.add_argument("--dry-run", action="store_true", help="Validate manifest and write a report without calling a model")
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest)
    stamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or (ROOT / "eval" / "live" / "results" / stamp)
    rows = [run_case(case, dry_run=args.dry_run) for case in manifest.cases]
    summary = compute_metrics(rows)
    summary["timestamp"] = stamp
    summary["manifest"] = str(args.manifest)
    summary["dry_run"] = args.dry_run
    summary["name"] = manifest.name
    write_report(out_dir, summary, rows)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
