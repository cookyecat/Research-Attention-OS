from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

import app.models  # noqa: F401
from app.cognitive.client import chat_json
from app.db import Base
from app.models.event import Event, EventMembershipAssertion
from app.models.source import Source
from app.services.event_observation import EventObservationV01
from app.services.event_state_fact_delta import (
    CurrentFactV01,
    SemanticFactStateV01,
    apply_fact_delta,
    decide_fact_delta,
    make_fact_state,
)

RUN_VERSION = "phase17-state-fact-delta-real-model-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase17_state_fact_delta_real_model_v0_1"
def _db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def _event(db: Session, label: str) -> Event:
    row = Event(
        title="Jev model launch / emergence and early validation episode",
        event_type="MODEL_LAUNCH_EARLY_VALIDATION",
        actors=["TypeSafe AI / Jev authors and ecosystem participants"],
        action="launch, explain, test, and early-validate Jev",
        object="Jev model",
        summary=f"Controlled Phase17 fact-delta case: {label}",
        confidence=0.5,
        status="CANDIDATE",
    )
    db.add(row)
    db.flush()
    return row


def _source(db: Session, label: str) -> Source:
    row = Source(
        source_type="TEXT",
        title=label,
        content_text=label,
        fingerprint=f"phase17-fact-real-{uuid4()}",
        ingestion_method="CONTROLLED_EVAL",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    return row
def _member(db: Session, event: Event, source: Source, *, local: bool = False):
    db.add(
        EventMembershipAssertion(
            workspace_id="local-default",
            event_id=event.id,
            source_id=source.id,
            frame_ids=[],
            action="ASSERT",
            membership="REPORTS_EVENT",
            contextual_role_fields={"origin": "PHASE17_FACT_DELTA_CONTROLLED"},
            audit_run_id=None,
            authority_policy_version="phase17-fact-delta-controlled",
            authority_epoch=1,
            authority_status="AUTHORIZED_SOURCE_LOCAL" if local else "AUTHORIZED",
            supersedes_assertion_id=None,
        )
    )
    db.flush()


def _obs(event: Event, source: Source, key: str, refs: tuple[str, ...], day: int):
    return EventObservationV01(
        event_id=event.id,
        observation_key=(key * 64)[:64],
        source_id=source.id,
        semantic_input_digests=(f"semantic-{key}",),
        evidence_time=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, day, 12, 1, tzinfo=timezone.utc),
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=refs,
    )
def _previous_state(
    *,
    event: Event,
    fact_text: str,
    fact_ref: str,
    status: str,
) -> SemanticFactStateV01:
    return make_fact_state(
        event_id=event.id,
        facts=(
            CurrentFactV01(
                fact_id="fact-previous",
                text=fact_text,
                support_refs=(fact_ref,),
            ),
        ),
        status=status,
        effective_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
    )


