from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

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
from app.services.ingestion import ingest_url, persist_normalized
from app.services.fingerprint import NormalizedSource
from app.services.pipeline import run_pipeline
from app.services.acquisition_types import DiscoveredExternalItem
from app.services.social_adapters import WeiboPublicAdapter, XPublicAdapter
from app.services.active_acquisition import ActiveQueryBundleAdapter
from app.services.discovery_adapters import (
    BilibiliCreatorAdapter,
    BilibiliSearchAdapter,
    HackerNewsSearchAdapter,
    SogouSearchAdapter,
)


def _text(node, *names: str) -> str | None:
    for name in names:
        child = node.find(name)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
    return None




def _clean_feed_text(value: str | None) -> str | None:
    if not value:
        return None
    text = BeautifulSoup(value, "lxml").get_text(" ", strip=True)
    return " ".join(text.split()) or None


def _child_by_local_name(node, *names: str):
    wanted = set(names)
    for child in list(node):
        local = child.tag.rsplit("}", 1)[-1]
        if local in wanted:
            return child
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
            summary_node = _child_by_local_name(entry, "summary")
            content_node = _child_by_local_name(entry, "content")
            feed_text = _clean_feed_text(
                (content_node.text if content_node is not None else None)
                or (summary_node.text if summary_node is not None else None)
            )
            entries.append(DiscoveredExternalItem(
                ref=link,
                external_id=external_id,
                title=title,
                published_at=_parse_time(published),
                metadata={"feed_format": "ATOM", "feed_content_text": feed_text},
            ))
        return entries

    channel = root.find("channel")
    if channel is None:
        return entries
    for item in channel.findall("item"):
        link = _text(item, "link")
        if not link:
            continue
        description_node = _child_by_local_name(item, "description")
        encoded_node = _child_by_local_name(item, "encoded")
        feed_text = _clean_feed_text(
            (encoded_node.text if encoded_node is not None else None)
            or (description_node.text if description_node is not None else None)
        )
        entries.append(DiscoveredExternalItem(
            ref=urljoin(base_url, link),
            external_id=_text(item, "guid"),
            title=_text(item, "title"),
            published_at=_parse_time(_text(item, "pubDate", "date")),
            metadata={"feed_format": "RSS", "feed_content_text": feed_text},
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


def _adapter_for(source: SourceDefinition):
    kind = source.source_type.upper()
    if kind == "RSS":
        return RSSAdapter()
    if kind == "X_PUBLIC":
        return XPublicAdapter()
    if kind == "WEIBO_PUBLIC":
        return WeiboPublicAdapter()
    if kind == "HACKERNEWS_SEARCH":
        return HackerNewsSearchAdapter()
    if kind == "BILIBILI_SEARCH":
        return BilibiliSearchAdapter()
    if kind == "BILIBILI_CREATOR":
        return BilibiliCreatorAdapter()
    if kind == "SOGOU_SEARCH":
        return SogouSearchAdapter()
    if kind == "ACTIVE_QUERY_BUNDLE":
        return ActiveQueryBundleAdapter()
    raise ValueError(f"Unsupported acquisition source type: {source.source_type}")


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
            item_type=str((discovered.metadata or {}).get("item_type") or ("ARTICLE" if source.source_type.upper() == "RSS" else "POST")),
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


def _persist_feed_fallback(db: Session, source: SourceDefinition, item: ExternalInformationItem, discovered: DiscoveredExternalItem) -> Source:
    text = (discovered.metadata or {}).get("feed_content_text")
    if not text:
        raise ValueError("Feed item has no fallback content")
    normalized = NormalizedSource(
        source_type="URL",
        title=item.title,
        canonical_url=item.canonical_url,
        content_text=text,
        published_at=item.published_at,
        publisher=source.name,
        raw_metadata={
            "origin_url": item.canonical_url,
            "feed_source_name": source.name,
            "feed_format": (discovered.metadata or {}).get("feed_format"),
            "feed_fallback": True,
            "parser": "rss-fallback-v1",
        },
        ingestion_method="RSS_FALLBACK",
    )
    return persist_normalized(db, normalized)


def _persist_inline_item(db: Session, source: SourceDefinition, item: ExternalInformationItem, discovered: DiscoveredExternalItem) -> Source:
    metadata = dict(discovered.metadata or {})
    text = str(metadata.get("content_text") or "").strip()
    if not text:
        raise ValueError("Platform item has no public text")
    author = metadata.get("social_author") or metadata.get("author_name")
    normalized = NormalizedSource(
        source_type=str(metadata.get("normalized_source_type") or "POST"),
        title=item.title,
        canonical_url=item.canonical_url,
        content_text=text,
        published_at=item.published_at,
        author_entities=[str(author)] if author else [],
        publisher=source.name,
        raw_metadata={
            **metadata,
            "origin_url": item.canonical_url,
            "acquisition_source_name": source.name,
            "parser": f"{source.source_type.lower()}-v1",
        },
        ingestion_method=source.source_type.upper(),
    )
    return persist_normalized(db, normalized)


def _persist_discovery_fallback(db: Session, source: SourceDefinition, item: ExternalInformationItem, discovered: DiscoveredExternalItem) -> Source:
    metadata = dict(discovered.metadata or {})
    text = str(metadata.get("fallback_content_text") or "").strip()
    if not text:
        raise ValueError("Discovered web item has no fallback content")
    normalized = NormalizedSource(
        source_type="URL",
        title=item.title,
        canonical_url=item.canonical_url,
        content_text=text,
        published_at=item.published_at,
        author_entities=[str(metadata["author_name"])] if metadata.get("author_name") else [],
        publisher=source.name,
        raw_metadata={
            **metadata,
            "origin_url": item.canonical_url,
            "acquisition_source_name": source.name,
            "discovery_fallback": True,
            "parser": f"{source.source_type.lower()}-fallback-v1",
        },
        ingestion_method=f"{source.source_type.upper()}_FALLBACK",
    )
    return persist_normalized(db, normalized)


def _deliver(db: Session, source: SourceDefinition, item: ExternalInformationItem, discovered: DiscoveredExternalItem, *, analyze: bool) -> InformationSnapshot:
    existing = _current_snapshot(db, item.id)
    if existing is not None:
        return existing
    metadata = dict(discovered.metadata or {})
    kind = source.source_type.upper()
    delivery_mode = str(metadata.get("delivery_mode") or ("URL_FETCH" if kind == "RSS" else "INLINE_PUBLIC")).upper()
    if delivery_mode == "URL_FETCH":
        try:
            raos_source = ingest_url(db, item.canonical_url)
        except Exception:
            if kind == "RSS" and metadata.get("feed_content_text"):
                raos_source = _persist_feed_fallback(db, source, item, discovered)
            elif metadata.get("fallback_content_text"):
                raos_source = _persist_discovery_fallback(db, source, item, discovered)
            else:
                raise
    elif delivery_mode == "INLINE_PUBLIC":
        raos_source = _persist_inline_item(db, source, item, discovered)
    else:
        raise ValueError(f"Unsupported acquisition delivery mode: {delivery_mode}")
    raos_source.raw_metadata = {
        **(raos_source.raw_metadata or {}),
        "acquisition": {"external_item_id": str(item.id), "identity_key": item.identity_key},
    }
    snapshot = InformationSnapshot(
        external_item_id=item.id,
        raos_source_id=raos_source.id,
        content_hash=raos_source.content_hash,
        snapshot_metadata={
            "delivery": delivery_mode,
            "source_type": kind,
            "cognition_deferred": bool(metadata.get("defer_cognition")),
            "cognition_defer_reason": metadata.get("defer_cognition_reason"),
        },
    )
    db.add(snapshot)
    db.flush()
    if analyze and not metadata.get("defer_cognition"):
        run_pipeline(db, raos_source.id)
    return snapshot


def poll_source(db: Session, source: SourceDefinition, *, limit: int = 5, analyze: bool = True) -> dict:
    adapter = _adapter_for(source)
    discovered = adapter.discover(source.locator)[: max(0, int(limit))]
    adapter_report = getattr(adapter, "last_report", None)
    counts = {"discovered": len(discovered), "new_items": 0, "new_observations": 0, "new_snapshots": 0, "item_failures": 0}
    delivered_source_ids: list[str] = []
    item_errors: list[dict] = []
    for candidate in discovered:
        try:
            with db.begin_nested():
                item, item_created = _get_or_create_item(db, source, candidate)
                _, observation_created = _observe(db, source, item, candidate)
                before = _current_snapshot(db, item.id)
                snapshot = _deliver(db, source, item, candidate, analyze=analyze)
                counts["new_items"] += int(item_created)
                counts["new_observations"] += int(observation_created)
                counts["new_snapshots"] += int(before is None)
                delivered_source_ids.append(str(snapshot.raos_source_id))
        except Exception as exc:
            counts["item_failures"] += 1
            item_errors.append({
                "ref": candidate.ref,
                "title": candidate.title,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
    source.last_polled_at = datetime.now(timezone.utc)
    db.flush()
    return {
        "source_definition_id": str(source.id),
        "source_name": source.name,
        **counts,
        "raos_source_ids": delivered_source_ids,
        "item_errors": item_errors,
        "adapter_report": adapter_report,
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
    results: list[dict] = []
    for source in sources:
        if not _due(source, now):
            continue
        # A newly registered Source establishes a present-time baseline first.
        # Historical feed entries are captured but are not pushed through cognition.
        bootstrap = source.last_polled_at is None
        try:
            with db.begin_nested():
                result = poll_source(
                    db,
                    source,
                    limit=limit_per_source,
                    analyze=analyze and not bootstrap,
                )
            result["bootstrap"] = bootstrap
            result["status"] = "OK"
            results.append(result)
        except Exception as exc:
            # One broken external Source must not terminate the whole poller.
            # Treat the attempt as a poll for cadence purposes, while preserving
            # the error as an explicit acquisition result.
            source.last_polled_at = now
            db.flush()
            results.append({
                "source_definition_id": str(source.id),
                "source_name": source.name,
                "bootstrap": bootstrap,
                "status": "ERROR",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
    return results
