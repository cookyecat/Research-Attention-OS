from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.models  # noqa: F401
from app.db import Base
from app.models.event import Event, EventSource
from app.services.event_processor import process_event
from app.services.extraction import ExtractionResult
from app.services.ingestion import ingest_text

RUN_VERSION = "phase17-jev-event-identity-v0.1"
FIXTURE = ROOT / "eval/live/fixtures/phase17_jev_longitudinal_v0_1.json"
OUT_DIR = ROOT / "eval/live/results/phase17_jev_event_identity_v0_1"


def run() -> dict:
    fixture = json.loads(FIXTURE.read_text())
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    observed = []
    with Session(engine) as db:
        canonical_event_id = None
        for index, epoch in enumerate(fixture["epochs"]):
            source = ingest_text(
                db,
                epoch["source_description"],
                title=f'Jev benchmark {epoch["epoch"]}: {epoch["source_label"]}',
            )
            extraction = ExtractionResult(
                event_title=f'Jev: {epoch["source_label"]}',
                event_summary=epoch["source_description"],
                current_facts=[epoch["source_description"]],
                evidence_maturity=0.6,
            )
            result = process_event(db, source, extraction)
            if canonical_event_id is None:
                canonical_event_id = str(result.event.id)

            expected = "DIFFERENT_EVENT" if index == 0 else epoch["expected_relation_to_event"]
            relation_ok = (
                (index == 0 and result.created)
                or (
                    index > 0
                    and result.resolution.decision == expected
                    and str(result.event.id) == canonical_event_id
                )
            )
            observed.append(
                {
                    "epoch": epoch["epoch"],
                    "source_label": epoch["source_label"],
                    "expected_relation": expected,
                    "observed_relation": result.resolution.decision,
                    "event_id": str(result.event.id),
                    "canonical_event_id": canonical_event_id,
                    "created": result.created,
                    "candidate": result.candidate.model_dump(mode="json"),
                    "rationale": result.resolution.rationale,
                    "relation_ok": bool(relation_ok),
                }
            )

        event_count = int(db.scalar(select(func.count()).select_from(Event)) or 0)
        source_link_count = int(db.scalar(select(func.count()).select_from(EventSource)) or 0)
        canonical_sources = int(
            db.scalar(
                select(func.count())
                .select_from(EventSource)
                .where(EventSource.event_id == result.event.id)
            )
            or 0
        )

        report = {
            "run_version": RUN_VERSION,
            "fixture_contract": fixture["contract"],
            "status": "CONTROLLED_REAL_MODEL_COMPLETE",
            "event_identity_label": fixture["event_identity"]["label"],
            "expected_attention_trajectory": fixture["expected_attention_trajectory"],
            "epochs": observed,
            "diagnostics": {
                "all_identity_expectations_pass": all(row["relation_ok"] for row in observed),
                "final_event_count": event_count,
                "event_source_links": source_link_count,
                "canonical_event_source_count": canonical_sources,
                "all_four_sources_share_one_event": event_count == 1 and canonical_sources == 4,
            },
            "guardrails": [
                "In-memory database only.",
                "Uses configured real LLM transport through Event Processor V1.",
                "No production Event/Attention/WATCH writes.",
                "Fixture was frozen before execution.",
                "This validates Event identity only; Attention trajectory is a future algorithm benchmark gate.",
            ],
        }
        db.rollback()
        return report


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for row in report["epochs"]:
        print(
            row["epoch"],
            "expected", row["expected_relation"],
            "observed", row["observed_relation"],
            "event", row["event_id"],
            "created", row["created"],
            "pass", row["relation_ok"],
        )
        print("  candidate:", row["candidate"]["title"])
        print("  rationale:", row["rationale"])
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
