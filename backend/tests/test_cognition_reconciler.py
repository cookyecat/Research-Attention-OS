from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.cognition_reconciler import reconcile_once
from app.models.acquisition import ExternalInformationItem, InformationSnapshot
from app.models.source import Source


def test_reconciler_skips_deferred_snapshot_without_content(engine, db, monkeypatch):
    source = Source(
        source_type="URL",
        title="Metadata-only source",
        canonical_url="https://example.invalid/metadata-only",
        content_text=None,
        fingerprint="metadata-only-source",
        content_hash=None,
        ingestion_method="TEST",
        raw_metadata={},
    )
    db.add(source)
    db.flush()
    item = ExternalInformationItem(
        identity_key="metadata-only-item",
        item_type="ARTICLE",
        canonical_url=source.canonical_url,
        title=source.title,
        published_at=None,
    )
    db.add(item)
    db.flush()
    snapshot = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=source.id,
        content_hash=None,
        snapshot_metadata={
            "cognition_deferred": True,
            "cognition_reconcile_eligible": True,
            "cognition_defer_reason": "post_commit_cognition",
        },
    )
    db.add(snapshot)
    db.commit()

    import app.db as db_module
    import app.execution_integrity as integrity
    import app.services.pipeline as pipeline

    monkeypatch.setattr(
        db_module,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False),
    )
    monkeypatch.setattr(
        integrity,
        "health_contract",
        lambda: {
            "attestation": {"enforced": True},
            "capabilities": {"cognition": "READY"},
        },
    )
    called = []

    def should_not_run(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("pipeline must not run for contentless Source")

    monkeypatch.setattr(pipeline, "run_pipeline", should_not_run)

    result = reconcile_once(limit=20)

    assert result["eligible"] == 0
    assert result["failed"] == 0
    assert result["skipped_unanalyzable"] == 1
    assert called == []

    db.expire_all()
    updated = db.get(InformationSnapshot, snapshot.id)
    meta = dict(updated.snapshot_metadata or {})
    assert meta["cognition_deferred"] is False
    assert meta["cognition_reconcile_eligible"] is False
    assert meta["reconciliation_outcome"] == "skipped_unanalyzable_no_content"
