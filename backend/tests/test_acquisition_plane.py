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


def test_inline_public_content_change_creates_new_snapshot(client, db, monkeypatch):
    source = SourceDefinition(name="Weibo test", source_type="WEIBO_PUBLIC", locator="1912085257", poll_interval_seconds=1800)
    db.add(source)
    db.flush()
    payload = {"text": "预览正文"}

    def discover(self, locator):
        return [DiscoveredExternalItem(
            ref="https://weibo.com/1912085257/AbCd",
            external_id="456",
            title="微博测试",
            metadata={
                "content_text": payload["text"],
                "social_author": "测试用户",
                "hero_image_url": "https://example.com/hero.jpg",
            },
        )]

    monkeypatch.setattr(acquisition.WeiboPublicAdapter, "discover", discover)
    monkeypatch.setattr(acquisition, "cache_remote_media", lambda url: "/api/media/cached-hero.jpg")
    first = poll_source(db, source, analyze=False)
    payload["text"] = "完整正文\n\n第二段"
    second = poll_source(db, source, analyze=False)

    snapshots = db.execute(select(InformationSnapshot).order_by(InformationSnapshot.captured_at)).scalars().all()
    assert first["new_snapshots"] == 1
    assert second["new_snapshots"] == 1
    assert len(snapshots) == 2
    assert len(db.execute(select(AcquisitionObservation)).scalars().all()) == 1
    current = db.get(acquisition.Source, snapshots[-1].raos_source_id)
    assert current.content_text == "完整正文\n\n第二段"
    assert current.raw_metadata["hero_image_cached_url"] == "/api/media/cached-hero.jpg"
    listed_ids = {row["id"] for row in client.get("/sources").json()}
    assert str(snapshots[-1].raos_source_id) in listed_ids
    assert str(snapshots[0].raos_source_id) not in listed_ids
    old_detail = client.get(f"/sources/{snapshots[0].raos_source_id}").json()
    assert old_detail["id"] == str(snapshots[-1].raos_source_id)
    assert old_detail["content_text"] == "完整正文\n\n第二段"


def test_inline_media_hydration_does_not_create_new_snapshot_or_require_reanalysis(db, monkeypatch):
    source = SourceDefinition(name="Weibo media hydrate", source_type="WEIBO_PUBLIC", locator="1912085257", poll_interval_seconds=1800)
    db.add(source)
    db.flush()
    state = {"with_media": False}

    def discover(self, locator):
        metadata = {"content_text": "正文不变", "social_author": "测试用户"}
        if state["with_media"]:
            metadata.update({
                "hero_image_url": "https://example.com/p1.jpg",
                "media_assets": [{"type": "IMAGE", "url": "https://example.com/p1.jpg", "media_id": "p1"}],
                "weibo_media_hydrated": True,
            })
        return [DiscoveredExternalItem(ref="https://weibo.com/1912085257/Hydrate1", external_id="h1", title="媒体补全", metadata=metadata)]

    monkeypatch.setattr(acquisition.WeiboPublicAdapter, "discover", discover)
    monkeypatch.setattr(acquisition, "cache_remote_media", lambda url: "/api/media/p1.jpg")
    first = poll_source(db, source, analyze=False)
    state["with_media"] = True
    second = poll_source(db, source, analyze=False)

    snapshots = db.execute(select(InformationSnapshot)).scalars().all()
    assert first["new_snapshots"] == 1
    assert second["new_snapshots"] == 0
    assert len(snapshots) == 1
    current = db.get(acquisition.Source, snapshots[0].raos_source_id)
    assert current.raw_metadata["media_assets"][0]["cached_url"] == "/api/media/p1.jpg"
    assert current.raw_metadata["weibo_media_hydrated"] is True
    assert current.raw_metadata["media_hydration"]["version"] == "social-media-v1"


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


