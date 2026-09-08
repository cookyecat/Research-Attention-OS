from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select

from app.enums import Disposition, ExpectedOutput, SourceEdgeRelationship
from app.models.analysis import AnalysisRun
from app.models.event import EventSource
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.continuous_attention import process_source_arrival
from app.services.scheduler import PlanDraft, validate_plan
from app.services.source_graph import persist_source_edge
from tests.conftest import add_text, analyze


def _make_watch(db, initial_result):
    run = db.get(AnalysisRun, UUID(initial_result["analysis_run"]["id"]))
    watch = Watch(
        target_type="SOURCE",
        target_ref="phase8b-arrival",
        status="ACTIVE",
        created_reason="controlled continuous arrival",
        kernel_target_ids=[],
        analysis_run_id=run.id,
    )
    db.add(watch); db.flush()
    trigger = WatchTrigger(watch_id=watch.id, trigger_type="NEW_EVIDENCE", trigger_config={})
    db.add(trigger); db.flush()
    return watch


def _maturity_route(features, *_args, **_kwargs):
    if features.independent_source_count >= 2:
        return validate_plan(
            PlanDraft(
                disposition=Disposition.AWARE,
                expected_output=ExpectedOutput.SUMMARY,
                reason="controlled independent-evidence promotion",
                cognitive_budget_minutes=2,
            )
        )
    return validate_plan(
        PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="controlled insufficient-independent-evidence watch",
            watch_after_processing=True,
            watch_triggers=["NEW_EVIDENCE"],
            cognitive_budget_minutes=2,
        )
    )


def _run_payload(db, analysis_run_id):
    run = db.get(AnalysisRun, analysis_run_id)
    assert run is not None
    return run.result_payload, run


def test_continuous_arrival_distinguishes_article_from_independent_evidence(client, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    a_text = "Original evidence about a developing result with one source."
    a = add_text(client, a_text, title="arrival-A")
    initial = analyze(client, a["id"])
    watch = _make_watch(db, initial)
    baseline_watch_count = db.scalar(select(func.count()).select_from(Watch))

    monkeypatch.setattr(pipeline_mod, "route", _maturity_route)

    # B is a byte-for-byte repost. Ingestion keeps the Source but SourceGraph marks it secondary.
    b = add_text(client, a_text, title="arrival-B-repost")
    b_result = process_source_arrival(db, UUID(b["id"]))
    b_decision = b_result["watch_decisions"][0]
    assert b_decision["evidence_class"] == "DUPLICATE"
    assert b_decision["action"] == "SUPPRESS_RECHECK"
    assert b_decision["outcome"] == "DUPLICATE_SUPPRESSED"
    assert watch.status == "ACTIVE"

    # C is a distinct article but explicitly a secondary report on A.
    c = add_text(client, "Secondary reporting repeats the same result with commentary.", title="arrival-C-secondary")
    persist_source_edge(db, UUID(c["id"]), UUID(a["id"]), SourceEdgeRelationship.REPORTS_ON)
    c_result = process_source_arrival(db, UUID(c["id"]))
    c_decision = c_result["watch_decisions"][0]
    assert c_decision["evidence_class"] == "SECONDARY"
    assert c_decision["action"] == "RECHECK"
    assert c_decision["outcome"] == "KEEP_ACTIVE"
    c_check = db.get(WatchCheck, UUID(c_decision["check_id"]))
    c_payload, c_run = _run_payload(db, c_check.analysis_run_id)
    c_ind = c_payload["relational_context"]["independence"]
    assert c_ind["independent_sources"] == 1
    assert c_ind["secondary_reports"] == 1
    assert str(UUID(c["id"])) in {str(x) for x in c_run.extra_source_ids}
    assert str(UUID(b["id"])) not in {str(x) for x in c_run.extra_source_ids}

    # D is new independent evidence attached to the same Event as A.
    a_event = db.execute(
        select(EventSource).where(EventSource.source_id == UUID(a["id"]))
    ).scalars().first()
    assert a_event is not None
    d = add_text(client, "Independent replication confirms the developing result.", title="arrival-D-independent")
    db.add(EventSource(event_id=a_event.event_id, source_id=UUID(d["id"]), relationship="REPORTS", confidence=0.9))
    db.flush()

    d_result = process_source_arrival(db, UUID(d["id"]))
    d_decision = d_result["watch_decisions"][0]
    assert d_decision["evidence_class"] == "INDEPENDENT"
    assert d_decision["action"] == "RECHECK"
    assert d_decision["outcome"] == "PROMOTED"
    assert watch.status == "PROMOTED"
    d_check = db.get(WatchCheck, UUID(d_decision["check_id"]))
    d_payload, d_run = _run_payload(db, d_check.analysis_run_id)
    d_ind = d_payload["relational_context"]["independence"]
    assert d_ind["independent_sources"] == 2
    assert d_ind["secondary_reports"] == 1
    d_extra = {str(x) for x in d_run.extra_source_ids}
    assert str(UUID(c["id"])) in d_extra
    assert str(UUID(d["id"])) in d_extra
    assert str(UUID(b["id"])) not in d_extra

    checks = db.execute(
        select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
    ).scalars().all()
    assert [check.outcome for check in checks] == [
        "DUPLICATE_SUPPRESSED", "KEEP_ACTIVE", "PROMOTED"
    ]
    assert db.scalar(select(func.count()).select_from(Watch)) == baseline_watch_count


def test_unrelated_arrival_uses_ordinary_analysis(client, db):
    a = add_text(client, "Initial watched evidence.", title="arrival-unrelated-A")
    initial = analyze(client, a["id"])
    watch = _make_watch(db, initial)

    unrelated = add_text(client, "A completely unrelated cooking note.", title="arrival-unrelated-X")
    result = process_source_arrival(db, UUID(unrelated["id"]))
    assert result["matched_watch"] is False
    assert result["watch_decisions"] == []
    assert result["ordinary_analysis"] is not None
    assert result["ordinary_analysis"]["analysis_run"]["source_id"] == unrelated["id"]
    assert watch.status == "ACTIVE"
