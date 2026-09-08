from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from sqlalchemy import func, select

from app.enums import Disposition, ExpectedOutput
from app.models.analysis import AnalysisRun
from app.models.watch import Watch, WatchCheck, WatchTrigger
from app.services.scheduler import PlanDraft, validate_plan
from app.services.watch_loop import recheck_watch
from tests.conftest import add_text, analyze


def _watch_route(*_a, **_k):
    return validate_plan(
        PlanDraft(
            disposition=Disposition.WATCH,
            expected_output=ExpectedOutput.WATCH,
            reason="controlled watch responsibility test",
            watch_after_processing=True,
            watch_triggers=["NEW_EVIDENCE"],
            cognitive_budget_minutes=2,
        )
    )

def _aware_route(*_a, **_k):
    return validate_plan(
        PlanDraft(
            disposition=Disposition.AWARE,
            expected_output=ExpectedOutput.SUMMARY,
            reason="controlled promotion test",
            cognitive_budget_minutes=2,
        )
    )


def _make_watch(db, initial_result):
    run = db.get(AnalysisRun, UUID(initial_result["analysis_run"]["id"]))
    watch = Watch(
        target_type="SOURCE",
        target_ref="phase8a-test",
        status="ACTIVE",
        created_reason="controlled lifecycle",
        kernel_target_ids=[],
        analysis_run_id=run.id,
    )
    db.add(watch); db.flush()
    trigger = WatchTrigger(watch_id=watch.id, trigger_type="NEW_EVIDENCE", trigger_config={})
    db.add(trigger); db.flush()
    return watch, trigger

def test_watch_recheck_is_cumulative_and_records_history(client, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    a = add_text(client, "Initial evidence about a developing research result.", title="watch-A")
    b = add_text(client, "A second independent report adds evidence.", title="watch-B")
    c = add_text(client, "A third report makes the result worth surfacing.", title="watch-C")
    initial = analyze(client, a["id"])
    watch, trigger = _make_watch(db, initial)
    baseline_watch_count = db.scalar(select(func.count()).select_from(Watch))

    monkeypatch.setattr(pipeline_mod, "route", _watch_route)
    first_check, first = recheck_watch(db, watch=watch, trigger=trigger, new_source_id=UUID(b["id"]))
    assert first_check.outcome == "KEEP_ACTIVE"
    assert watch.status == "ACTIVE"
    assert db.scalar(select(func.count()).select_from(Watch)) == baseline_watch_count
    assert first["attention_plan"]["score_debug"]["authorized_artifacts"]["watch_creation_suppressed"] is True
    first_run = db.get(AnalysisRun, first_check.analysis_run_id)
    assert str(UUID(b["id"])) in {str(x) for x in first_run.extra_source_ids}

    monkeypatch.setattr(pipeline_mod, "route", _aware_route)
    second_check, second = recheck_watch(db, watch=watch, trigger=trigger, new_source_id=UUID(c["id"]))
    assert second_check.outcome == "PROMOTED"
    assert watch.status == "PROMOTED"
    assert db.scalar(select(func.count()).select_from(Watch)) == baseline_watch_count

    second_run = db.get(AnalysisRun, second_check.analysis_run_id)
    extra_ids = {str(x) for x in second_run.extra_source_ids}
    assert str(UUID(b["id"])) in extra_ids
    assert str(UUID(c["id"])) in extra_ids
    assert second["attention_plan"]["disposition"] == "AWARE"

    checks = db.execute(
        select(WatchCheck).where(WatchCheck.watch_id == watch.id).order_by(WatchCheck.checked_at)
    ).scalars().all()
    assert [x.outcome for x in checks] == ["KEEP_ACTIVE", "PROMOTED"]

def test_watch_fire_api_returns_recheck_history(client, db, monkeypatch):
    import app.services.pipeline as pipeline_mod

    a = add_text(client, "Initial watch evidence.", title="watch-api-A")
    b = add_text(client, "Later evidence that is still insufficient.", title="watch-api-B")
    initial = analyze(client, a["id"])
    watch, trigger = _make_watch(db, initial)
    monkeypatch.setattr(pipeline_mod, "route", _watch_route)

    response = client.post(
        f"/watches/{watch.id}/triggers/{trigger.id}/fire",
        params={"source_id": b["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["check"]["outcome"] == "KEEP_ACTIVE"
    assert body["watch"]["status"] == "ACTIVE"
    assert len(body["watch"]["checks"]) == 1
    assert body["watch"]["checks"][0]["new_source_id"] == b["id"]
