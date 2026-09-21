from __future__ import annotations

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
from app.services.event_state import WorldStateV02
from app.services.event_state_transition import (
    StateTransitionProposalV01,
    estimate_state_transition,
    reduce_state_transition,
)

RUN_VERSION = "phase17-state-transition-phi-real-model-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase17_state_transition_phi_real_model_v0_1"


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
        fingerprint=f"phase17-phi-{uuid4()}",
        ingestion_method="CONTROLLED_EVAL",
        raw_metadata={},
    )
    db.add(row)
    db.flush()
    db.refresh(row)
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
            contextual_role_fields={"origin": "PHASE17_PHI_CONTROLLED"},
            audit_run_id=None,
            authority_policy_version="phase17-phi-controlled",
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
        source_snapshot_id=None,
        frame_ids=(),
        semantic_input_digests=(f"semantic-{key}",),
        evidence_time=datetime(2026, 9, day, 12, 0, tzinfo=timezone.utc),
        ingest_time=datetime(2026, 9, day, 12, 1, tzinfo=timezone.utc),
        world_time=None,
        provenance_digest=f"prov-{key}",
        audited_semantic_unit_refs=refs,
    )


def _controlled_initial(
    db: Session,
    *,
    event: Event,
    source: Source,
    obs: EventObservationV01,
    synopsis: str,
    status: str,
    refs: tuple[str, ...],
):
    proposal = StateTransitionProposalV01(
        transition_kind="INITIALIZE",
        world_state=WorldStateV02(
            synopsis=synopsis,
            status=status,
            effective_at=obs.evidence_time,
            active_semantic_unit_refs=refs,
        ),
        rationale="controlled initial state",
    )
    return reduce_state_transition(
        db,
        event_id=event.id,
        previous=None,
        observation=obs,
        proposal=proposal,
        supporting_source_ids=[source.id],
    ).next_state


def _run_case(
    *,
    name: str,
    expected_kind: str,
    previous_synopsis: str | None,
    previous_status: str | None,
    previous_ref: str | None,
    new_statement: str,
    expected_new_ref: str,
):
    db = _db()
    try:
        event = _event(db, name)
        source_ids = []
        previous = None
        if previous_synopsis is not None:
            a = _source(db, "previous evidence")
            _member(db, event, a, local=True)
            source_ids.append(a.id)
            obs_a = _obs(event, a, "a", (previous_ref,), 16)
            previous = _controlled_initial(
                db,
                event=event,
                source=a,
                obs=obs_a,
                synopsis=previous_synopsis,
                status=previous_status or "reported",
                refs=(previous_ref,),
            )

        b = _source(db, "new evidence")
        _member(db, event, b, local=previous is None)
        source_ids.append(b.id)
        obs_b = _obs(event, b, "b", (expected_new_ref,), 18)

        proposal = estimate_state_transition(
            previous=previous,
            observation=obs_b,
            new_semantic_units=[
                {
                    "unit_id": expected_new_ref,
                    "statement": new_statement,
                    "epistemic_status": "SOURCE_CLAIM",
                    "confidence": "HIGH",
                }
            ],
            chat_fn=chat_json,
        )

        reduced = None
        reducer_error = None
        try:
            reduced = reduce_state_transition(
                db,
                event_id=event.id,
                previous=previous,
                observation=obs_b,
                proposal=proposal,
                supporting_source_ids=source_ids,
            )
        except Exception as exc:
            reducer_error = f"{type(exc).__name__}: {exc}"

        return {
            "name": name,
            "expected_kind": expected_kind,
            "observed_kind": proposal.transition_kind,
            "kind_match": proposal.transition_kind == expected_kind,
            "proposal": proposal.model_dump(mode="json"),
            "reducer_accepted": reduced is not None,
            "reducer_error": reducer_error,
            "next_state": (
                reduced.next_state.model_dump(mode="json") if reduced is not None else None
            ),
        }
    finally:
        db.close()


def run() -> dict:
    cases = [
        _run_case(
            name="INITIALIZE",
            expected_kind="INITIALIZE",
            previous_synopsis=None,
            previous_status=None,
            previous_ref=None,
            new_statement="Jev has been publicly released as a new decision-oriented model.",
            expected_new_ref="uLaunch",
        ),
        _run_case(
            name="CORROBORATION_NO_CHANGE",
            expected_kind="NO_MATERIAL_CHANGE",
            previous_synopsis="Jev has been publicly released as a new decision-oriented model.",
            previous_status="early emergence",
            previous_ref="uLaunch",
            new_statement="An independent source reports the same Jev public release without adding a new material fact.",
            expected_new_ref="uCorroborate",
        ),
        _run_case(
            name="ENRICH",
            expected_kind="ENRICH",
            previous_synopsis="Jev has been publicly released and is attracting early discussion.",
            previous_status="early emergence",
            previous_ref="uLaunch",
            new_statement="The authors publish a technical presentation explaining Jev's mechanism in substantially more detail.",
            expected_new_ref="uMechanism",
        ),
        _run_case(
            name="REPLACE_CURRENT",
            expected_kind="REPLACE_CURRENT",
            previous_synopsis="The reported implementation uses a transformer architecture.",
            previous_status="reported",
            previous_ref="uOld",
            new_statement="The authors explicitly correct the earlier description and state that the implementation is not a transformer architecture.",
            expected_new_ref="uCorrection",
        ),
        _run_case(
            name="CONTEST",
            expected_kind="CONTEST",
            previous_synopsis="An independent reproduction reports a strong Jev workflow improvement.",
            previous_status="reported",
            previous_ref="uPositive",
            new_statement="A separate independent reproduction fails to reproduce the reported workflow improvement under comparable conditions.",
            expected_new_ref="uNegative",
        ),
    ]
    return {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_REAL_MODEL_COMPLETE",
        "cases": cases,
        "diagnostics": {
            "kind_matches": sum(1 for row in cases if row["kind_match"]),
            "reducer_accepts": sum(1 for row in cases if row["reducer_accepted"]),
            "all_kind_matches": all(row["kind_match"] for row in cases),
            "all_reducer_accepted": all(row["reducer_accepted"] for row in cases),
        },
        "guardrails": [
            "In-memory database only.",
            "Configured real LLM used only for Phi proposals.",
            "Deterministic reducer retains canonical support authority.",
            "No production Event/Attention/WATCH writes.",
            "Cases fixed before execution; no Human Gold tuning.",
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
            "reducer", row["reducer_accepted"],
        )
        if row["reducer_error"]:
            print("  reducer_error:", row["reducer_error"])
        print("  synopsis:", row["proposal"]["world_state"]["synopsis"])
        print("  refs:", row["proposal"]["world_state"]["active_semantic_unit_refs"])
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