def test_one_broken_item_does_not_stop_sibling_items(db, monkeypatch):
    source = _source(db, "Mixed Feed", "https://example.com/mixed.xml")
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [
        DiscoveredExternalItem(ref="https://example.com/bad", title="Bad"),
        DiscoveredExternalItem(ref="https://example.com/good", title="Good"),
    ])
    def fake_ingest(db, url):
        if url.endswith("/bad"):
            raise RuntimeError("article fetch failed")
        row = ingest_text(db, "Good body", title="Good")
        row.canonical_url = url
        return row
    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest)
    result = poll_source(db, source, analyze=False)
    assert result["item_failures"] == 1
    assert result["new_snapshots"] == 1
    assert result["item_errors"][0]["title"] == "Bad"


def test_feed_content_fallback_preserves_item_when_page_fetch_fails(db, monkeypatch):
    source = _source(db, "Fallback Feed", "https://example.com/fallback.xml")
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [
        DiscoveredExternalItem(ref="https://example.com/blocked", title="Blocked", metadata={
            "feed_format": "RSS", "feed_content_text": "Publisher supplied summary text."
        })
    ])
    monkeypatch.setattr(acquisition, "ingest_url", lambda db, url: (_ for _ in ()).throw(RuntimeError("403")))
    result = poll_source(db, source, analyze=False)
    snapshot = db.execute(select(InformationSnapshot)).scalar_one()
    from app.models.source import Source
    stored = db.get(Source, snapshot.raos_source_id)
    assert result["new_snapshots"] == 1
    assert stored.ingestion_method == "RSS_FALLBACK"
    assert stored.content_text == "Publisher supplied summary text."
    assert stored.raw_metadata["feed_fallback"] is True




def test_feed_fallback_recovers_to_full_body_on_later_poll(db, monkeypatch):
    source = _source(db, "Recovering Feed", "https://example.com/recovering.xml")
    item = DiscoveredExternalItem(
        ref="https://example.com/article",
        title="Article",
        metadata={"feed_format": "RSS", "feed_content_text": "Publisher summary."},
    )
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [item])
    calls = {"n": 0}

    def fake_ingest(db, url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary 403")
        row = ingest_text(db, "Full recovered article body.", title="Article")
        row.canonical_url = url
        return row

    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest)
    first = poll_source(db, source, analyze=False)
    second = poll_source(db, source, analyze=False)

    snapshots = db.execute(select(InformationSnapshot).order_by(InformationSnapshot.captured_at)).scalars().all()
    from app.models.source import Source
    assert first["new_snapshots"] == 1
    assert second["new_snapshots"] == 1
    assert len(snapshots) == 2
    old = db.get(Source, snapshots[0].raos_source_id)
    new = db.get(Source, snapshots[1].raos_source_id)
    assert old.raw_metadata["feed_fallback"] is True
    assert old.content_text == "Publisher summary."
    assert new.content_text == "Full recovered article body."
    assert snapshots[1].snapshot_metadata["recovered_from_feed_fallback"] is True
    assert snapshots[1].snapshot_metadata["previous_snapshot_id"] == str(snapshots[0].id)


def test_feed_fallback_retry_failure_keeps_existing_snapshot(db, monkeypatch):
    source = _source(db, "Still Blocked Feed", "https://example.com/still-blocked.xml")
    item = DiscoveredExternalItem(
        ref="https://example.com/blocked",
        title="Blocked",
        metadata={"feed_format": "RSS", "feed_content_text": "Publisher summary."},
    )
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [item])
    monkeypatch.setattr(acquisition, "ingest_url", lambda db, url: (_ for _ in ()).throw(RuntimeError("still 403")))

    first = poll_source(db, source, analyze=False)
    second = poll_source(db, source, analyze=False)
    snapshots = db.execute(select(InformationSnapshot)).scalars().all()
    assert first["new_snapshots"] == 1
    assert second["new_snapshots"] == 0
    assert len(snapshots) == 1
    meta = snapshots[0].snapshot_metadata
    assert "still 403" in meta["fallback_recovery_last_error"]
    assert meta["fallback_recovery_last_attempt_at"]


