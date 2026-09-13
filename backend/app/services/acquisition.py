from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.connectors.url import validate_public_url
from app.models.acquisition import (
    AcquisitionObservation,
    ExternalInformationItem,
    InformationSnapshot,
    SourceDefinition,
)
from app.models.source import Source
from app.services.ingestion import ingest_url
from app.services.pipeline import run_pipeline


@dataclass(frozen=True)
class DiscoveredExternalItem:
    ref: str
    external_id: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


def _text(node, *names: str) -> str | None:
    for name in names:
        child = node.find(name)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
    return None


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_rss_or_atom(payload: bytes | str, *, base_url: str) -> list[DiscoveredExternalItem]:
    root = ET.fromstring(payload)
    entries: list[DiscoveredExternalItem] = []
    if root.tag.endswith("feed"):
        namespace = root.tag.removesuffix("feed")
        for entry in root.findall(f"{namespace}entry"):
            title = _text(entry, f"{namespace}title")
            external_id = _text(entry, f"{namespace}id")
            link = None
            for link_node in entry.findall(f"{namespace}link"):
                rel = (link_node.attrib.get("rel") or "alternate").lower()
                href = link_node.attrib.get("href")
                if href and rel == "alternate":
                    link = urljoin(base_url, href)
                    break
            if not link:
                continue
            published = _text(entry, f"{namespace}published", f"{namespace}updated")
            entries.append(DiscoveredExternalItem(
                ref=link,
                external_id=external_id,
                title=title,
                published_at=_parse_time(published),
                metadata={"feed_format": "ATOM"},
            ))
        return entries

    channel = root.find("channel")
    if channel is None:
        return entries
    for item in channel.findall("item"):
        link = _text(item, "link")
        if not link:
            continue
        entries.append(DiscoveredExternalItem(
            ref=urljoin(base_url, link),
            external_id=_text(item, "guid"),
            title=_text(item, "title"),
            published_at=_parse_time(_text(item, "pubDate", "date")),
            metadata={"feed_format": "RSS"},
        ))
    return entries


class RSSAdapter:
    source_type = "RSS"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        url = validate_public_url(locator)
        with httpx.Client(follow_redirects=True, timeout=settings.url_fetch_timeout_seconds) as client:
            response = client.get(url, headers={"User-Agent": "RAOS/1.1 Acquisition"})
            response.raise_for_status()
            final_url = str(response.url)
            validate_public_url(final_url)
            return parse_rss_or_atom(response.content, base_url=final_url)


def _identity_key(source: SourceDefinition, item: DiscoveredExternalItem) -> str:
    if item.ref:
        parsed = urlparse(item.ref)
        normalized = parsed._replace(fragment="").geturl().rstrip("/")
        return f"url:{normalized}"
    return f"{source.source_type.lower()}:{source.id}:{item.external_id or item.title or 'unknown'}"


def _get_or_create_item(db: Session, source: SourceDefinition, discovered: DiscoveredExternalItem):
    key = _identity_key(source, discovered)
    item = db.execute(
        select(ExternalInformationItem).where(ExternalInformationItem.identity_key == key)
    ).scalars().first()
    created = item is None
    if item is None:
        item = ExternalInformationItem(
            identity_key=key,
            item_type="ARTICLE",
            canonical_url=discovered.ref,
            title=discovered.title,
            published_at=discovered.published_at,
        )
        db.add(item)
        db.flush()
    return item, created


def _observe(db: Session, source: SourceDefinition, item: ExternalInformationItem, discovered: DiscoveredExternalItem):
    observation = db.execute(
        select(AcquisitionObservation).where(
            AcquisitionObservation.source_definition_id == source.id,
            AcquisitionObservation.external_item_id == item.id,
        )
    ).scalars().first()
    if observation is not None:
        return observation, False
    observation = AcquisitionObservation(
        source_definition_id=source.id,
        external_item_id=item.id,
        external_ref=discovered.ref,
        observation_metadata=dict(discovered.metadata or {}),
    )
    db.add(observation)
    db.flush()
    return observation, True


def _current_snapshot(db: Session, item_id):
    return db.execute(
        select(InformationSnapshot)
        .where(InformationSnapshot.external_item_id == item_id)
        .order_by(InformationSnapshot.captured_at.desc())
    ).scalars().first()


def _deliver(db: Session, item: ExternalInformationItem, *, analyze: bool) -> InformationSnapshot:
    existing = _current_snapshot(db, item.id)
    if existing is not None:
        return existing
    raos_source = ingest_url(db, item.canonical_url)
    raos_source.raw_metadata = {
        **(raos_source.raw_metadata or {}),
        "acquisition": {"external_item_id": str(item.id), "identity_key": item.identity_key},
    }
    snapshot = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=raos_source.id,
        content_hash=raos_source.content_hash,
        snapshot_metadata={"delivery": "URL_FETCH"},
    )
    db.add(snapshot)
    db.flush()
    if analyze:
        run_pipeline(db, raos_source.id)
    return snapshot


def poll_source(db: Session, source: SourceDefinition, *, limit: int = 5, analyze: bool = True) -> dict:
    if source.source_type.upper() != "RSS":
        raise ValueError(f"Unsupported acquisition source type: {source.source_type}")
    discovered = RSSAdapter().discover(source.locator)[: max(0, int(limit))]
    counts = {"discovered": len(discovered), "new_items": 0, "new_observations": 0, "new_snapshots": 0}
    delivered_source_ids: list[str] = []
    for candidate in discovered:
        item, item_created = _get_or_create_item(db, source, candidate)
        _, observation_created = _observe(db, source, item, candidate)
        before = _current_snapshot(db, item.id)
        snapshot = _deliver(db, item, analyze=analyze)
        counts["new_items"] += int(item_created)
        counts["new_observations"] += int(observation_created)
        counts["new_snapshots"] += int(before is None)
        delivered_source_ids.append(str(snapshot.raos_source_id))
    source.last_polled_at = datetime.now(timezone.utc)
    db.flush()
    return {
        "source_definition_id": str(source.id),
        "source_name": source.name,
        **counts,
        "raos_source_ids": delivered_source_ids,
    }


def poll_source_by_id(db: Session, source_id, *, limit: int = 5, analyze: bool = True) -> dict:
    source = db.get(SourceDefinition, source_id)
    if source is None:
        raise ValueError("Acquisition Source not found")
    return poll_source(db, source, limit=limit, analyze=analyze)


def _due(source: SourceDefinition, now: datetime) -> bool:
    if not source.enabled:
        return False
    if source.last_polled_at is None:
        return True
    last = source.last_polled_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return last + timedelta(seconds=max(1, source.poll_interval_seconds)) <= now


def poll_due_sources(db: Session, *, limit_per_source: int = 5, analyze: bool = True) -> list[dict]:
    now = datetime.now(timezone.utc)
    sources = db.execute(
        select(SourceDefinition).where(SourceDefinition.enabled.is_(True)).order_by(SourceDefinition.created_at)
    ).scalars().all()
    return [
        poll_source(db, source, limit=limit_per_source, analyze=analyze)
        for source in sources
        if _due(source, now)
    ]
