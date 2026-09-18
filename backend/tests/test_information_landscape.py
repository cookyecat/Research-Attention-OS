from app.enums import SourceEdgeRelationship
from app.models.event import Event, EventSource
from app.services.information_landscape import source_information_landscape
from app.services.ingestion import ingest_text
from app.services.source_graph import persist_source_edge


def test_information_landscape_separates_coverage_from_related_and_keeps_p_unauthorized(db):
    primary = ingest_text(db, "Vivo announced a new AI phone agent architecture.", title="Vivo AI phone launch")
    derivative = ingest_text(db, "A media outlet rewrites the Vivo launch announcement.", title="Vivo launch coverage")
    independent = ingest_text(db, "Independent reporting from the Vivo event.", title="Vivo event report")
    related = ingest_text(db, "A separate article discusses AI-phone agent design.", title="AI phone design discussion")

    event = Event(
        title="Vivo announces AI phone agent architecture",
        event_type="PRODUCT_ANNOUNCEMENT",
        summary="One world event covered by several sources.",
        confidence=0.92,
        status="CONFIRMED",
    )
    db.add(event)
    db.flush()
    db.add_all([
        EventSource(event_id=event.id, source_id=primary.id, relationship="PRIMARY", confidence=0.95),
        EventSource(event_id=event.id, source_id=derivative.id, relationship="REPORTS", confidence=0.9),
        EventSource(event_id=event.id, source_id=independent.id, relationship="REPORTS", confidence=0.85),
    ])
    db.flush()

    persist_source_edge(
        db,
        derivative.id,
        primary.id,
        SourceEdgeRelationship.DERIVED_FROM,
        confidence=0.96,
        detected_by="AI",
        evidence="The derivative article explicitly follows the launch announcement.",
    )
    persist_source_edge(
        db,
        related.id,
        primary.id,
        SourceEdgeRelationship.DISCUSSES,
        confidence=0.8,
        detected_by="AI",
        evidence="Same technical area, different event.",
    )

    landscape = source_information_landscape(db, primary.id)

    assert landscape["event"]["title"] == "Vivo announces AI phone agent architecture"
    assert landscape["coverage"]["source_count"] == 3
    assert landscape["coverage"]["other_source_count"] == 2
    assert {row["source_id"] for row in landscape["coverage"]["sources"]} == {
        str(derivative.id),
        str(independent.id),
    }
    assert landscape["coverage"]["independence"] == {
        "independent_sources": 2,
        "secondary_reports": 1,
        "independent_source_ids": [str(primary.id), str(independent.id)],
        "secondary_source_ids": [str(derivative.id)],
    }
    derivative_row = next(row for row in landscape["coverage"]["sources"] if row["source_id"] == str(derivative.id))
    assert derivative_row["relationship"] == "DERIVED_FROM"

    assert landscape["related"]["count"] == 1
    assert landscape["related"]["sources"][0]["source_id"] == str(related.id)
    assert landscape["related"]["sources"][0]["relationship"] == "DISCUSSES"
    assert landscape["p_input_status"] == "NOT_YET_AUTHORIZED"


def test_information_landscape_does_not_guess_same_event_without_persisted_facts(db):
    source = ingest_text(db, "One article about an AI phone.", title="AI phone article")
    other = ingest_text(db, "Another similarly titled article about an AI phone.", title="AI phone article analysis")

    landscape = source_information_landscape(db, source.id)

    assert landscape["event"] is None
    assert landscape["coverage"]["source_count"] == 1
    assert landscape["coverage"]["other_source_count"] == 0
    assert landscape["coverage"]["sources"] == []
    assert landscape["related"]["count"] == 0
    assert str(other.id) not in {row["source_id"] for row in landscape["coverage"]["sources"]}


def test_candidate_event_cluster_is_not_user_visible_coverage_without_authority(db):
    primary = ingest_text(db, "A candidate story about a new AI product.", title="Candidate story A")
    other = ingest_text(db, "A second article that was tentatively grouped.", title="Candidate story B")
    event = Event(
        title="Tentative AI product story",
        event_type="PRODUCT_ANNOUNCEMENT",
        summary="Unreviewed same-event candidate.",
        confidence=0.6,
        status="CANDIDATE",
    )
    db.add(event)
    db.flush()
    db.add_all([
        EventSource(event_id=event.id, source_id=primary.id, relationship="REPORTS", confidence=0.6),
        EventSource(event_id=event.id, source_id=other.id, relationship="REPORTS", confidence=0.6),
    ])
    db.flush()

    landscape = source_information_landscape(db, primary.id)

    assert landscape["event"] is None
    assert landscape["events"][0]["coverage_authorized"] is False
    assert landscape["coverage"]["source_count"] == 1
    assert landscape["coverage"]["other_source_count"] == 0
    assert landscape["coverage"]["sources"] == []


def test_information_landscape_exposes_explicit_cites_as_provenance_not_coverage(db):
    primary = ingest_text(db, "An article explicitly links an official source.", title="Secondary article")
    official = ingest_text(db, "Official source body.", title="Official source")
    official.canonical_url = "https://official.example/story"
    db.flush()

    persist_source_edge(
        db,
        primary.id,
        official.id,
        SourceEdgeRelationship.CITES,
        confidence=1.0,
        detected_by="PARSER",
        evidence="Official source",
    )
    db.flush()

    landscape = source_information_landscape(db, primary.id)

    assert landscape["coverage"]["other_source_count"] == 0
    assert landscape["related"]["count"] == 0
    assert landscape["references"]["count"] == 1
    ref = landscape["references"]["sources"][0]
    assert ref["source_id"] == str(official.id)
    assert ref["relationship"] == "CITES"
    assert ref["canonical_url"] == "https://official.example/story"
    assert ref["detected_by"] == "PARSER"
    assert landscape["provenance"]["relationship_authority"] == "literal-link-only"
    assert landscape["p_input_status"] == "NOT_YET_AUTHORIZED"
