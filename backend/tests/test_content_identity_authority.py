from __future__ import annotations

from app.enums import DetectedBy, SourceEdgeRelationship
from app.models.source import Source, SourceEdge
from app.services.continuous_attention import _evidence_class
from app.services.fingerprint import content_hash
from app.services.information_landscape import source_information_landscape
from app.services.ingestion import attach_or_create_event
from app.services.source_graph import (
    freeze_analysis_relational_context,
    link_near_duplicates,
    source_content_identity_eligible,
    source_edge_authority_eligible,
)


def _source(db, *, title: str, text: str, scope: str | None = None):
    raw = {}
    if scope is not None:
        raw["content_scope"] = scope
    row = Source(
        source_type="VIDEO" if scope == "METADATA_ONLY" else "TEXT",
        title=title,
        canonical_url=f"https://example.test/{title.replace(' ', '-')}",
        content_text=text,
        fingerprint=f"fp:{title}",
        content_hash=content_hash(text),
        ingestion_method="TEST",
        raw_metadata=raw,
    )
    db.add(row)
    db.flush()
    return row


def test_metadata_only_placeholder_hash_cannot_create_repost_authority(db):
    a = _source(db, title="Video A", text="-", scope="METADATA_ONLY")
    b = _source(db, title="Video B", text="-", scope="METADATA_ONLY")

    assert a.content_hash == b.content_hash
    assert source_content_identity_eligible(a) is False
    assert source_content_identity_eligible(b) is False

    linked = link_near_duplicates(db, b)
    assert linked == []
    assert db.query(SourceEdge).count() == 0


def test_historical_placeholder_repost_edge_is_quarantined_from_current_independence(db):
    a = _source(db, title="Video A", text="-", scope="METADATA_ONLY")
    b = _source(db, title="Video B", text="-", scope="METADATA_ONLY")
    edge = SourceEdge(
        source_id=b.id,
        target_id=a.id,
        relationship=SourceEdgeRelationship.REPOSTS,
        confidence=0.9,
        detected_by=DetectedBy.METADATA,
        evidence="identical content_hash",
    )
    db.add(edge)
    db.flush()

    assert source_edge_authority_eligible(db, edge) is False
    ctx = freeze_analysis_relational_context(db, [a.id, b.id])
    assert ctx.independent_sources == 2
    assert ctx.secondary_reports == 0
    assert ctx.facts == ()


def test_historical_placeholder_repost_edge_does_not_create_landscape_coverage(db):
    a = _source(db, title="Video A", text="-", scope="METADATA_ONLY")
    b = _source(db, title="Video B", text="-", scope="METADATA_ONLY")
    db.add(
        SourceEdge(
            source_id=a.id,
            target_id=b.id,
            relationship=SourceEdgeRelationship.REPOSTS,
            confidence=0.9,
            detected_by=DetectedBy.METADATA,
            evidence="identical content_hash",
        )
    )
    db.flush()

    landscape = source_information_landscape(db, a.id)
    assert landscape["coverage"]["other_source_count"] == 0
    assert landscape["coverage"]["independence"]["independent_sources"] == 1


def test_watch_duplicate_class_ignores_metadata_only_placeholder_hash(db):
    a = _source(db, title="Video A", text="-", scope="METADATA_ONLY")
    b = _source(db, title="Video B", text="-", scope="METADATA_ONLY")
    assert _evidence_class(db, b, [a.id]) == "INDEPENDENT"


def test_legacy_event_fallback_ignores_metadata_only_placeholder_hash(db):
    a = _source(db, title="Video A", text="-", scope="METADATA_ONLY")
    b = _source(db, title="Video B", text="-", scope="METADATA_ONLY")

    event_a = attach_or_create_event(db, a, "Event A", "A")
    event_b = attach_or_create_event(db, b, "Event B", "B")
    assert event_a.id != event_b.id


def test_substantive_identical_content_still_supports_duplicate_relation(db):
    text = "A substantive report describing the same concrete publication event."
    a = _source(db, title="Report A", text=text)
    b = _source(db, title="Report B", text=text)

    assert source_content_identity_eligible(a) is True
    assert source_content_identity_eligible(b) is True
    linked = link_near_duplicates(db, b)
    assert [row.id for row in linked] == [a.id]

    edge = db.query(SourceEdge).one()
    assert source_edge_authority_eligible(db, edge) is True
    ctx = freeze_analysis_relational_context(db, [a.id, b.id])
    assert ctx.independent_sources == 1
    assert ctx.secondary_reports == 1
    assert len(ctx.facts) == 1
    assert _evidence_class(db, b, [a.id]) == "DUPLICATE"
