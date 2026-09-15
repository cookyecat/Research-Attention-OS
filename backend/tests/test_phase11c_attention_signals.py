from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.acquisition import AttentionSignalSample, ExternalInformationItem, SourceDefinition
from app.services.acquisition_types import DiscoveredExternalItem
from app.services.attention_signals import record_attention_signal_sample


def _rows(db):
    return db.execute(select(AttentionSignalSample).order_by(AttentionSignalSample.first_observed_at)).scalars().all()


def _fixture(db):
    source = SourceDefinition(name="HN test", source_type="HACKERNEWS_SEARCH", locator="AI agent", poll_interval_seconds=60)
    item = ExternalInformationItem(
        identity_key="url:https://example.com/a",
        item_type="ARTICLE",
        canonical_url="https://example.com/a",
        title="A",
        published_at=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
    )
    db.add_all([source, item]); db.flush()
    return source, item


def test_same_signal_state_extends_interval_without_row_growth(db):
    source, item = _fixture(db)
    discovered = DiscoveredExternalItem(
        ref=item.canonical_url,
        metadata={"platform": "HACKER_NEWS", "engagement": {"points": 10, "comments": 2}},
    )
    t1 = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
    t2 = t1 + timedelta(minutes=30)
    row1, action1 = record_attention_signal_sample(db, source=source, item=item, discovered=discovered, observed_at=t1)
    row2, action2 = record_attention_signal_sample(db, source=source, item=item, discovered=discovered, observed_at=t2)
    assert action1 == "CREATED"
    assert action2 == "EXTENDED"
    assert row1.id == row2.id
    assert len(_rows(db)) == 1
    assert _rows(db)[0].last_observed_at == t2


def test_changed_signal_state_appends_new_segment(db):
    source, item = _fixture(db)
    t1 = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
    first = DiscoveredExternalItem(ref=item.canonical_url, metadata={"platform": "HACKER_NEWS", "engagement": {"points": 10, "comments": 2}})
    second = DiscoveredExternalItem(ref=item.canonical_url, metadata={"platform": "HACKER_NEWS", "engagement": {"points": 25, "comments": 5}})
    record_attention_signal_sample(db, source=source, item=item, discovered=first, observed_at=t1)
    _, action = record_attention_signal_sample(db, source=source, item=item, discovered=second, observed_at=t1 + timedelta(hours=1))
    rows = _rows(db)
    assert action == "CREATED"
    assert len(rows) == 2
    assert rows[0].metrics == {"comments": 2, "points": 10}
    assert rows[1].metrics == {"comments": 5, "points": 25}




def test_same_metrics_crossing_age_bucket_creates_new_segment(db):
    source, item = _fixture(db)
    discovered = DiscoveredExternalItem(
        ref=item.canonical_url,
        metadata={"platform": "HACKER_NEWS", "engagement": {"points": 10, "comments": 2}},
    )
    t1 = datetime(2026, 9, 15, 0, 30, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)
    record_attention_signal_sample(db, source=source, item=item, discovered=discovered, observed_at=t1)
    _, action = record_attention_signal_sample(db, source=source, item=item, discovered=discovered, observed_at=t2)
    rows = _rows(db)
    assert action == "CREATED"
    assert len(rows) == 2
    assert rows[0].signal_context["content_age_bucket"] == "lt_1h"
    assert rows[1].signal_context["content_age_bucket"] == "6h_24h"


def test_no_engagement_signal_creates_no_sample(db):
    source, item = _fixture(db)
    discovered = DiscoveredExternalItem(ref=item.canonical_url, metadata={"platform": "HACKER_NEWS"})
    row, action = record_attention_signal_sample(db, source=source, item=item, discovered=discovered)
    assert row is None
    assert action == "NO_SIGNAL"
    assert _rows(db) == []

from app.models.acquisition import InformationSnapshot
from app.models.event import Event, EventSource
from app.services.attention_normalization import magnitude_free_observation
from app.services.ingestion import ingest_text
from app.services.p_evidence import build_event_p_evidence_packet
from eval.live.collective_attention_v1 import CollectiveAttentionEvidencePacketV1


def _sample(db, *, source, item, platform, metric, value, age_bucket="1h_6h", when=None):
    when = when or datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
    row = AttentionSignalSample(
        source_definition_id=source.id,
        external_item_id=item.id,
        platform=platform,
        first_observed_at=when,
        last_observed_at=when,
        signal_hash=f"{platform}-{metric}-{value}-{item.id}",
        metrics={metric: value},
        signal_context={"content_age_bucket": age_bucket, "sensor_version": "test"},
        quality="direct",
        contamination=[],
    )
    db.add(row); db.flush()
    return row


def test_magnitude_free_returns_unknown_under_insufficient_support(db):
    source, item = _fixture(db)
    target = _sample(db, source=source, item=item, platform="HACKER_NEWS", metric="points", value=50)
    obs = magnitude_free_observation(db, target, "points", min_support=20)
    assert obs.status == "INSUFFICIENT_SUPPORT"
    assert obs.percentile is None
    assert obs.support_n == 0


