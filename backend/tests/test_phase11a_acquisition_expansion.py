from datetime import datetime, timezone

from sqlalchemy import select

from app.models.acquisition import AcquisitionObservation, ExternalInformationItem, InformationSnapshot, SourceDefinition
from app.models.source import Source
from app.services import acquisition
from app.services.acquisition import poll_due_sources, poll_source
from app.services.acquisition_types import DiscoveredExternalItem
from app.services.discovery_adapters import (
    parse_bilibili_creator_response,
    parse_bilibili_search_response,
    parse_hackernews_hits,
    parse_sogou_search_html,
)
from app.services.ingestion import ingest_text


def test_parse_hackernews_hits_preserves_web_identity_and_attention_signals():
    rows = parse_hackernews_hits({"hits": [{
        "objectID": "42",
        "title": "A new agent result",
        "url": "https://example.com/agent",
        "created_at": "2026-09-15T01:00:00Z",
        "author": "alice",
        "points": 17,
        "num_comments": 9,
    }]})
    assert len(rows) == 1
    row = rows[0]
    assert row.ref == "https://example.com/agent"
    assert row.metadata["delivery_mode"] == "URL_FETCH"
    assert row.metadata["engagement"] == {"points": 17, "comments": 9}
    assert row.metadata["platform_item_url"] == "https://news.ycombinator.com/item?id=42"


def test_parse_bilibili_search_preserves_video_and_raw_engagement():
    rows = parse_bilibili_search_response({"code": 0, "data": {"result": [{
        "bvid": "BV123",
        "title": "AI <em class=\"keyword\">Agent</em> demo",
        "description": "A useful demo",
        "author": "creator",
        "mid": 123,
        "pic": "//i.example/cover.jpg",
        "play": 100,
        "favorites": 8,
        "review": 5,
        "danmaku": 4,
        "like": 12,
        "pubdate": 1789434000,
    }]}})
    assert len(rows) == 1
    row = rows[0]
    assert row.title == "AI Agent demo"
    assert row.metadata["normalized_source_type"] == "VIDEO"
    assert row.metadata["hero_image_url"] == "https://i.example/cover.jpg"
    assert row.metadata["engagement"]["views"] == 100
    assert row.metadata["engagement"]["likes"] == 12


def test_parse_bilibili_creator_uses_same_video_contract():
    rows = parse_bilibili_creator_response({"code": 0, "data": {"list": {"vlist": [{
        "bvid": "BV999", "title": "Creator update", "description": "desc",
        "author": "creator", "mid": 9, "pic": "https://i.example/x.jpg",
        "play": 3, "favorites": 1, "comment": 2, "danmaku": 0, "created": 1789434000,
    }]}}})
    assert len(rows) == 1
    assert rows[0].external_id == "BV999"
    assert rows[0].metadata["item_type"] == "VIDEO"


def test_parse_sogou_result_html_and_reject_shell_page():
    html = '''<html><body><div class="vrwrap"><h3><a href="https://example.com/x">Result X</a></h3><p>Useful snippet</p></div></body></html>'''
    rows = parse_sogou_search_html(html)
    assert len(rows) == 1
    assert rows[0].ref == "https://example.com/x"
    assert rows[0].metadata["fallback_content_text"] == "Useful snippet"

    try:
        parse_sogou_search_html("<html><title>搜狗搜索</title><body>shell</body></html>")
    except RuntimeError as exc:
        assert "no result DOM" in str(exc)
    else:
        raise AssertionError("Sogou shell page must be a technical failure, not an empty success")


def test_phase11a_source_types_are_manageable_via_api(client):
    for source_type in ("HACKERNEWS_SEARCH", "BILIBILI_SEARCH", "BILIBILI_CREATOR", "SOGOU_SEARCH"):
        created = client.post("/acquisition/sources", json={
            "name": source_type,
            "source_type": source_type,
            "locator": "123" if source_type == "BILIBILI_CREATOR" else "AI agent",
            "enabled": False,
        })
        assert created.status_code == 200, created.text
        assert created.json()["source_type"] == source_type