def _run_case(
    *,
    name: str,
    expected_kind: str | None,
    previous_fact: str | None,
    previous_ref: str | None,
    previous_status: str | None,
    new_statement: str,
    new_ref: str,
    expected_status: str | None = None,
    expect_retire: bool | None = None,
    expect_fact_count: int | None = None,
):
    db = _db()
    try:
        event = _event(db, name)
        source_ids = []
        previous = None
        previous_units = []
        if previous_fact is not None:
            a = _source(db, "previous evidence")
            _member(db, event, a, local=True)
            source_ids.append(a.id)
            previous = _previous_state(
                event=event,
                fact_text=previous_fact,
                fact_ref=previous_ref,
                status=previous_status or "ACTIVE",
            )
            previous_units = [
                {
                    "unit_id": previous_ref,
                    "statement": previous_fact,
                    "epistemic_status": "SOURCE_CLAIM",
                    "confidence": "HIGH",
                }
            ]

        b = _source(db, "new evidence")
        _member(db, event, b, local=previous is None)
        source_ids.append(b.id)
        obs = _obs(event, b, "b", (new_ref,), 18)
        new_units = [
            {
                "unit_id": new_ref,
                "statement": new_statement,
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
            }
        ]

        delta = decide_fact_delta(
            event_identity={
                "title": event.title,
                "event_type": event.event_type,
                "actors": list(event.actors or []),
                "action": event.action,
                "object": event.object,
            },
            previous=previous,
            observation=obs,
            previous_support_units=previous_units,
            new_semantic_units=new_units,
            chat_fn=chat_json,
        )
        observed_kind = delta.kind if delta is not None else None
        applied = apply_fact_delta(
            db,
            event_id=event.id,
            previous=previous,
            observation=obs,
            delta=delta,
            supporting_source_ids=source_ids,
        )
        observed_status = applied.fact_state.status
        retired = bool(delta and delta.retire_fact_ids)
        fact_count = len(applied.fact_state.facts)
        return {
            "name": name,
            "expected_kind": expected_kind,
            "observed_kind": observed_kind,
            "kind_match": observed_kind == expected_kind,
            "expected_status": expected_status,
            "observed_status": observed_status,
            "status_match": (
                True if expected_status is None else observed_status == expected_status
            ),
            "expect_retire": expect_retire,
            "observed_retire": retired,
            "retire_match": (
                True if expect_retire is None else retired == expect_retire
            ),
            "expect_fact_count": expect_fact_count,
            "observed_fact_count": fact_count,
            "fact_count_match": (
                True if expect_fact_count is None else fact_count == expect_fact_count
            ),
            "delta": delta.model_dump(mode="json") if delta is not None else None,
            "fact_state": applied.fact_state.model_dump(mode="json"),
            "event_state": applied.event_state.model_dump(mode="json"),
        }
    finally:
        db.close()