def test_cognition_failure_preserves_snapshot_for_reconciliation(db, monkeypatch):
    source = _source(db, "Recoverable Feed", "https://example.com/recoverable.xml")
    source.last_polled_at = datetime(2026, 9, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [
        DiscoveredExternalItem(ref="https://example.com/recoverable-item", title="Recoverable")
    ])

    def fake_ingest(db, url):
        row = ingest_text(db, "Recoverable body", title="Recoverable")
        row.canonical_url = url
        return row

    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest)
    monkeypatch.setattr(
        acquisition,
        "run_pipeline",
        lambda db, source_id: (_ for _ in ()).throw(RuntimeError("canonical cognition unavailable")),
    )

    result = poll_source(db, source, analyze=True)
    snapshots = db.execute(select(InformationSnapshot)).scalars().all()

    assert result["new_snapshots"] == 1
    assert result["item_failures"] == 0
    assert len(snapshots) == 1
    meta = snapshots[0].snapshot_metadata
    assert meta["cognition_deferred"] is True
    assert meta["cognition_reconcile_eligible"] is True
    assert meta["cognition_defer_reason"] == "technical_cognition_failure"
    assert "canonical cognition unavailable" in meta["last_cognition_error"]


def test_operator_no_analyze_marks_genuine_arrival_recoverable(db, monkeypatch):
    source = _source(db, "Deferred Feed", "https://example.com/deferred.xml")
    source.last_polled_at = datetime(2026, 9, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [
        DiscoveredExternalItem(ref="https://example.com/deferred-item", title="Deferred")
    ])
    monkeypatch.setattr(acquisition, "ingest_url", lambda db, url: ingest_text(db, "Deferred body", title="Deferred"))

    result = poll_source(
        db,
        source,
        analyze=False,
        cognition_defer_reason="execution_integrity_deferred",
    )
    snapshot = db.execute(select(InformationSnapshot)).scalar_one()

    assert result["new_snapshots"] == 1
    assert snapshot.snapshot_metadata["cognition_deferred"] is True
    assert snapshot.snapshot_metadata["cognition_reconcile_eligible"] is True
    assert snapshot.snapshot_metadata["cognition_defer_reason"] == "execution_integrity_deferred"


def test_bootstrap_is_deferred_but_not_reconciliation_eligible(db, monkeypatch):
    _fake_delivery(monkeypatch)
    source = _source(db, "Baseline Feed", "https://example.com/baseline.xml")

    results = poll_due_sources(db, limit_per_source=5, analyze=True)
    snapshot = db.execute(select(InformationSnapshot)).scalar_one()

    assert results[0]["bootstrap"] is True
    assert snapshot.snapshot_metadata["cognition_deferred"] is True
    assert snapshot.snapshot_metadata["cognition_reconcile_eligible"] is False
    assert snapshot.snapshot_metadata["cognition_defer_reason"] == "baseline"


def test_user_source_surface_excludes_graph_stubs_and_metadata_only(client, db):
    visible = ingest_text(
        db,
        "Readable source body",
        title="Readable source",
    )
    graph_stub = ingest_text(
        db,
        "Internal graph node",
        title="Internal reference node",
    )
    graph_stub.ingestion_method = "REFERENCE_STUB"

    metadata_only = ingest_text(
        db,
        "Discovery metadata only",
        title="Metadata-only discovery",
    )
    metadata_only.ingestion_method = "BILIBILI_SEARCH"
    metadata_only.raw_metadata = {
        **(metadata_only.raw_metadata or {}),
        "content_scope": "METADATA_ONLY",
    }
    db.flush()

    listed_ids = {
        row["id"]
        for row in client.get("/sources?compact=true").json()
    }
    assert str(visible.id) in listed_ids
    assert str(graph_stub.id) not in listed_ids
    assert str(metadata_only.id) not in listed_ids

    graph_search = client.get(
        "/sources/search?q=Internal%20reference%20node"
    ).json()
    metadata_search = client.get(
        "/sources/search?q=Metadata-only%20discovery"
    ).json()
    assert graph_search == []
    assert metadata_search == []
