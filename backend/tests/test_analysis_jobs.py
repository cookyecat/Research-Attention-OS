from uuid import uuid4

import app.services.analysis_jobs as jobs


def _reset_jobs():
    with jobs._lock:
        jobs._jobs.clear()
        jobs._active.clear()


def test_enqueue_analysis_job_deduplicates_active_work():
    _reset_jobs()
    source_id = uuid4()
    first, dispatch_first = jobs.enqueue_analysis_job(source_id=source_id, reprocess=False)
    second, dispatch_second = jobs.enqueue_analysis_job(source_id=source_id, reprocess=False)

    assert dispatch_first is True
    assert dispatch_second is False
    assert first["id"] == second["id"]
    assert second["status"] == "QUEUED"


def test_analysis_job_endpoint_returns_before_cognition(client, monkeypatch):
    _reset_jobs()
    source = client.post(
        "/sources",
        json={"source_type": "TEXT", "title": "Async cognition", "content_text": "A source saved before cognition."},
    ).json()

    monkeypatch.setattr(jobs, "run_analysis_job", lambda *args, **kwargs: None)
    response = client.post("/analysis/jobs", json={"source_id": source["id"]})

    assert response.status_code == 202
    payload = response.json()
    assert payload["source_id"] == source["id"]
    assert payload["status"] == "QUEUED"
    status = client.get(f"/analysis/jobs/{payload['id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "QUEUED"

def test_enqueue_analysis_job_deduplicates_analyze_and_reprocess_for_same_source():
    _reset_jobs()
    source_id = uuid4()
    analyze, dispatch_analyze = jobs.enqueue_analysis_job(source_id=source_id, reprocess=False)
    reprocess, dispatch_reprocess = jobs.enqueue_analysis_job(source_id=source_id, reprocess=True)

    assert dispatch_analyze is True
    assert dispatch_reprocess is False
    assert analyze["id"] == reprocess["id"]
    assert reprocess["mode"] == "ANALYZE"


def test_active_job_endpoint_recovers_source_state_after_client_refresh(client, monkeypatch):
    _reset_jobs()
    source = client.post(
        "/sources",
        json={"source_type": "TEXT", "title": "Refresh-safe cognition", "content_text": "Saved before analysis."},
    ).json()
    monkeypatch.setattr(jobs, "run_analysis_job", lambda *args, **kwargs: None)

    queued = client.post("/analysis/jobs", json={"source_id": source["id"]})
    assert queued.status_code == 202
    job = queued.json()

    active = client.get(f"/analysis/jobs/source/{source['id']}/active")
    assert active.status_code == 200
    payload = active.json()
    assert payload["active"] is True
    assert payload["job"]["id"] == job["id"]
    assert payload["job"]["status"] == "QUEUED"


def test_active_job_endpoint_returns_inactive_when_none(client):
    _reset_jobs()
    source = client.post(
        "/sources",
        json={"source_type": "TEXT", "title": "Idle cognition", "content_text": "No job yet."},
    ).json()

    active = client.get(f"/analysis/jobs/source/{source['id']}/active")
    assert active.status_code == 200
    assert active.json() == {"active": False, "job": None}

