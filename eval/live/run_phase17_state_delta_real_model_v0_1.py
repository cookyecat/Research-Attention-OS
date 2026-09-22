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
from app.services.event_state import (
    WorldStateV02,
    make_event_state_v02,
    structural_evidence_state_v02,
)
from app.services.event_state_delta import (
    StateDeltaV01,
    apply_state_delta,
    decide_state_delta,
)

RUN_VERSION = "phase17-state-delta-real-model-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase17_state_delta_real_model_v0_1"
def _db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return Session(engine)


def _event(db: Session, label: str) -> Event:
    row = Event(
        title=label,
        event_type="RESEARCH_RESULT",
        actors=["Acme Research"],
        action="report result",
        object=label,
        summary=label,
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
        fingerprint=f"phase17-state-delta-{uuid4()}",
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
            contextual_role_fields={"origin": "PHASE17_STATE_DELTA_CONTROLLED"},
            audit_run_id=None,
            authority_policy_version="phase17-state-delta-controlled",
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
def _controlled_previous(
    db: Session,
    *,
    event: Event,
    source: Source,
    ref: str,
    statement: str,
    status: str,
):
    evidence_state = structural_evidence_state_v02(
        db,
        event.id,
        active_semantic_unit_refs=(ref,),
        supporting_source_ids=[source.id],
    )
    return make_event_state_v02(
        event_id=event.id,
        world_state=WorldStateV02(
            synopsis=statement,
            status=status,
            effective_at=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
            active_semantic_unit_refs=(ref,),
        ),
        evidence_state=evidence_state,
    )


def _run_case(
    *,
    name: str,
    expected_kind: str | None,
    previous_statement: str | None,
    previous_status: str | None,
    previous_ref: str | None,
    new_statement: str,
    new_ref: str,
    expected_status: str | None = None,
):
    db = _db()
    try:
        event = _event(db, name)
        source_ids = []
        previous = None
        unit_index = {}
        previous_units = []
        if previous_statement is not None:
            a = _source(db, "previous evidence")
            _member(db, event, a, local=True)
            source_ids.append(a.id)
            previous = _controlled_previous(
                db,
                event=event,
                source=a,
                ref=previous_ref,
                statement=previous_statement,
                status=previous_status or "ACTIVE",
            )
            previous_row = {
                "unit_id": previous_ref,
                "statement": previous_statement,
                "epistemic_status": "SOURCE_CLAIM",
                "confidence": "HIGH",
            }
            previous_units = [previous_row]
            unit_index[previous_ref] = previous_row

        b = _source(db, "new evidence")
        _member(db, event, b, local=previous is None)
        source_ids.append(b.id)
        obs = _obs(event, b, "b", (new_ref,), 18)
        new_row = {
            "unit_id": new_ref,
            "statement": new_statement,
            "epistemic_status": "SOURCE_CLAIM",
            "confidence": "HIGH",
        }
        unit_index[new_ref] = new_row

        delta = decide_state_delta(
            previous=previous,
            observation=obs,
            previous_active_semantic_units=previous_units,
            new_semantic_units=[new_row],
            chat_fn=chat_json,
        )
        observed_kind = delta.kind if delta is not None else None
        applied = None
        apply_error = None
        try:
            applied = apply_state_delta(
                db,
                event_id=event.id,
                previous=previous,
                observation=obs,
                delta=delta,
                supporting_source_ids=source_ids,
                semantic_units_by_ref=unit_index,
            )
        except Exception as exc:
            apply_error = f"{type(exc).__name__}: {exc}"

        observed_status = (
            applied.next_state.world_state.status if applied is not None else None
        )
        return {
            "name": name,
            "expected_kind": expected_kind,
            "observed_kind": observed_kind,
            "kind_match": observed_kind == expected_kind,
            "delta": delta.model_dump(mode="json") if delta is not None else None,
            "expected_status": expected_status,
            "observed_status": observed_status,
            "status_match": (
                True if expected_status is None else observed_status == expected_status
            ),
            "apply_accepted": applied is not None,
            "apply_error": apply_error,
            "next_state": (
                applied.next_state.model_dump(mode="json")
                if applied is not None
                else None
            ),
        }
    finally:
        db.close()
def run() -> dict:
    cases = [
        _run_case(
            name="INITIAL_ADD",
            expected_kind="ADD",
            previous_statement=None,
            previous_status=None,
            previous_ref=None,
            new_statement="Jev has been publicly released as a new decision-oriented model.",
            new_ref="uLaunch",
            expected_status="EMERGING",
        ),
        _run_case(
            name="CORROBORATION_NONE",
            expected_kind=None,
            previous_statement="Jev has been publicly released as a new decision-oriented model.",
            previous_status="ACTIVE",
            previous_ref="uLaunch",
            new_statement="An independent source reports the same Jev public release without adding a new material fact.",
            new_ref="uCorroborate",
            expected_status="ACTIVE",
        ),
        _run_case(
            name="ADD",
            expected_kind="ADD",
            previous_statement="Jev has been publicly released.",
            previous_status="ACTIVE",
            previous_ref="uLaunch",
            new_statement="The authors publish a technical presentation explaining Jev's mechanism in substantially more detail.",
            new_ref="uMechanism",
            expected_status="ACTIVE",
        ),
        _run_case(
            name="TOPIC_SHIFT_ADD",
            expected_kind="ADD",
            previous_statement="Jev is demonstrated in a claimed Tesla FSD rebuild use case.",
            previous_status="ACTIVE",
            previous_ref="uFSD",
            new_statement=(
                "A Monad engineer demonstrates a separate Jev-based automated trading bot "
                "that reads market data and sends orders to an on-chain order book."
            ),
            new_ref="uTrading",
            expected_status="ACTIVE",
        ),
        _run_case(
            name="ADDITIONAL_DEMO_ADD",
            expected_kind="ADD",
            previous_statement="Jev was demonstrated playing one game in real time.",
            previous_status="ACTIVE",
            previous_ref="uDemoA",
            new_statement=(
                "A separate later demonstration shows Jev playing a different game in real time; "
                "the new source does not say the earlier demonstration was wrong."
            ),
            new_ref="uDemoB",
            expected_status="ACTIVE",
        ),
        _run_case(
            name="SUPERSEDE",
            expected_kind="SUPERSEDE",
            previous_statement="The reported implementation uses a transformer architecture.",
            previous_status="ACTIVE",
            previous_ref="uOld",
            new_statement="The authors explicitly correct the earlier description and state that the implementation is not a transformer architecture.",
            new_ref="uCorrection",
            expected_status="ACTIVE",
        ),
        _run_case(
            name="CONTEST",
            expected_kind="CONTEST",
            previous_statement="An independent reproduction reports a strong Jev workflow improvement.",
            previous_status="ACTIVE",
            previous_ref="uPositive",
            new_statement="A separate independent reproduction fails to reproduce the reported workflow improvement under comparable conditions.",
            new_ref="uNegative",
            expected_status="CONTESTED",
        ),
        _run_case(
            name="RESOLVE",
            expected_kind="SUPERSEDE",
            previous_statement="Jev remains an active launch-and-validation episode.",
            previous_status="ACTIVE",
            previous_ref="uActive",
            new_statement=(
                "The authors explicitly announce that this Jev launch episode is concluded "
                "and no further releases or validation updates are planned for this episode."
            ),
            new_ref="uClosure",
            expected_status="RESOLVED",
        ),
    ]
    return {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_STATE_DELTA_REAL_MODEL_COMPLETE",
        "cases": cases,
        "diagnostics": {
            "kind_matches": sum(1 for row in cases if row["kind_match"]),
            "status_matches": sum(1 for row in cases if row["status_match"]),
            "apply_accepts": sum(1 for row in cases if row["apply_accepted"]),
            "all_kind_matches": all(row["kind_match"] for row in cases),
            "all_status_matches": all(row["status_match"] for row in cases),
            "all_apply_accepted": all(row["apply_accepted"] for row in cases),
        },
        "guardrails": [
            "In-memory database only.",
            "Configured real LLM used only for Decide.",
            "Apply is deterministic and owns canonical state materialization.",
            "Decide returns only None or minimal StateDelta; it never rewrites next EventState.",
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
            "expected", row["expected_kind"],
            "observed", row["observed_kind"],
            "match", row["kind_match"],
            "status", row["observed_status"],
            "apply", row["apply_accepted"],
        )
        print("  delta:", json.dumps(row["delta"], ensure_ascii=False))
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
