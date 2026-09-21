from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.db import Base
from app.enums import DetectedBy, SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.event import Event, EventLineage, EventMembershipAssertion, EventSource
from app.models.scheduler import AttentionPlan
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.continuous_attention import process_source_arrival
from app.services.ingestion import ingest_text
from app.services.pipeline import run_pipeline
from app.services.source_graph import persist_source_edge
from app.services.watch_loop import watch_cumulative_source_ids
from app.testing.kernel_fixture import seed_mvp_kernel

RUN_VERSION = "phase15-event-continuity-lifecycle-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase15_event_continuity_lifecycle_v0_1"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _event_ids(db: Session, source_id):
    return sorted(
        str(x)
        for x in db.execute(
            select(EventSource.event_id).where(EventSource.source_id == source_id)
        ).scalars().all()
    )


def _make_watch(db: Session, initial_result: dict) -> Watch:
    run = db.get(AnalysisRun, UUID(str(initial_result["analysis_run"]["id"])))
    watch = Watch(
        target_type="SOURCE",
        target_ref="phase15-controlled",
        status="ACTIVE",
        created_reason="Phase15 controlled Event-continuity lifecycle probe",
        kernel_target_ids=[],
        analysis_run_id=run.id,
    )
    db.add(watch)
    db.flush()
    db.add(
        WatchTrigger(
            watch_id=watch.id,
            trigger_type="NEW_EVIDENCE",
            trigger_config={},
        )
    )
    db.flush()
    return watch


def _base_world(db: Session):
    seed_mvp_kernel(db)
    provider = RuleBasedCognitiveProvider()
    a = ingest_text(
        db,
        "Acme launched the Nimbus API public beta at AtlasConf. This is the first report.",
        title="Acme launches Nimbus API beta",
    )
    initial = run_pipeline(
        db,
        a.id,
        provider=provider,
        allow_watch_creation=False,
        reprocess=True,
    )
    watch = _make_watch(db, initial)
    a_links = db.execute(
        select(EventSource).where(EventSource.source_id == a.id)
    ).scalars().all()
    if len(a_links) != 1:
        raise RuntimeError(f"expected exactly one initial Event membership, got {len(a_links)}")
    event_a = db.get(Event, a_links[0].event_id)
    return provider, a, event_a, watch, initial