def run() -> dict:
    cases = [
        _run_case(
            name="INITIAL_ADD",
            expected_kind="ADD",
            previous_fact=None,
            previous_ref=None,
            previous_status=None,
            new_statement="Jev has been publicly released as a new decision-oriented model.",
            new_ref="uLaunch",
            expected_status="EMERGING",
            expect_retire=False,
            expect_fact_count=1,
        ),
        _run_case(
            name="CORROBORATION_NONE",
            expected_kind=None,
            previous_fact="Jev has been publicly released.",
            previous_ref="uLaunch",
            previous_status="ACTIVE",
            new_statement="An independent source reports the same Jev release without adding a new material fact.",
            new_ref="uCorroborate",
            expected_status="ACTIVE",
            expect_retire=False,
            expect_fact_count=1,
        ),
        _run_case(
            name="PERIPHERAL_REACTION_NONE",
            expected_kind=None,
            previous_fact="Jev has multiple live game demonstrations.",
            previous_ref="uGame",
            previous_status="ACTIVE",
            new_statement="The author says this feels like an everything-is-about-to-change moment and reports that people sent DMs asking whether the demo is real.",
            new_ref="uReaction",
            expected_status="ACTIVE",
            expect_retire=False,
            expect_fact_count=1,
        ),
        _run_case(
            name="SPECULATION_NONE",
            expected_kind=None,
            previous_fact="Jev has been publicly released and is undergoing early validation.",
            previous_ref="uLaunch",
            previous_status="ACTIVE",
            new_statement="The author suggests Jev could someday be used as a teaching assistant or for other human-hired roles.",
            new_ref="uSpeculation",
            expected_status="ACTIVE",
            expect_retire=False,
            expect_fact_count=1,
        ),
        _run_case(
            name="INCIDENTAL_HARDWARE_NONE",
            expected_kind=None,
            previous_fact="A Jev-based model has been open-sourced for early validation.",
            previous_ref="uOpen",
            previous_status="ACTIVE",
            new_statement="The accompanying demo is shown on an M4 MacBook.",
            new_ref="uHardware",
            expected_status="ACTIVE",
            expect_retire=False,
            expect_fact_count=1,
        ),
        _run_case(
            name="GAME_DEMO_MERGE",
            expected_kind="ADD",
            previous_fact="Jev has a live Super Mario demonstration.",
            previous_ref="uMario",
            previous_status="ACTIVE",
            new_statement="A separate later demonstration shows Jev playing DOOM live in real time.",
            new_ref="uDoom",
            expected_status="ACTIVE",
            expect_retire=True,
            expect_fact_count=1,
        ),
        _run_case(
            name="BROAD_GAME_FACT_MERGE",
            expected_kind="ADD",
            previous_fact="Jev has multiple live game demonstrations, including Super Mario and DOOM.",
            previous_ref="uGames",
            previous_status="ACTIVE",
            new_statement="A later demonstration shows Jev playing Tetris live, with prompt changes altering play.",
            new_ref="uTetris",
            expected_status="ACTIVE",
            expect_retire=True,
            expect_fact_count=1,
        ),
        _run_case(
            name="USE_CASE_ADD",
            expected_kind="ADD",
            previous_fact="Jev has been demonstrated in live video-game control.",
            previous_ref="uGame",
            previous_status="ACTIVE",
            new_statement="A Monad engineer demonstrates a Jev-based automated trading bot using market data and an on-chain order book.",
            new_ref="uTrading",
            expected_status="ACTIVE",
            expect_retire=None,
            expect_fact_count=None,
        ),
        _run_case(
            name="SUPERSEDE",
            expected_kind="SUPERSEDE",
            previous_fact="The implementation uses a transformer architecture.",
            previous_ref="uOld",
            previous_status="ACTIVE",
            new_statement="The authors explicitly correct the earlier description and state that the implementation is not a transformer architecture.",
            new_ref="uCorrection",
            expected_status="ACTIVE",
            expect_retire=True,
            expect_fact_count=1,
        ),
        _run_case(
            name="CONTEST",
            expected_kind="CONTEST",
            previous_fact="An independent reproduction reports a strong workflow gain.",
            previous_ref="uPositive",
            previous_status="ACTIVE",
            new_statement="A separate independent reproduction fails to reproduce that workflow gain under comparable conditions.",
            new_ref="uNegative",
            expected_status="CONTESTED",
            expect_retire=False,
            expect_fact_count=2,
        ),
        _run_case(
            name="RESOLVE",
            expected_kind="SUPERSEDE",
            previous_fact="The Jev launch-and-validation episode remains active.",
            previous_ref="uActive",
            previous_status="ACTIVE",
            new_statement="The authors explicitly announce that this Jev launch episode is concluded and no further validation updates are planned.",
            new_ref="uClosure",
            expected_status="RESOLVED",
            expect_retire=True,
            expect_fact_count=1,
        ),
    ]
    diagnostics = {
        "kind_matches": sum(1 for row in cases if row["kind_match"]),
        "status_matches": sum(1 for row in cases if row["status_match"]),
        "retire_matches": sum(1 for row in cases if row["retire_match"]),
        "fact_count_matches": sum(1 for row in cases if row["fact_count_match"]),
        "all_kind_matches": all(row["kind_match"] for row in cases),
        "all_status_matches": all(row["status_match"] for row in cases),
        "all_retire_matches": all(row["retire_match"] for row in cases),
        "all_fact_count_matches": all(row["fact_count_match"] for row in cases),
    }
    return {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_FACT_DELTA_REAL_MODEL_COMPLETE",
        "cases": cases,
        "diagnostics": diagnostics,
        "guardrails": [
            "In-memory database only.",
            "Configured real LLM used only for Decide.",
            "Apply is deterministic.",
            "No fixed current-fact count cap.",
            "No production Event/Attention/WATCH writes.",
        ],
    }


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for row in report["cases"]:
        print(
            row["name"],
            "kind", row["observed_kind"],
            "kind_ok", row["kind_match"],
            "status", row["observed_status"],
            "retire", row["observed_retire"],
            "facts", row["observed_fact_count"],
        )
        print("  delta:", json.dumps(row["delta"], ensure_ascii=False))
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