def test_bilibili_inline_delivery_preserves_engagement_without_attention_logic(db, monkeypatch):
    source = SourceDefinition(name="Bilibili AI", source_type="BILIBILI_SEARCH", locator="AI agent")
    db.add(source)
    db.flush()
    discovered = DiscoveredExternalItem(
        ref="https://www.bilibili.com/video/BV1",
        external_id="BV1",
        title="Agent video",
        published_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        metadata={
            "delivery_mode": "INLINE_PUBLIC",
            "item_type": "VIDEO",
            "normalized_source_type": "VIDEO",
            "platform": "BILIBILI",
            "content_text": "Video description",
            "content_scope": "METADATA_ONLY",
            "defer_cognition": True,
            "defer_cognition_reason": "video transcript/full semantic content not acquired",
            "author_name": "creator",
            "engagement": {"views": 50, "likes": 3, "comments": 2},
        },
    )
    analyses = []
    monkeypatch.setattr(acquisition.BilibiliSearchAdapter, "discover", lambda self, locator: [discovered])
    monkeypatch.setattr(acquisition, "run_pipeline", lambda db, source_id: analyses.append(str(source_id)))
    result = poll_source(db, source, analyze=True)
    assert result["new_snapshots"] == 1
    snapshot = db.execute(select(InformationSnapshot)).scalar_one()
    stored = db.get(Source, snapshot.raos_source_id)
    assert stored.source_type == "VIDEO"
    assert stored.raw_metadata["engagement"]["views"] == 50
    assert "attention" not in stored.raw_metadata
    assert snapshot.snapshot_metadata["cognition_deferred"] is True
    assert analyses == []


def test_hn_and_rss_observations_deduplicate_same_external_url(db, monkeypatch):
    rss = SourceDefinition(name="RSS", source_type="RSS", locator="https://example.com/feed")
    hn = SourceDefinition(name="HN", source_type="HACKERNEWS_SEARCH", locator="agent")
    db.add_all([rss, hn])
    db.flush()
    candidate = DiscoveredExternalItem(
        ref="https://example.com/same",
        external_id="hn-1",
        title="Same event",
        metadata={"delivery_mode": "URL_FETCH", "fallback_content_text": "Same event"},
    )
    monkeypatch.setattr(acquisition.RSSAdapter, "discover", lambda self, locator: [candidate])
    monkeypatch.setattr(acquisition.HackerNewsSearchAdapter, "discover", lambda self, locator: [candidate])

    def fake_ingest(db, url):
        row = ingest_text(db, "Fetched full body", title="Same event")
        row.canonical_url = url
        return row

    monkeypatch.setattr(acquisition, "ingest_url", fake_ingest)
    poll_source(db, rss, analyze=False)
    poll_source(db, hn, analyze=False)

    assert len(db.execute(select(ExternalInformationItem)).scalars().all()) == 1
    assert len(db.execute(select(AcquisitionObservation)).scalars().all()) == 2
    assert len(db.execute(select(InformationSnapshot)).scalars().all()) == 1


def test_new_bilibili_source_bootstraps_without_cognition(db, monkeypatch):
    analyses = []
    source = SourceDefinition(name="Bilibili Bootstrap", source_type="BILIBILI_SEARCH", locator="AI", enabled=True)
    db.add(source)
    db.flush()
    monkeypatch.setattr(acquisition.BilibiliSearchAdapter, "discover", lambda self, locator: [
        DiscoveredExternalItem(
            ref="https://www.bilibili.com/video/BVBOOT",
            title="Bootstrap video",
            metadata={"delivery_mode": "INLINE_PUBLIC", "normalized_source_type": "VIDEO", "content_text": "body"},
        )
    ])
    monkeypatch.setattr(acquisition, "run_pipeline", lambda db, source_id: analyses.append(str(source_id)))
    result = poll_due_sources(db, limit_per_source=5, analyze=True)
    assert result[0]["bootstrap"] is True
    assert analyses == []
