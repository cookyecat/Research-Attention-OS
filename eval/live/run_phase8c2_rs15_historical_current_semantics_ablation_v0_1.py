from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
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

from app.cognitive.factory import get_provider
from app.services.pipeline import run_pipeline
from eval.live.phase6b_cognitive_semantics_v0_1 import admitted_epistemic_units
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import (
    _arm_summary,
    _base_world,
    _load_manifest,
)
from eval.live.run_phase8c2_rs15_event_projection_ablation_v0_1 import (
    FrozenExtractionBridge,
    _freeze_semantic_world,
    _hash_units,
    _make_extraction,
)

HIST_AUDIT = ROOT / (
    "eval/live/results/phase7a_v0_2_6_epistemic_audit_v0_1/"
    "phase6b_epistemic_unit_audit_v0_1_20260908T090628Z.json"
)
OUT_DIR = ROOT / "eval/live/results/phase8c2_rs15_historical_current_semantics_ablation_v0_1"
RUN_VERSION = "phase8c2-rs15-historical-current-semantics-ablation-v0.1"
SOURCE_ID = "RS15"
CONDITIONS = ("HIST7_PHASE7A", "CURR_NON_EVENT")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_hist7() -> tuple[list[dict[str, Any]], str]:
    raw = HIST_AUDIT.read_bytes()
    artifact_sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    source = next(row for row in data["sources"] if str(row.get("source_id")) == SOURCE_ID)
    units = admitted_epistemic_units(list(source.get("audits") or []))
    if len(units) != 7:
        raise RuntimeError(f"expected 7 historical admitted units, got {len(units)}")
    return units, artifact_sha


def _run_condition(
    case: dict[str, Any],
    *,
    condition: str,
    units: list[dict[str, Any]],
    repeat: int,
) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(SOURCE_ID, case)
    provider = get_provider()
    extraction = _make_extraction(units, event_title=source.title or SOURCE_ID)
    bridge = FrozenExtractionBridge(
        condition=f"{RUN_VERSION}:{condition}",
        extraction=extraction,
        semantic_hash=_hash_units(units),
    )
    try:
        result = run_pipeline(
            db,
            source.id,
            provider=provider,
            extraction_bridge=bridge,
            reprocess=True,
            allow_watch_creation=False,
        )
        summary = _arm_summary(result, provider, code_by_id)
        summary.update({"condition": condition, "repeat": repeat, "status": "OK", "error": None})
        return summary
    except Exception as exc:
        return {
            "condition": condition,
            "repeat": repeat,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        db.close()
        engine.dispose()


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_fixture_code"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _match_scores(row: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for match in row.get("matches") or []:
        if match.get("fixture_code") in {"Q2", "B2"}:
            out[str(match["fixture_code"])] = float(match.get("score") or 0.0)
    return out


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition": row.get("condition"),
        "repeat": row.get("repeat"),
        "status": row.get("status"),
        "landing": list(_landing(row)) if row.get("status") == "OK" else None,
        "q2_b2_scores": _match_scores(row) if row.get("status") == "OK" else {},
        "delta_content": row.get("delta_content"),
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for condition in CONDITIONS:
        items = [row for row in rows if row.get("condition") == condition]
        landings = [list(_landing(row)) for row in items if row.get("status") == "OK"]
        summary[condition] = {
            "n_runs": len(items),
            "n_ok": sum(row.get("status") == "OK" for row in items),
            "landings": landings,
            "q2_b2_scores": [_match_scores(row) for row in items if row.get("status") == "OK"],
            "stable_landing": landings[0] if landings and all(x == landings[0] for x in landings) else None,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    manifest = _load_manifest()
    case = dict(manifest["cases"][SOURCE_ID])
    measurement_sha = git_head()
    hist7, hist_artifact_sha = _load_hist7()
    frozen_current = _freeze_semantic_world(case)
    curr_units = list(frozen_current["unit_sets"]["N_NON_EVENT"])

    condition_units = {
        "HIST7_PHASE7A": hist7,
        "CURR_NON_EVENT": curr_units,
    }
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for condition in CONDITIONS:
            row = _run_condition(
                case,
                condition=condition,
                units=condition_units[condition],
                repeat=repeat,
            )
            rows.append(row)
            print(json.dumps(_compact_row(row), ensure_ascii=False), flush=True)

    summary = _summarize(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": measurement_sha,
        "source_id": SOURCE_ID,
        "kernel_fixture": case["kernel_fixture"],
        "repeats": args.repeats,
        "historical_audit_artifact": str(HIST_AUDIT.relative_to(ROOT)),
        "historical_audit_sha256": hist_artifact_sha,
        "representations": {
            "HIST7_PHASE7A": {
                "n_units": len(hist7),
                "semantic_sha256": _hash_units(hist7),
                "units": hist7,
            },
            "CURR_NON_EVENT": {
                "n_units": len(curr_units),
                "semantic_sha256": _hash_units(curr_units),
                "units": curr_units,
                "sensor": frozen_current["sensor"],
            },
        },
        "summary": summary,
        "runs": rows,
        "interpretation_guardrails": [
            "Both conditions run through the same current production Locate/Delta/Attention machinery.",
            "The current representation is frozen from one Sensor v0.2.6 plus Auditor v0.1.1 realization and reused across repeats.",
            "The historical representation is the exact seven SUFFICIENT RS15 non-event units from the canonical Phase 7A audit artifact.",
            "This isolates representation composition from historical-vs-current downstream model/runtime differences.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={digest}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
