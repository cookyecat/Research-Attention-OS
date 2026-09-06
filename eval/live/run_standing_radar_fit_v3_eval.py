"""Run Standing Radar Fit (D) estimator v3 eval. Not part of ordinary CI."""

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

from eval.live.run_standing_radar_fit_eval import git_head, load_fit_manifest, load_repo_env
from eval.live.standing_radar_fit import compute_standing_radar_fit_metrics
from eval.live.standing_radar_fit_v3 import (
    ESTIMATOR_VERSION,
    PROMPT_VERSION,
    estimate_standing_radar_fit_v3,
    invocation_record,
    load_standing_radar_profile,
    prompt_sha256,
)

DEFAULT_MANIFEST = ROOT / "eval" / "live" / "manifest.standing_radar_fit_v3_final_fresh_human_gold.yaml"
DEFAULT_OUT = ROOT / "eval" / "live" / "results" / "standing_radar_fit_v3_final_fresh_first_run.json"


def run_manifest_v3(
    manifest_path: Path,
    *,
    score: bool,
    dry_run: bool,
    chat_fn=None,
) -> dict[str, Any]:
    load_repo_env()
    from app.config import settings

    profile = load_standing_radar_profile()
    manifest = load_fit_manifest(manifest_path)
    rows: list[dict[str, Any]] = []
    technical_failures: list[dict[str, Any]] = []

    for case in manifest["cases"]:
        event = case["event"]
        raw_gold = case.get("standing_radar_fit") if score else None
        gold = raw_gold if raw_gold in {"IN", "OUT"} else None
        row: dict[str, Any] = {
            "case_id": case["id"],
            "gold": gold if score else None,
            "gold_status": case.get("gold_status"),
            "label_provenance": case.get("label_provenance"),
            "prediction": None,
            "correct": None,
            "scorable": False,
            "substantive_anchors": [],
            "matched_clauses": [],
            "reason": None,
            "failure_kind": None,
            "error": None,
            "transport_retries": 0,
            "model_meta": None,
        }
        if dry_run:
            rows.append(row)
            continue

        estimate = estimate_standing_radar_fit_v3(event, profile=profile, chat_fn=chat_fn)
        row["scorable"] = bool(estimate["scorable"])
        row["prediction"] = estimate["standing_radar_fit"]
        row["substantive_anchors"] = estimate["substantive_anchors"]
        row["matched_clauses"] = estimate["matched_clauses"]
        row["reason"] = estimate["reason"]
        row["failure_kind"] = estimate["failure_kind"]
        row["error"] = estimate["error"]
        row["transport_retries"] = estimate["transport_retries"]
        row["model_meta"] = estimate["model_meta"]

        if row["scorable"] and gold in {"IN", "OUT"}:
            row["correct"] = row["prediction"] == gold
        elif estimate["failure_kind"]:
            technical_failures.append(
                {
                    "case_id": case["id"],
                    "failure_kind": estimate["failure_kind"],
                    "error": estimate["error"],
                    "transport_retries": estimate["transport_retries"],
                }
            )
        rows.append(row)

    metrics = compute_standing_radar_fit_metrics(rows) if score and not dry_run else None
    models = sorted(
        {
            str((row.get("model_meta") or {}).get("model"))
            for row in rows
            if (row.get("model_meta") or {}).get("model")
        }
    )
    return {
        "name": manifest.get("name"),
        "estimator_version": ESTIMATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_sha256(),
        "estimator_freeze_commit": git_head(),
        "measurement_timestamp": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "manifest": str(manifest_path),
        "dry_run": dry_run,
        "scored": bool(score and not dry_run),
        "invocation": invocation_record(
            requested_model=settings.llm_model,
            provider_base_url=settings.llm_base_url,
            thinking_protocol=settings.llm_thinking_protocol,
        ),
        "actual_models": models,
        "cases": rows,
        "metrics": metrics,
        "technical_failures": technical_failures,
        "n_cases": len(rows),
        "n_technical_failures": len(technical_failures),
    }


def write_artifact(payload: dict[str, Any], path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing first-run artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standing Radar Fit (D) estimator v3 final fresh eval")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-score", action="store_true")
    args = parser.parse_args(argv)

    payload = run_manifest_v3(args.manifest, score=not args.no_score, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps({"n_cases": payload["n_cases"], "prompt_sha256": payload["prompt_sha256"]}, indent=2))
        return 0

    write_artifact(payload, args.out)
    print(f"wrote {args.out}")
    if payload.get("metrics"):
        print(json.dumps(payload["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