def _new_distinct_event(db: Session, source, *, title: str, summary: str) -> Event:
    event = Event(
        title=title,
        event_type="PUBLICATION",
        summary=summary,
        confidence=0.8,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    db.add(
        EventSource(
            event_id=event.id,
            source_id=source.id,
            relationship="REPORTS",
            confidence=0.9,
        )
    )
    db.flush()
    return event


def _capture_before(db: Session, watch: Watch, b) -> dict:
    return {
        "watch_count": db.scalar(select(func.count()).select_from(Watch)),
        "attention_plan_count": db.scalar(select(func.count()).select_from(AttentionPlan)),
        "watch_status": watch.status,
        "watch_cumulative_source_ids": [str(x) for x in watch_cumulative_source_ids(db, watch)],
        "new_source_event_ids": _event_ids(db, b.id),
    }


def _capture_after(db: Session, watch: Watch, b, result: dict) -> dict:
    checks = db.execute(
        select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
    ).scalars().all()
    return {
        "matched_watch": bool(result["matched_watch"]),
        "watch_decisions": result["watch_decisions"],
        "ordinary_analysis_present": result["ordinary_analysis"] is not None,
        "watch_count": db.scalar(select(func.count()).select_from(Watch)),
        "attention_plan_count": db.scalar(select(func.count()).select_from(AttentionPlan)),
        "watch_status": watch.status,
        "watch_cumulative_source_ids": [str(x) for x in watch_cumulative_source_ids(db, watch)],
        "new_source_event_ids": _event_ids(db, b.id),
        "watch_check_count": len(checks),
        "watch_check_outcomes": [row.outcome for row in checks],
    }


def _run_arm(kind: str, *, add_source_proxy: bool = False) -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        provider, a, event_a, watch, initial = _base_world(db)

        if kind == "SAME_EVENT_CORROBORATION":
            b = ingest_text(
                db,
                "Independent Publisher Beta confirms Acme launched the Nimbus API public beta at AtlasConf.",
                title="Independent report confirms Nimbus API beta launch",
            )
            db.add(
                EventSource(
                    event_id=event_a.id,
                    source_id=b.id,
                    relationship="REPORTS",
                    confidence=0.9,
                )
            )
            db.add(
                EventMembershipAssertion(
                    workspace_id="phase15-controlled",
                    event_id=event_a.id,
                    source_id=b.id,
                    frame_ids=[],
                    action="ASSERT",
                    membership="REPORTS_EVENT",
                    contextual_role_fields={
                        "cross_source_commitment": True,
                        "controlled_fixture": True,
                    },
                    audit_run_id=None,
                    authority_policy_version="phase15-controlled-cross-source-v0.1",
                    authority_epoch=1,
                    authority_status="AUTHORIZED",
                    supersedes_assertion_id=None,
                )
            )
            db.flush()
            expected = "UPDATE_EXISTING_EVENT"

        elif kind == "SUCCESSOR_CONTRADICTION":
            b = ingest_text(
                db,
                "Acme later paused the Nimbus API public beta after a launch-day reliability incident.",
                title="Acme pauses Nimbus API beta after reliability incident",
            )
            event_b = _new_distinct_event(
                db,
                b,
                title="Acme pauses Nimbus API beta",
                summary="A later state transition pauses the previously launched Nimbus API beta.",
            )
            db.add(
                EventLineage(
                    workspace_id="phase15-controlled",
                    predecessor_event_id=event_a.id,
                    successor_event_id=event_b.id,
                    relationship="SUCCESSOR_CONTRADICTS",
                    audit_run_id=None,
                    authority_epoch=1,
                )
            )
            db.flush()
            if add_source_proxy:
                persist_source_edge(
                    db,
                    b.id,
                    a.id,
                    SourceEdgeRelationship.CONTRADICTS,
                    confidence=1.0,
                    detected_by=DetectedBy.USER,
                    evidence="Controlled proxy for a successor contradiction.",
                )
            expected = "RECOMPUTE_EXISTING_LIFECYCLE"

        elif kind == "DISTINCT_SAME_ACTOR_PRODUCT":
            b = ingest_text(
                db,
                "Acme opened a separate Nimbus API developer grant program for university teams.",
                title="Acme opens Nimbus API developer grant program",
            )
            _new_distinct_event(
                db,
                b,
                title="Acme opens Nimbus API developer grant program",
                summary="A separate program involving the same actor/product but a distinct state transition.",
            )
            expected = "SPAWN_NEW_EVENT_DECISION_PATH"

        else:
            raise ValueError(kind)

        before = _capture_before(db, watch, b)
        result = process_source_arrival(
            db,
            b.id,
            provider=provider,
        )
        after = _capture_after(db, watch, b, result)

        observed = (
            "EXISTING_LIFECYCLE_RECHECK"
            if after["matched_watch"] and after["watch_decisions"]
            and any(d.get("action") == "RECHECK" for d in after["watch_decisions"])
            else "EXISTING_LIFECYCLE_OTHER"
            if after["matched_watch"]
            else "ORDINARY_NEW_ANALYSIS_PATH"
        )

        membership_added = sorted(
            set(after["new_source_event_ids"]) - set(before["new_source_event_ids"])
        )

        return {
            "kind": kind,
            "source_proxy_added": add_source_proxy,
            "expected_lifecycle_semantics": expected,
            "observed_current_router": observed,
            "before": before,
            "after": after,
            "new_source_membership_added_during_processing": membership_added,
            "materialized_membership_changed_during_processing": bool(membership_added),
            "initial_attention_plan_id": (initial.get("attention_plan") or {}).get("id"),
        }


def run() -> dict:
    same = _run_arm("SAME_EVENT_CORROBORATION")
    successor_lineage_only = _run_arm("SUCCESSOR_CONTRADICTION", add_source_proxy=False)
    successor_with_proxy = _run_arm("SUCCESSOR_CONTRADICTION", add_source_proxy=True)
    distinct = _run_arm("DISTINCT_SAME_ACTOR_PRODUCT")

    diagnostics = {
        "same_event_routes_existing_lifecycle": (
            same["observed_current_router"] == "EXISTING_LIFECYCLE_RECHECK"
        ),
        "lineage_only_routes_existing_lifecycle": (
            successor_lineage_only["observed_current_router"] == "EXISTING_LIFECYCLE_RECHECK"
        ),
        "source_proxy_routes_successor_existing_lifecycle": (
            successor_with_proxy["observed_current_router"] == "EXISTING_LIFECYCLE_RECHECK"
        ),
        "distinct_same_actor_product_routes_new_path": (
            distinct["observed_current_router"] == "ORDINARY_NEW_ANALYSIS_PATH"
        ),
        "same_event_reuses_watch_identity": (
            same["after"]["watch_count"] == same["before"]["watch_count"] == 1
        ),
        "successor_proxy_reuses_watch_identity": (
            successor_with_proxy["after"]["watch_count"]
            == successor_with_proxy["before"]["watch_count"]
            == 1
        ),
        "same_event_processing_added_unexpected_event_membership": (
            same["materialized_membership_changed_during_processing"]
        ),
        "successor_proxy_processing_added_unexpected_event_membership": (
            successor_with_proxy["materialized_membership_changed_during_processing"]
        ),
    }

    return {
        "run_version": RUN_VERSION,
        "status": "EVENT_CONTINUITY_LIFECYCLE_PROBE_COMPLETE",
        "measurement_git_head": git_head(),
        "arms": {
            "CASE1_SAME_EVENT_CORROBORATION": same,
            "CASE2A_SUCCESSOR_EVENT_LINEAGE_ONLY": successor_lineage_only,
            "CASE2B_SUCCESSOR_EVENT_WITH_SOURCE_PROXY": successor_with_proxy,
            "CASE3_DISTINCT_SAME_ACTOR_PRODUCT": distinct,
        },
        "diagnostics": diagnostics,
        "guardrails": [
            "In-memory database only.",
            "No production Event/Attention mutation.",
            "EventLineage is distinct from SAME_EVENT.",
            "Case2a/2b are one semantic case with a routing-substrate ablation.",
            "Current AttentionPlan rows remain Source-level diagnostics; no EventDecision persistence is inferred.",
        ],
    }


def main():
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for name, arm in report["arms"].items():
        print(
            name,
            "expected", arm["expected_lifecycle_semantics"],
            "observed", arm["observed_current_router"],
            "before_events", arm["before"]["new_source_event_ids"],
            "after_events", arm["after"]["new_source_event_ids"],
            "added", arm["new_source_membership_added_during_processing"],
            "watch_count", arm["before"]["watch_count"], "->", arm["after"]["watch_count"],
            "plans", arm["before"]["attention_plan_count"], "->", arm["after"]["attention_plan_count"],
        )
    print("DIAGNOSTICS", json.dumps(report["diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
