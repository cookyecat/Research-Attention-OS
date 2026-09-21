from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.cognitive.client import chat_json
from app.services.benchmark_event_gold_projector import (
    project_audited_units_to_benchmark_event,
)

RUN_VERSION = "phase17-jev-event-gold-semantic-projection-v0.2"
HYDRATION_DIR = ROOT / "eval/live/results/phase17_jev_semantic_hydration_v0_1"
FIXTURE = ROOT / "eval/live/fixtures/phase17_jev_longitudinal_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_event_gold_projection_v0_2"


def _latest_repaired_hydration() -> Path:
    rows = sorted(HYDRATION_DIR.glob("*repaired_full_*.json"))
    if not rows:
        raise RuntimeError(
            "No repaired full hydration artifact found. "
            "Run run_phase17_jev_semantic_hydration_repair_v0_1.py first."
        )
    return rows[-1]


def run(
    hydration_path: Path,
    limit: int | None = None,
    max_attempts: int = 2,
) -> dict:
    hydration_path = hydration_path.resolve()
    hydration = json.loads(hydration_path.read_text())
    fixture = json.loads(FIXTURE.read_text())

    if hydration["summary"]["failed"] or hydration["summary"]["no_source"]:
        raise RuntimeError("Projection requires a fully repaired hydration artifact")

    items = list(hydration["items"])
    if limit is not None:
        items = items[:limit]

    event_identity = dict(fixture["event_identity"])
    projected_rows = []

    for index, row in enumerate(items, start=1):
        units = list(row.get("semantic_units") or [])
        result = None
        last_exc = None
        attempt_used = 0
        for attempt in range(1, max_attempts + 1):
            try:
                result = project_audited_units_to_benchmark_event(
                    event_identity=event_identity,
                    audited_semantic_units=units,
                    chat_fn=chat_json,
                )
                attempt_used = attempt
                break
            except Exception as exc:
                last_exc = exc
        if result is None:
            raise RuntimeError(
                f"Event-Gold projection failed for Source {row.get('source_id')} "
                f"after {max_attempts} attempts: {type(last_exc).__name__}: {last_exc}"
            )
        by_id = {
            str(unit.get("unit_id")): unit
            for unit in units
            if str(unit.get("unit_id") or "").strip()
        }
        projected_units = [
            by_id[unit_id]
            for unit_id in result.projected_unit_ids
        ]
        out = {
            **row,
            "projection_contract": result.contract,
            "projection_selections": [
                selection.model_dump(mode="json")
                for selection in result.selections
            ],
            "projected_unit_ids": list(result.projected_unit_ids),
            "projected_units": projected_units,
            "projection_summary": {
                "input_audited_units": len(units),
                "projected_event_units": len(projected_units),
                "excluded_units": len(units) - len(projected_units),
                "attempt_used": attempt_used,
            },
        }
        projected_rows.append(out)
        print(
            index,
            "/",
            len(items),
            "source",
            row.get("source_id"),
            "audited",
            len(units),
            "projected",
            len(projected_units),
        )

    return {
        "run_version": RUN_VERSION,
        "status": "EVAL_ONLY_EVENT_GOLD_SEMANTIC_PROJECTION_COMPLETE",
        "hydration_artifact": str(hydration_path.relative_to(ROOT)),
        "fixture_contract": fixture["contract"],
        "frozen_event_identity": event_identity,
        "scope": {
            "items": len(projected_rows),
            "canonical_writes": False,
            "topology_writes": False,
            "attention_writes": False,
            "benchmark_event_gold_assumed": True,
        },
        "summary": {
            "items": len(projected_rows),
            "input_audited_units": sum(
                row["projection_summary"]["input_audited_units"]
                for row in projected_rows
            ),
            "projected_event_units": sum(
                row["projection_summary"]["projected_event_units"]
                for row in projected_rows
            ),
            "excluded_units": sum(
                row["projection_summary"]["excluded_units"]
                for row in projected_rows
            ),
            "zero_projected_rows": sum(
                row["projection_summary"]["projected_event_units"] == 0
                for row in projected_rows
            ),
        },
        "items": projected_rows,
        "guardrails": [
            "The Jev coarse Event identity is frozen benchmark Event Gold.",
            "Projector can only classify existing audited unit_ids; it cannot create facts.",
            "Projection is eval-only and does not create Event membership or topology authority.",
            "All audited semantic units are classified exactly once as IN_EVENT or OUT_OF_EVENT.",
            "Zero projected units are legal and mean no new world-state semantic content from that Source.",
            "Human Gold Attention labels are not supplied to the projector.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hydration-artifact", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()

    hydration_path = args.hydration_artifact or _latest_repaired_hydration()
    report = run(
        hydration_path,
        limit=args.limit,
        max_attempts=args.max_attempts,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_n{args.limit}" if args.limit is not None else "_full"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / (
        f"{RUN_VERSION.replace('-', '_')}{suffix}_{stamp}.json"
    )
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    print("SUMMARY=" + json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