def test_magnitude_free_percentile_is_reproducible_with_sufficient_support(db):
    source = SourceDefinition(name="HN reference", source_type="HACKERNEWS_SEARCH", locator="agent", poll_interval_seconds=60)
    db.add(source); db.flush()
    for i in range(20):
        item = ExternalInformationItem(identity_key=f"url:https://example.com/ref-{i}", item_type="ARTICLE", canonical_url=f"https://example.com/ref-{i}", title=f"ref {i}")
        db.add(item); db.flush()
        _sample(db, source=source, item=item, platform="HACKER_NEWS", metric="points", value=i)
    target_item = ExternalInformationItem(identity_key="url:https://example.com/target", item_type="ARTICLE", canonical_url="https://example.com/target", title="target")
    db.add(target_item); db.flush()
    target = _sample(db, source=source, item=target_item, platform="HACKER_NEWS", metric="points", value=15)
    obs = magnitude_free_observation(db, target, "points", min_support=20)
    assert obs.status == "OK"
    assert obs.support_n == 20
    assert obs.percentile == 0.775


def test_event_p_evidence_packet_is_schema_valid_and_cross_platform(db):
    event = Event(title="Agent scientific discovery release", summary="An autonomous AI research agent was released for scientific discovery.", confidence=0.9, status="CANDIDATE")
    db.add(event); db.flush()
    platforms = [
        ("HACKER_NEWS", "points", 37, "HACKERNEWS_SEARCH"),
        ("BILIBILI", "comments", 12, "BILIBILI_SEARCH"),
    ]
    for idx, (platform, metric, value, source_type) in enumerate(platforms):
        source_def = SourceDefinition(name=f"{platform} source", source_type=source_type, locator="agent", poll_interval_seconds=60)
        item = ExternalInformationItem(identity_key=f"url:https://example.com/p-{idx}", item_type="ARTICLE", canonical_url=f"https://example.com/p-{idx}", title=f"platform {idx}")
        db.add_all([source_def, item]); db.flush()
        raos_source = ingest_text(db, f"Evidence from {platform}", title=f"Evidence {idx}")
        db.add(EventSource(event_id=event.id, source_id=raos_source.id, relationship="REPORTS", confidence=0.9))
        db.add(InformationSnapshot(external_item_id=item.id, raos_source_id=raos_source.id, content_hash=raos_source.content_hash, snapshot_metadata={"delivery": source_type}))
        _sample(db, source=source_def, item=item, platform=platform, metric=metric, value=value)
    db.flush()
    packet = build_event_p_evidence_packet(db, event.id, min_normalization_support=20)
    validated = CollectiveAttentionEvidencePacketV1.model_validate(packet)
    assert validated.event.event_id == str(event.id)
    assert set(validated.collection_context.channels_checked) == {"BILIBILI", "HACKER_NEWS"}
    assert any(row.kind == "cross_platform_spread" for row in validated.current_attention_evidence)
    assert any("normalization=UNKNOWN" in row.observation for row in validated.current_attention_evidence)


def test_magnitude_free_reference_counts_latest_state_once_per_item(db):
    source = SourceDefinition(name="HN reference states", source_type="HACKERNEWS_SEARCH", locator="agent", poll_interval_seconds=60)
    db.add(source); db.flush()
    when = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
    # 20 distinct reference items; one of them has many historical state segments.
    for i in range(20):
        item = ExternalInformationItem(identity_key=f"url:https://example.com/latest-{i}", item_type="ARTICLE", canonical_url=f"https://example.com/latest-{i}", title=f"latest {i}")
        db.add(item); db.flush()
        _sample(db, source=source, item=item, platform="HACKER_NEWS", metric="points", value=i, when=when)
        if i == 0:
            for j in range(1, 8):
                _sample(db, source=source, item=item, platform="HACKER_NEWS", metric="points", value=j, when=when + timedelta(minutes=j))
    target_item = ExternalInformationItem(identity_key="url:https://example.com/latest-target", item_type="ARTICLE", canonical_url="https://example.com/latest-target", title="target")
    db.add(target_item); db.flush()
    target = _sample(db, source=source, item=target_item, platform="HACKER_NEWS", metric="points", value=15, when=when + timedelta(hours=1))
    obs = magnitude_free_observation(db, target, "points", min_support=20)
    assert obs.status == "OK"
    assert obs.support_n == 20


def test_event_p_evidence_packet_includes_signal_history(db):
    event = Event(title="Signal history event", summary="A monitored event with changing public attention.", confidence=0.9, status="CANDIDATE")
    source_def = SourceDefinition(name="HN history", source_type="HACKERNEWS_SEARCH", locator="agent", poll_interval_seconds=60)
    item = ExternalInformationItem(identity_key="url:https://example.com/history", item_type="ARTICLE", canonical_url="https://example.com/history", title="history")
    db.add_all([event, source_def, item]); db.flush()
    raos_source = ingest_text(db, "Historical signal evidence", title="History source")
    db.add(EventSource(event_id=event.id, source_id=raos_source.id, relationship="REPORTS", confidence=0.9))
    db.add(InformationSnapshot(external_item_id=item.id, raos_source_id=raos_source.id, content_hash=raos_source.content_hash, snapshot_metadata={}))
    t1 = datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc)
    _sample(db, source=source_def, item=item, platform="HACKER_NEWS", metric="points", value=10, when=t1)
    _sample(db, source=source_def, item=item, platform="HACKER_NEWS", metric="points", value=30, when=t1 + timedelta(hours=1))
    db.flush()
    packet = build_event_p_evidence_packet(db, event.id)
    validated = CollectiveAttentionEvidencePacketV1.model_validate(packet)
    assert validated.recent_attention_history
    assert any("points 10→30" in row.observation for row in validated.recent_attention_history)
