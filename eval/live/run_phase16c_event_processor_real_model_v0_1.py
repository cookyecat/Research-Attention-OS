from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.models  # noqa: F401
from app.db import Base
from app.enums import AttributionType, ClaimType
from app.services.event_processor import process_event
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.ingestion import ingest_text

RUN_VERSION = "phase16c-event-processor-real-model-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase16c_event_processor_real_model_v0_1"


def _extraction(source, statement: str) -> ExtractionResult:
    support_id = f"{source.id}:primary-event"
    return ExtractionResult(
        event_title=source.title,
        event_summary=statement,
        claims=[
            ExtractedClaim(
                text=statement,
                claim_type=ClaimType.FACTUAL,
                attributed_to="source",
                attribution_type=AttributionType.UNKNOWN,
                confidence_extraction=0.9,
                source_span_text=statement,
                semantic_unit_id=support_id,
                semantic_supports=[
                    {
                        "source_id": str(source.id),
                        "support_pointer": "PARA 0001",
                        "support_excerpt": statement,
                    }
                ],
            )
        ],
        current_facts=[statement],
        evidence_maturity=0.7,
    )


def _add(db: Session, title: str, statement: str):
    source = ingest_text(db, statement, title=title)
    result = process_event(db, source, _extraction(source, statement))
    return source, result


def run() -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        source_a, initial = _add(
            db,
            "Acme launches Nimbus API public beta at AtlasConf",
            "Acme launched the Nimbus API public beta at AtlasConf on September 20, 2026.",
        )
        launch_event_id = str(initial.event.id)

        source_b, same = _add(
            db,
            "Reuters reports Acme Nimbus API public-beta launch at AtlasConf",
            "Reuters independently reports that Acme launched the Nimbus API public beta at AtlasConf on September 20, 2026.",
        )

        source_c, different = _add(
            db,
            "Acme opens Nimbus university grant program",
            "Acme opened a separate Nimbus university grant program for research teams on September 20, 2026.",
        )

        source_d, uncertain = _add(
            db,
            "Nimbus update underway",
            "A Nimbus update is underway; more details will be announced soon.",
        )

        result = {
            "run_version": RUN_VERSION,
            "status": "CONTROLLED_REAL_MODEL_COMPLETE",
            "initial_event_id": launch_event_id,
            "cases": {
                "A_SAME_EVENT": {
                    "source_id": str(source_b.id),
                    **same.as_dict(),
                    "expected": "SAME_EVENT",
                    "pass": same.resolution.decision == "SAME_EVENT"
                    and str(same.event.id) == launch_event_id,
                },
                "B_DIFFERENT_EVENT": {
                    "source_id": str(source_c.id),
                    **different.as_dict(),
                    "expected": "DIFFERENT_EVENT",
                    "pass": different.resolution.decision == "DIFFERENT_EVENT"
                    and str(different.event.id) != launch_event_id,
                },
                "C_UNCERTAIN": {
                    "source_id": str(source_d.id),
                    **uncertain.as_dict(),
                    "expected": "UNCERTAIN preferred; DIFFERENT_EVENT acceptable; SAME_EVENT forbidden",
                    "pass": uncertain.resolution.decision in {"UNCERTAIN", "DIFFERENT_EVENT"}
                    and str(uncertain.event.id) != launch_event_id,
                },
            },
            "diagnostics": {
                "same_event_collapsed": str(same.event.id) == launch_event_id,
                "different_event_separate": str(different.event.id) != launch_event_id,
                "uncertain_not_merged": str(uncertain.event.id) != launch_event_id,
                "all_fixed_case_constraints_pass": False,
            },
            "guardrails": [
                "In-memory database only.",
                "Uses configured real LLM transport.",
                "No production database writes.",
                "Cases were preregistered before this run.",
                "No adaptive prompt/case tuning after observing outputs.",
            ],
        }
        result["diagnostics"]["all_fixed_case_constraints_pass"] = all(
            row["pass"] for row in result["cases"].values()
        )
        db.rollback()
        return result


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for name, row in report["cases"].items():
        print(
            name,
            "decision", row["resolution"]["decision"],
            "event", row["event_id"],
            "created", row["created"],
            "pass", row["pass"],
        )
        print("  rationale:", row["resolution"]["rationale"])
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
