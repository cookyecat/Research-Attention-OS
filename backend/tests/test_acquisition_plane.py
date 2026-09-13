from datetime import datetime, timezone

from sqlalchemy import select

from app.models.acquisition import (
    AcquisitionObservation,
    ExternalInformationItem,
    InformationSnapshot,
    SourceDefinition,
)
from app.services import acquisition
from app.services.acquisition import DiscoveredExternalItem, parse_rss_or_atom, poll_due_sources, poll_source
from app.services.ingestion import ingest_text


RSS = b'''<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example</title>
<item><title>New result</title><link>https://example.com/a</link><guid>item-a</guid><pubDate>Sun, 13 Sep 2026 02:00:00 GMT</pubDate></item>
</channel></rss>'''

ATOM = b'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example</title>
<entry><title>Atom result</title><id>tag:example.com,2026:b</id><updated>2026-09-13T03:00:00Z</updated><link href="https://example.com/b" /></entry>
</feed>'''


def test_rss_and_atom_discovery_parse_to_external_information():
    rss = parse_rss_or_atom(RSS, base_url="https://example.com/feed.xml")
    atom = parse_rss_or_atom(ATOM, base_url="https://example.com/atom.xml")
    assert [(x.title, x.ref, x.external_id) for x in rss] == [
        ("New result", "https://example.com/a", "item-a")
    ]
    assert rss[0].published_at == datetime(2026, 9, 13, 2, 0, tzinfo=timezone.utc)
    assert [(x.title, x.ref) for x in atom] == [("Atom result", "https://example.com/b")]


def _fake_delivery(monkeypatch):
    analyses = []

    def fake_ingest_url(db, url):
        row = ingest_text(db, f"Fetched body for {url}", title=f"Article {url}")
        row.canonical_url = url
        row.ingestion_method = "URL_FETCH"
        return row

    def fake_run_pipeline(db, source_id):
        analyses.append(str(source_id))
        return {"analysis_run": {"status": "COMPLETED"}}

    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest_url)
    monkeypatch.setattr(acquisition, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        acquisition.RSSAdapter,
        "discover",
        lambda self, locator: [
            DiscoveredExternalItem(
                ref="https://example.com/article-1",
                external_id="article-1",
                title="Article 1",
                published_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
            )
        ],
    )
    return analyses


def _source(db, name="Feed A", locator="https://example.com/feed-a.xml"):
    row = SourceDefinition(name=name, source_type="RSS", locator=locator, poll_interval_seconds=1800)
    db.add(row)
    db.flush()
    return row


def test_repeated_poll_is_idempotent_at_information_and_snapshot_layer(db, monkeypatch):
    analyses = _fake_delivery(monkeypatch)
    source = _source(db)

    first = poll_source(db, source, limit=5, analyze=True)
    second = poll_source(db, source, limit=5, analyze=True)

    assert first["new_items"] == 1
    assert first["new_observations"] == 1
    assert first["new_snapshots"] == 1
    assert second["new_items"] == 0
    assert second["new_observations"] == 0
    assert second["new_snapshots"] == 0
    assert len(db.execute(select(ExternalInformationItem)).scalars().all()) == 1
    assert len(db.execute(select(AcquisitionObservation)).scalars().all()) == 1
    assert len(db.execute(select(InformationSnapshot)).scalars().all()) == 1
    assert len(analyses) == 1


def test_same_information_from_two_sources_is_one_item_two_observations(db, monkeypatch):
    analyses = _fake_delivery(monkeypatch)
    feed_a = _source(db, "Feed A", "https://example.com/feed-a.xml")
    feed_b = _source(db, "Feed B", "https://example.com/feed-b.xml")

    poll_source(db, feed_a, analyze=True)
    poll_source(db, feed_b, analyze=True)

    items = db.execute(select(ExternalInformationItem)).scalars().all()
    observations = db.execute(select(AcquisitionObservation)).scalars().all()
    snapshots = db.execute(select(InformationSnapshot)).scalars().all()
    assert len(items) == 1
    assert len(observations) == 2
    assert {row.source_definition_id for row in observations} == {feed_a.id, feed_b.id}
    assert len(snapshots) == 1
    assert len(analyses) == 1


def test_source_definition_can_be_managed_without_touching_cognition(client):
    created = client.post(
        "/acquisition/sources",
        json={
            "name": "Managed Feed",
            "source_type": "RSS",
            "locator": "https://example.com/feed.xml",
            "poll_interval_seconds": 600,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()
    updated = client.patch(
        f"/acquisition/sources/{row['id']}",
        json={"enabled": False, "poll_interval_seconds": 3600},
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["enabled"] is False
    assert body["poll_interval_seconds"] == 3600
    listed = client.get("/acquisition/sources")
    assert listed.status_code == 200
    assert any(item["id"] == row["id"] for item in listed.json())


def test_first_due_poll_bootstraps_without_cognitive_analysis(db, monkeypatch):
    analyses = _fake_delivery(monkeypatch)
    source = _source(db, "Bootstrap Feed", "https://example.com/bootstrap.xml")

    results = poll_due_sources(db, limit_per_source=5, analyze=True)

    assert len(results) == 1
    assert results[0]["status"] == "OK"
    assert results[0]["bootstrap"] is True
    assert results[0]["new_snapshots"] == 1
    assert analyses == []
    assert source.last_polled_at is not None


def test_one_broken_source_does_not_stop_other_due_sources(db, monkeypatch):
    analyses = []

    def fake_discover(self, locator):
        if "broken" in locator:
            raise RuntimeError("feed unavailable")
        return [DiscoveredExternalItem(ref="https://example.com/good-article", title="Good")]

    def fake_ingest_url(db, url):
        row = ingest_text(db, f"Fetched body for {url}", title="Good article")
        row.canonical_url = url
        return row

    monkeypatch.setattr(acquisition.RSSAdapter, "discover", fake_discover)
    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest_url)
    monkeypatch.setattr(acquisition, "run_pipeline", lambda db, source_id: analyses.append(str(source_id)))
    broken = _source(db, "Broken", "https://example.com/broken.xml")
    good = _source(db, "Good", "https://example.com/good.xml")

    results = poll_due_sources(db, limit_per_source=5, analyze=True)
    by_name = {row["source_name"]: row for row in results}

    assert by_name["Broken"]["status"] == "ERROR"
    assert by_name["Good"]["status"] == "OK"
    assert by_name["Good"]["bootstrap"] is True
    assert broken.last_polled_at is not None
    assert good.last_polled_at is not None
    assert analyses == []
