from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from app.models.acquisition import (
    AcquisitionObservation,
    ExternalInformationItem,
    InformationSnapshot,
)
from app.models.source import Source
from eval.live.phase8c2_production_sensor_bridge_v0_1 import (
    SemanticSensorProductionBridgeV0_1,
)

RUN_VERSION = "phase17-jev-semantic-hydration-v0.1"
TRACE = ROOT / "eval/live/fixtures/phase17_jev_observed_world_trace_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_semantic_hydration_v0_1"


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _representative_source(db, item_id: UUID):
    snapshots = db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.external_item_id == item_id)
        .order_by(InformationSnapshot.captured_at.asc(), InformationSnapshot.id.asc())
    ).scalars().all()
    if not snapshots:
        return None, None

    first_fallback = None
    for snap in snapshots:
        source = db.get(Source, snap.raos_source_id)
        if source is None:
            continue
        if first_fallback is None:
            first_fallback = (snap, source)
        if str(source.content_text or "").strip():
            return snap, source
    return first_fallback or (None, None)


def _earliest_observed_at(db, item_id: UUID):
    return db.execute(
        select(AcquisitionObservation.observed_at)
        .where(AcquisitionObservation.external_item_id == item_id)
        .order_by(AcquisitionObservation.observed_at.asc(), AcquisitionObservation.id.asc())
        .limit(1)
    ).scalar_one_or_none()


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


def run(limit: int | None = None) -> dict:
    trace = json.loads(TRACE.read_text())
    items = list(trace["items"])
    if limit is not None:
        items = items[:limit]

    bridge = SemanticSensorProductionBridgeV0_1()
    bridge_snapshot = bridge.execution_snapshot()
    results = []

    db = SessionLocal()
    try:
        for index, trace_row in enumerate(items, start=1):
            item_id = UUID(trace_row["external_item_id"])
            item = db.get(ExternalInformationItem, item_id)
            snap, source = _representative_source(db, item_id)
            record = {
                "ordinal": index,
                "external_item_id": str(item_id),
                "trace_published_at": trace_row.get("published_at"),
                "title": trace_row.get("title"),
                "item_type": trace_row.get("item_type"),
                "domain": trace_row.get("domain"),
                "source_selection_policy": (
                    "earliest captured snapshot whose Source has non-empty content_text; "
                    "fallback earliest available snapshot"
                ),
                "source_id": str(source.id) if source is not None else None,
                "snapshot_id": str(snap.id) if snap is not None else None,
                "snapshot_content_hash": snap.content_hash if snap is not None else None,
                "source_content_hash": source.content_hash if source is not None else None,
                "source_published_at": _iso(source.published_at) if source is not None else None,
                "source_ingested_at": _iso(source.ingested_at) if source is not None else None,
                "earliest_observed_at": _iso(_earliest_observed_at(db, item_id)),
            }
            if source is None:
                record.update(
                    {
                        "status": "NO_SOURCE",
                        "error": "No Source-backed snapshot found.",
                        "semantic_units": [],
                        "event_units": [],
                    }
                )
                results.append(record)
                print(index, "/", len(items), "NO_SOURCE", trace_row.get("title"))
                continue

            try:
                bridged = bridge.extract(source, [])
                units = canonical_semantic_units(bridged.extraction)
                event_units = _event_units(bridged.diagnostics)
                record.update(
                    {
                        "status": "OK",
                        "error": None,
                        "semantic_units": units,
                        "event_units": event_units,
                        "diagnostics": bridged.diagnostics,
                    }
                )
                print(
                    index,
                    "/",
                    len(items),
                    "OK",
                    "units", len(units),
                    "event_units", len(event_units),
                    str(source.id),
                )
            except Exception as exc:
                record.update(
                    {
                        "status": "FAILED",
                        "error": f"{type(exc).__name__}: {exc}",
                        "semantic_units": [],
                        "event_units": [],
                    }
                )
                print(
                    index,
                    "/",
                    len(items),
                    "FAILED",
                    type(exc).__name__,
                    str(exc)[:240],
                )
            results.append(record)
    finally:
        db.close()

    ok = [row for row in results if row["status"] == "OK"]
    with_units = [row for row in ok if row["semantic_units"]]
    with_event_units = [row for row in ok if row["event_units"]]
    return {
        "run_version": RUN_VERSION,
        "status": "EVAL_ONLY_SEMANTIC_HYDRATION_COMPLETE",
        "trace_contract": trace["contract"],
        "bridge_execution": bridge_snapshot,
        "scope": {
            "requested_items": len(items),
            "full_trace_items": len(trace["items"]),
            "canonical_writes": False,
            "topology_writes": False,
            "attention_writes": False,
        },
        "summary": {
            "ok": len(ok),
            "failed": sum(row["status"] == "FAILED" for row in results),
            "no_source": sum(row["status"] == "NO_SOURCE" for row in results),
            "with_semantic_units": len(with_units),
            "with_event_units": len(with_event_units),
            "semantic_unit_total": sum(len(row["semantic_units"]) for row in ok),
            "event_unit_total": sum(len(row["event_units"]) for row in ok),
        },
        "items": results,
        "guardrails": [
            "Read-only canonical DB access for Source/Snapshot retrieval.",
            "Semantic Sensor + Auditor are invoked directly through the production bridge.",
            "No pipeline, AnalysisRun, Event topology, EventRevision, AttentionPlan, WATCH or Delivery writes.",
            "Hydrated units are benchmark/eval evidence only.",
            "Representative source version is frozen by deterministic earliest-nonempty snapshot policy.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    report = run(limit=args.limit)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_n{args.limit}" if args.limit is not None else "_full"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}{suffix}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("SUMMARY=" + json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
