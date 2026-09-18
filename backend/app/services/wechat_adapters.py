from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

import httpx

from app.connectors.wechat import wechat_url_identity
from app.services.acquisition_types import DiscoveredExternalItem

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153 Safari/537.36"
)
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


def parse_wechat_account_locator(locator: str) -> dict:
    try:
        config = json.loads(locator)
    except json.JSONDecodeError as exc:
        raise ValueError("WECHAT_ACCOUNT locator must be JSON") from exc
    if not isinstance(config, dict):
        raise ValueError("WECHAT_ACCOUNT locator must be a JSON object")
    account = str(config.get("account") or "").strip()
    biz = str(config.get("biz") or "").strip()

    feed_urls = [str(value).strip() for value in (config.get("feed_urls") or []) if str(value).strip()]
    if not account or not biz or not feed_urls:
        raise ValueError("WECHAT_ACCOUNT locator requires account, biz and feed_urls")
    return {"account": account, "biz": biz, "feed_urls": feed_urls}


def _published(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _parse_feed(payload: bytes, *, account: str, biz: str, feed_url: str) -> list[DiscoveredExternalItem]:
    root = ET.fromstring(payload)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("Wechat2RSS feed has no channel")
    rows: list[DiscoveredExternalItem] = []
    for item in channel.findall("item"):
        ref = str(item.findtext("link") or "").strip()
        title = str(item.findtext("title") or "").strip()
        if not ref or not title:
            continue
        actual_biz, mid, idx = wechat_url_identity(ref)
        if actual_biz != biz or not mid or not idx:
            continue

        encoded = item.find(_CONTENT_NS)
        full_html = encoded.text if encoded is not None and encoded.text else None
        rows.append(
            DiscoveredExternalItem(
                ref=ref,
                external_id=f"{biz}:{mid}:{idx}",
                title=title,
                published_at=_published(item.findtext("pubDate")),
                metadata={
                    "delivery_mode": "WECHAT_ARTICLE",
                    "item_type": "ARTICLE",
                    "platform": "WECHAT",
                    "wechat_account": account,
                    "wechat_biz": biz,
                    "wechat_mid": mid,
                    "wechat_idx": idx,
                    "wechat_identity_key": f"wechat:{biz}:{mid}:{idx}",
                    "wechat_feed_url": feed_url,
                    "wechat_feed_html": full_html,
                    "wechat_feed_has_full_html": bool(full_html and len(full_html) >= 500),
                    "discovery_transport": "wechat2rss",
                },
            )
        )
    return rows


class WechatAccountAdapter:
    source_type = "WECHAT_ACCOUNT"

    def __init__(self) -> None:
        self.last_report: dict | None = None

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        config = parse_wechat_account_locator(locator)
        account, biz = config["account"], config["biz"]
        merged: dict[str, DiscoveredExternalItem] = {}
        reports = []
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for feed_url in config["feed_urls"]:
                try:
                    response = client.get(feed_url, headers={"User-Agent": _BROWSER_UA})
                    response.raise_for_status()
                    rows = _parse_feed(response.content, account=account, biz=biz, feed_url=feed_url)
                    reports.append({"feed_url": feed_url, "status": "OK", "items": len(rows)})
                    for row in rows:
                        key = str(row.metadata.get("wechat_identity_key") or row.external_id)
                        current = merged.get(key)
                        if current is None:
                            merged[key] = row
                            continue
                        # Prefer the first configured feed for payload transport,
                        # but retain corroborating discovery paths as provenance.
                        feeds = list(current.metadata.get("wechat_discovery_feeds") or [current.metadata.get("wechat_feed_url")])
                        if feed_url not in feeds:
                            feeds.append(feed_url)
                        current.metadata["wechat_discovery_feeds"] = [value for value in feeds if value]
                except Exception as exc:
                    reports.append({"feed_url": feed_url, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:500]})

        if not merged:
            raise RuntimeError(f"No valid WeChat items discovered for {account}")
        rows = list(merged.values())
        rows.sort(key=lambda row: row.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        self.last_report = {
            "account": account,
            "biz": biz,
            "feeds": reports,
            "items": len(rows),
        }
        return rows
