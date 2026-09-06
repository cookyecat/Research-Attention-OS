"""Run Standing Radar Fit (D) estimator eval. Not part of ordinary CI.

Does not call production scheduler. Does not estimate S or P.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
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

DEFAULT_MANIFEST = ROOT / "eval" / "live" / "manifest.standing_radar_fit_human_gold.v1.yaml"
DEFAULT_OUT = ROOT / "eval" / "live" / "results" / "standing_radar_fit_v1_first_run.json"


def load_repo_env(root: Path = ROOT) -> None:
    """Load unset keys from repo .env so the existing Settings path sees them."""
    path = root / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def git_head(root: Path = ROOT) -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.strip() or None


def load_fit_manifest(path: Path) -> dict[str, Any]:
    import yaml
    from pydantic import BaseModel, ConfigDict, Field

    class FitCase(BaseModel):
        model_config = ConfigDict(extra="ignore")

        id: str
        event: str
        gold_status: str | None = None
        label_provenance: str | None = None
        standing_radar_fit: str | None = None

    class FitManifest(BaseModel):
        model_config = ConfigDict(extra="ignore")

        name: str | None = None
        profile: str | None = None
        variable: str | None = None
        semantic_contract: str | None = None
        cases: list[FitCase] = Field(default_factory=list)

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return FitManifest.model_validate(data).model_dump()


def run_manifest(
    manifest_path: Path,
    *,
    score: bool,
    dry_run: bool,
    chat_fn=None,
) -> dict[str, Any]:
    from eval.live.standing_radar_fit import (
        ESTIMATOR_VERSION,
        PROMPT_VERSION,
        build_messages,
        compute_standing_radar_fit_metrics,
        estimate_standing_radar_fit,
        invocation_record,
        load_standing_radar_profile,
        prompt_sha256,
    )

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
            "matched_interests": [],
            "reason": None,
            "failure_kind": None,
            "error": None,
            "transport_retries": 0,
            "model_meta": None,
        }
        if dry_run:
            messages = build_messages(event, profile)
            row["dry_run"] = True
            row["prompt_chars"] = sum(len(m["content"]) for m in messages)
            rows.append(row)
            continue
        estimate = estimate_standing_radar_fit(event, profile=profile, chat_fn=chat_fn)
        row["scorable"] = bool(estimate["scorable"])
        row["prediction"] = estimate["standing_radar_fit"]
        row["matched_interests"] = estimate["matched_interests"]
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Standing Radar Fit (D) estimator eval")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-score", action="store_true", help="Predict without reading gold labels")
    args = parser.parse_args(argv)
    payload = run_manifest(args.manifest, score=not args.no_score, dry_run=args.dry_run)
    write_artifact(payload, args.out)
    print(f"wrote {args.out}")
    metrics = payload.get("metrics") or {}
    if metrics:
        print(
            json.dumps(
                {
                    "n_scored": metrics.get("n_scored"),
                    "exact_accuracy": metrics.get("exact_accuracy"),
                    "balanced_accuracy": metrics.get("balanced_accuracy"),
                    "in_recall": metrics.get("in_recall"),
                    "out_recall": metrics.get("out_recall"),
                    "metrics_pass": metrics.get("metrics_pass"),
                    "n_technical_failures": payload.get("n_technical_failures"),
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
