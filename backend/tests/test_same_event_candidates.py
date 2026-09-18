from sqlalchemy import func, select

from app.models.event import EventSource
from app.models.source import SourceEdge
from app.services.ingestion import ingest_text
from app.services.same_event_candidates import same_event_candidates


def test_same_event_candidate_retrieval_is_shadow_only_and_ranks_plausible_pair(db):
    primary = ingest_text(
        db,
        "Google introduced a new family coordination agent.",
        title='Google announces new experimental "CC" AI agent for families',
        publisher="Ars Technica",
    )
    plausible = ingest_text(
        db,
        "Google described CC for families and groups.",
        title="CC is an AI agent for families and groups",
        publisher="Google",
    )
    unrelated = ingest_text(
        db,
        "A genomics transfer learning result.",
        title="Transfer learning for genomic prediction in underrepresented populations",
        publisher="Google Research",
    )
    db.flush()

    edge_count_before = db.scalar(select(func.count()).select_from(SourceEdge))
    event_link_count_before = db.scalar(select(func.count()).select_from(EventSource))

    result = same_event_candidates(db, primary.id, limit=10)

    assert result["mode"] == "SHADOW_CANDIDATE_RETRIEVAL"
    assert result["authority"] == "NONE"
    assert result["mutates_graph"] is False
    ids = [row["source_id"] for row in result["candidates"]]
    assert str(plausible.id) in ids
    assert ids.index(str(plausible.id)) < ids.index(str(unrelated.id))
    plausible_row = next(row for row in result["candidates"] if row["source_id"] == str(plausible.id))
    assert plausible_row["features"]["title_sequence"] > 0.4

    assert db.scalar(select(func.count()).select_from(SourceEdge)) == edge_count_before
    assert db.scalar(select(func.count()).select_from(EventSource)) == event_link_count_before
