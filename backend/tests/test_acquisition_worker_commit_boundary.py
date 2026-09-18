from app import acquisition_worker


def test_worker_defers_requested_cognition_until_after_observation_commit(monkeypatch):
    calls = {}

    class FakeSession:
        def commit(self): calls["committed"] = True
        def rollback(self): calls["rolled_back"] = True
        def close(self): calls["closed"] = True

    fake_session = FakeSession()

    def fake_poll(db, *, limit_per_source, analyze, cognition_defer_reason):
        calls.update(
            db=db,
            limit_per_source=limit_per_source,
            analyze=analyze,
            cognition_defer_reason=cognition_defer_reason,
        )
        return [{"status": "OK"}]

    monkeypatch.setattr("app.db.SessionLocal", lambda: fake_session)
    monkeypatch.setattr("app.services.acquisition.poll_due_sources", fake_poll)

    result = acquisition_worker.run_once(limit_per_source=3, analyze=True)
    assert result == [{"status": "OK"}]
    assert calls["analyze"] is False
    assert calls["cognition_defer_reason"] == "post_commit_cognition"
    assert calls["committed"] is True
    assert calls["closed"] is True


def test_sqlite_writer_contention_is_transient_but_other_errors_are_not():
    from sqlalchemy.exc import OperationalError

    locked = OperationalError(
        "UPDATE acquisition_sources SET last_polled_at=?",
        {},
        Exception("database is locked"),
    )
    assert acquisition_worker._is_sqlite_writer_contention(locked) is True
    assert acquisition_worker._is_sqlite_writer_contention(RuntimeError("network failed")) is False
