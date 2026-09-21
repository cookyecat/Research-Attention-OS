from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.cognitive.research_aligned_contract import canonical_semantic_units
from app.db import SessionLocal
from app.models.acquisition import AcquisitionObservation, InformationSnapshot
from app.models.source import Source
from eval.live.phase8c2_production_sensor_bridge_v0_1 import (
    SemanticSensorProductionBridgeV0_1,
)

RUN_VERSION = "phase17-jev-semantic-hydration-repair-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_semantic_hydration_v0_1"


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _event_units(diagnostics: dict) -> list[dict]:
    rows: list[dict] = []
    sources = diagnostics.get("sources") or []
    if not sources:
        return rows
    for event in (sources[0] or {}).get("events") or []:
        for unit in (event or {}).get("admitted_semantic_units") or []:
            if isinstance(unit, dict) and unit.get("unit_id"):
                rows.append(unit)
    return rows


def _latest_full_artifact() -> Path:
    rows = sorted(
        p for p in OUT_DIR.glob("phase17_jev_semantic_hydration_v0.1_full_*.json")
        if "repaired" not in p.name
    )
    if not rows:
        raise RuntimeError("No full hydration artifact found")
    return rows[-1]


def _source_for_row(db, row: dict) -> Source:
    source_id = row.get("source_id")
    if not source_id:
        raise RuntimeError(f"Hydration row {row.get('ordinal')} has no source_id")
    source = db.get(Source, UUID(source_id))
    if source is None:
        raise RuntimeError(f"Source not found: {source_id}")
    return source


def _earliest_observed_at(db, snapshot_id: str | None):
    if not snapshot_id:
        return None
    snapshot = db.get(InformationSnapshot, UUID(snapshot_id))
    if snapshot is None:
        return None
    return db.execute(
        select(AcquisitionObservation.observed_at)
        .where(AcquisitionObservation.external_item_id == snapshot.external_item_id)
        .order_by(AcquisitionObservation.observed_at.asc(), AcquisitionObservation.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def run(base_path: Path, max_attempts: int = 2) -> dict:
    base_path = base_path.resolve()
    base = json.loads(base_path.read_text())
    items = [dict(row) for row in base["items"]]
    bridge = SemanticSensorProductionBridgeV0_1()
    bridge_snapshot = bridge.execution_snapshot()
    repaired = []

    db = SessionLocal()
    try:
        for row in items:
            if row.get("status") == "OK":
                continue
            source = _source_for_row(db, row)
            last_exc = None
            success = None
            for attempt in range(1, max_attempts + 1):
                try:
                    bridged = bridge.extract(source, [])
                    units = canonical_semantic_units(bridged.extraction)
                    success = {
                        **row,
                        "status": "OK",
                        "error": None,
                        "semantic_units": units,
                        "event_units": _event_units(bridged.diagnostics),
                        "diagnostics": bridged.diagnostics,
                        "repair": {
                            "run_version": RUN_VERSION,
                            "attempt": attempt,
                            "base_status": row.get("status"),
                            "base_error": row.get("error"),
                        },
                    }
                    break
                except Exception as exc:
                    last_exc = exc
            if success is None:
                raise RuntimeError(
                    f"Repair failed for Source {source.id} after {max_attempts} attempts: "
                    f"{type(last_exc).__name__}: {last_exc}"
                )
            row.clear()
            row.update(success)
            repaired.append(str(source.id))
            print(
                "REPAIRED",
                source.id,
                "semantic_units",
                len(row["semantic_units"]),
                "event_units",
                len(row["event_units"]),
            )
    finally:
        db.close()

    ok = [row for row in items if row.get("status") == "OK"]
    summary = {
        "ok": len(ok),
        "failed": sum(row.get("status") == "FAILED" for row in items),
        "no_source": sum(row.get("status") == "NO_SOURCE" for row in items),
        "with_semantic_units": sum(bool(row.get("semantic_units")) for row in ok),
        "with_event_units": sum(bool(row.get("event_units")) for row in ok),
        "semantic_unit_total": sum(len(row.get("semantic_units") or []) for row in ok),
        "event_unit_total": sum(len(row.get("event_units") or []) for row in ok),
        "repaired_rows": len(repaired),
    }
    return {
        **base,
        "run_version": RUN_VERSION,
        "status": "EVAL_ONLY_SEMANTIC_HYDRATION_REPAIRED",
        "base_artifact": str(base_path.relative_to(ROOT)),
        "repair_bridge_execution": bridge_snapshot,
        "repair_policy": {
            "only_retry_non_OK_rows": True,
            "max_attempts_per_failed_row": max_attempts,
            "prompts_or_contracts_changed": False,
        },
        "summary": summary,
        "items": items,
        "repaired_source_ids": repaired,
        "guardrails": list(base.get("guardrails") or [])
        + [
            "Original successful rows are preserved byte-semantically as loaded JSON objects.",
            "Only failed/no-source rows are eligible for bounded retry.",
            "Retries use the same current production Sensor + Auditor bridge without prompt tuning.",
            "A repaired artifact is new immutable eval evidence; the original failed artifact is not overwritten.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-artifact", type=Path, default=None)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()

    base = args.base_artifact or _latest_full_artifact()
    report = run(base, max_attempts=args.max_attempts)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / (
        f"{RUN_VERSION.replace('-', '_')}_repaired_full_{stamp}.json"
    )
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("SUMMARY=" + json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
