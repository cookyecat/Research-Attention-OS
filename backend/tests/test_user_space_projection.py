from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select

from app.models.source import Source
from app.models.user_space import (
    ProjectionOutbox,
    SourceSurfaceProjection,
    UserAttentionProjection,
)
from app.services.user_space_projection import (
    process_projection_outbox,
    projection_status,
    rebuild_user_space_projections,
)


def _drain_projection(db) -> dict:
    total = 0
    while True:
        processed = process_projection_outbox(
            db,
            limit=1000,
        )
        if not processed:
            break
        total += processed
    db.commit()
    status = projection_status(db)
    assert status["pending_outbox"] == 0
    status["processed_this_drain"] = total
    return status


def test_user_space_inbox_excludes_reference_stubs_and_paginates(
    client,
    db,
):
    created = []
    for index in range(3):
        response = client.post(
            "/sources",
            json={
                "source_type": "TEXT",
                "title": f"Readable source {index}",
                "content_text": f"Readable body {index}",
            },
        )
        assert response.status_code == 200
        created.append(response.json()["id"])

    stub = Source(
        source_type="URL",
        title="Privacy Policy",
        canonical_url=f"https://example.com/{uuid4()}",
        content_text=None,
        fingerprint=f"stub-{uuid4()}",
        content_hash=None,
        ingestion_method="REFERENCE_STUB",
        raw_metadata={"stub": True},
        publisher=None,
    )
    db.add(stub)
    db.commit()

    status = _drain_projection(db)
    assert status["source_surface_count"] == 3
    assert status["processed_this_drain"] >= 3

    first = client.get("/user-space/inbox?limit=2")
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["contract"] == "user-space-inbox-v0.3"
    assert payload["page_size"] == 2
    assert payload["next_cursor"]
    assert all(
        row["source_id"] != str(stub.id)
        for row in payload["items"]
    )

    second = client.get(
        "/user-space/inbox",
        params={
            "limit": 2,
            "cursor": payload["next_cursor"],
        },
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    visible_ids = {
        row["source_id"]
        for row in payload["items"] + second_payload["items"]
    }
    assert set(created).issubset(visible_ids)
    assert str(stub.id) not in visible_ids


def test_user_space_attention_preserves_event_identity_but_returns_source_card(
    client,
    db,
):
    source = client.post(
        "/sources",
        json={
            "source_type": "TEXT",
            "title": "User Space event projection probe",
            "content_text": (
                "A technical report about motor intelligence latency "
                "and energy tradeoffs."
            ),
        },
    ).json()

    analyzed = client.post(
        "/analysis/extract",
        json={
            "source_id": source["id"],
            "extra_source_ids": [],
        },
    )
    assert analyzed.status_code == 200, analyzed.text
    plan = analyzed.json()["attention_plan"]
    assert plan["candidate_type"] == "EVENT"

    status = _drain_projection(db)
    assert status["source_surface_count"] == 1
    assert status["user_attention_count"] == 1
    assert status["user_source_attention_count"] == 1

    response = client.get("/user-space/attention?limit=20")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["contract"] == "user-space-attention-v0.3"
    row = next(
        item
        for item in payload["items"]
        if item["attention_plan_id"] == plan["id"]
    )

    assert row["source_id"] == source["id"]
    assert row["event_id"] == plan["candidate_id"]
    assert row["attention_plan_id"] == plan["id"]
    assert row["disposition"] == plan["disposition"]
    assert "score_debug" not in row
    assert "content_text" not in row

    today = client.get("/user-space/today")
    assert today.status_code == 200, today.text
    today_payload = today.json()
    assert today_payload["contract"] == "user-space-today-v0.3"
    assert today_payload["current_attention_count"] >= 1
    assert (
        today_payload["counts"][plan["disposition"]]
        >= 1
    )
    assert len(today_payload["briefs"]) <= 6


def test_projection_outbox_is_idempotent_and_durable(
    client,
    db,
):
    response = client.post(
        "/sources",
        json={
            "source_type": "TEXT",
            "title": "Outbox idempotency",
            "content_text": "A durable projection trigger.",
        },
    )
    assert response.status_code == 200
    source_id = response.json()["id"]

    pending = list(
        db.execute(
            select(ProjectionOutbox).where(
                ProjectionOutbox.processed_at.is_(None)
            )
        ).scalars().all()
    )
    assert pending

    first = _drain_projection(db)
    assert first["source_surface_count"] == 1

    second = _drain_projection(db)
    assert second["processed_this_drain"] == 0
    assert second["source_surface_count"] == 1

    rows = list(
        db.execute(
            select(SourceSurfaceProjection)
        ).scalars().all()
    )
    assert [str(row.source_id) for row in rows] == [
        source_id
    ]


def test_rebuild_recovers_same_current_projection(
    client,
    db,
):
    sources = []
    for index in range(2):
        source = client.post(
            "/sources",
            json={
                "source_type": "TEXT",
                "title": f"Rebuild source {index}",
                "content_text": (
                    "Embodied intelligence latency "
                    f"measurement {index}."
                ),
            },
        ).json()
        sources.append(source)

    analyzed = client.post(
        "/analysis/extract",
        json={
            "source_id": sources[0]["id"],
            "extra_source_ids": [],
        },
    )
    assert analyzed.status_code == 200, analyzed.text

    _drain_projection(db)
    before_sources = [
        (
            str(row.source_id),
            row.surface_seq,
            str(row.current_event_id)
            if row.current_event_id
            else None,
        )
        for row in db.execute(
            select(SourceSurfaceProjection).order_by(
                SourceSurfaceProjection.surface_seq
            )
        ).scalars()
    ]
    before_attention = [
        (
            row.candidate_type,
            str(row.candidate_id),
            str(row.attention_plan_id),
            row.attention_seq,
            row.disposition,
        )
        for row in db.execute(
            select(UserAttentionProjection).order_by(
                UserAttentionProjection.attention_seq
            )
        ).scalars()
    ]

    first_status = rebuild_user_space_projections(db)
    db.commit()
    after_first_sources = [
        (
            str(row.source_id),
            row.surface_seq,
            str(row.current_event_id)
            if row.current_event_id
            else None,
        )
        for row in db.execute(
            select(SourceSurfaceProjection).order_by(
                SourceSurfaceProjection.surface_seq
            )
        ).scalars()
    ]
    after_first_attention = [
        (
            row.candidate_type,
            str(row.candidate_id),
            str(row.attention_plan_id),
            row.attention_seq,
            row.disposition,
        )
        for row in db.execute(
            select(UserAttentionProjection).order_by(
                UserAttentionProjection.attention_seq
            )
        ).scalars()
    ]

    second_status = rebuild_user_space_projections(db)
    db.commit()
    after_second_sources = [
        (
            str(row.source_id),
            row.surface_seq,
            str(row.current_event_id)
            if row.current_event_id
            else None,
        )
        for row in db.execute(
            select(SourceSurfaceProjection).order_by(
                SourceSurfaceProjection.surface_seq
            )
        ).scalars()
    ]
    after_second_attention = [
        (
            row.candidate_type,
            str(row.candidate_id),
            str(row.attention_plan_id),
            row.attention_seq,
            row.disposition,
        )
        for row in db.execute(
            select(UserAttentionProjection).order_by(
                UserAttentionProjection.attention_seq
            )
        ).scalars()
    ]

    assert before_sources == after_first_sources
    assert after_first_sources == after_second_sources
    assert before_attention == after_first_attention
    assert after_first_attention == after_second_attention
    assert first_status["source_surface_count"] == 2
    assert second_status["source_surface_count"] == 2


def test_new_snapshot_retires_old_source_surface(db):
    from datetime import datetime, timedelta, timezone

    from app.models.acquisition import (
        ExternalInformationItem,
        InformationSnapshot,
    )
    from app.services.ingestion import ingest_text
    from app.services.user_space_projection import (
        SNAPSHOT_CHANGED,
        enqueue_projection_change,
    )

    first = ingest_text(
        db,
        "First immutable version.",
        title="Versioned item",
    )
    second = ingest_text(
        db,
        "Second immutable version with changed body.",
        title="Versioned item",
    )
    item = ExternalInformationItem(
        identity_key=f"projection-test:{uuid4()}",
        item_type="ARTICLE",
        canonical_url="https://example.invalid/versioned",
        title="Versioned item",
    )
    db.add(item)
    db.flush()

    now = datetime.now(timezone.utc)
    snap1 = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=first.id,
        captured_at=now,
        content_hash=first.content_hash,
        snapshot_metadata={},
    )
    snap2 = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=second.id,
        captured_at=now + timedelta(seconds=1),
        content_hash=second.content_hash,
        snapshot_metadata={},
    )
    db.add_all([snap1, snap2])
    db.flush()
    enqueue_projection_change(
        db,
        SNAPSHOT_CHANGED,
        snap1.id,
    )
    enqueue_projection_change(
        db,
        SNAPSHOT_CHANGED,
        snap2.id,
    )
    db.commit()

    status = _drain_projection(db)
    assert status["source_surface_count"] == 1

    rows = list(
        db.execute(
            select(SourceSurfaceProjection)
        ).scalars().all()
    )
    assert [row.source_id for row in rows] == [
        second.id
    ]
