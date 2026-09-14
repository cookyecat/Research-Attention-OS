from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.acquisition_types import DiscoveredExternalItem

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"
)


def _parse_iso_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_hackernews_hits(payload: dict) -> list[DiscoveredExternalItem]:
    found: list[DiscoveredExternalItem] = []
    for hit in payload.get("hits") or []:
        object_id = str(hit.get("objectID") or "").strip()
        title = str(hit.get("title") or hit.get("story_title") or "").strip()
        if not object_id or not title:
            continue
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        external_url = str(hit.get("url") or "").strip() or hn_url
        story_text = BeautifulSoup(str(hit.get("story_text") or ""), "lxml").get_text(" ", strip=True)
        fallback = story_text or title
        found.append(
            DiscoveredExternalItem(
                ref=external_url,
                external_id=object_id,
                title=title,
                published_at=_parse_iso_time(hit.get("created_at")),
                metadata={
                    "delivery_mode": "URL_FETCH" if external_url != hn_url else "INLINE_PUBLIC",
                    "item_type": "ARTICLE" if external_url != hn_url else "POST",
                    "fallback_content_text": fallback,
                    "content_text": fallback,
                    "platform": "HACKER_NEWS",
                    "platform_item_url": hn_url,
                    "author_name": hit.get("author"),
                    "engagement": {
                        "points": hit.get("points") or 0,
                        "comments": hit.get("num_comments") or 0,
                    },
                },
            )
        )
    found.sort(key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return found


class HackerNewsSearchAdapter:
    source_type = "HACKERNEWS_SEARCH"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        query = locator.strip()
        if not query:
            raise ValueError("HACKERNEWS_SEARCH locator must be a non-empty query")
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={"query": query, "tags": "story", "hitsPerPage": 50},
                headers={"User-Agent": "RAOS/1.1 Acquisition"},
            )
            response.raise_for_status()
            return parse_hackernews_hits(response.json())


def _clean_bilibili_title(value: str | None) -> str:
    text = re.sub(r"</?em[^>]*>", "", value or "")
    return " ".join(BeautifulSoup(text, "lxml").get_text(" ", strip=True).split())


def _bilibili_thumbnail(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value)
    return f"https:{value}" if value.startswith("//") else value


def _bilibili_headers(referer: str) -> dict[str, str]:
    # Anonymous visitor cookie; no authenticated/personal session is used.
    buvid3 = f"{uuid.uuid4()}infoc"
    return {
        "User-Agent": _BROWSER_UA,
        "Referer": referer,
        "Accept": "application/json",
        "Cookie": f"buvid3={buvid3}",
    }


def _bilibili_item(video: dict, *, created_key: str) -> DiscoveredExternalItem | None:
    bvid = str(video.get("bvid") or "").strip()
    title = _clean_bilibili_title(video.get("title"))
    if not bvid or not title:
        return None
    description = str(video.get("description") or "").strip()
    timestamp = video.get(created_key)
    try:
        published = datetime.fromtimestamp(int(timestamp), tz=timezone.utc) if timestamp else None
    except (TypeError, ValueError, OSError):
        published = None
    author = str(video.get("author") or video.get("name") or "").strip() or None
    mid = video.get("mid")
    return DiscoveredExternalItem(
        ref=f"https://www.bilibili.com/video/{bvid}",
        external_id=bvid,
        title=title,
        published_at=published,
        metadata={
            "delivery_mode": "INLINE_PUBLIC",
            "item_type": "VIDEO",
            "normalized_source_type": "VIDEO",
            "platform": "BILIBILI",
            "content_text": description or title,
            "content_scope": "METADATA_ONLY",
            "defer_cognition": True,
            "defer_cognition_reason": "video transcript/full semantic content not acquired",
            "author_name": author,
            "author_id": str(mid) if mid is not None else None,
            "hero_image_url": _bilibili_thumbnail(video.get("pic")),
            "engagement": {
                "views": video.get("play") or 0,
                "favorites": video.get("favorites") or 0,
                "comments": video.get("comment") or video.get("review") or 0,
                "danmaku": video.get("danmaku") or 0,
                "likes": video.get("like") or 0,
            },
        },
    )


def parse_bilibili_search_response(payload: dict) -> list[DiscoveredExternalItem]:
    if payload.get("code") != 0:
        raise RuntimeError(f"Bilibili search rejected: code={payload.get('code')}")
    results = ((payload.get("data") or {}).get("result") or [])
    rows = [_bilibili_item(video, created_key="pubdate") for video in results]
    return [row for row in rows if row is not None]


def parse_bilibili_creator_response(payload: dict) -> list[DiscoveredExternalItem]:
    if payload.get("code") != 0:
        raise RuntimeError(f"Bilibili creator feed rejected: code={payload.get('code')}")
    results = ((((payload.get("data") or {}).get("list") or {}).get("vlist")) or [])
    rows = [_bilibili_item(video, created_key="created") for video in results]
    return [row for row in rows if row is not None]


class BilibiliSearchAdapter:
    source_type = "BILIBILI_SEARCH"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        query = locator.strip()
        if not query:
            raise ValueError("BILIBILI_SEARCH locator must be a non-empty query")
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params={"keyword": query, "search_type": "video", "order": "pubdate", "page": 1, "pagesize": 50},
                headers=_bilibili_headers("https://search.bilibili.com/"),
            )
            response.raise_for_status()
            return parse_bilibili_search_response(response.json())


class BilibiliCreatorAdapter:
    source_type = "BILIBILI_CREATOR"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        mid = locator.strip().rstrip("/").split("/")[-1]
        if not mid.isdigit():
            raise ValueError("BILIBILI_CREATOR locator must be a numeric MID")
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                "https://api.bilibili.com/x/space/arc/search",
                params={"mid": mid, "pn": 1, "ps": 30, "order": "pubdate"},
                headers=_bilibili_headers(f"https://space.bilibili.com/{mid}"),
            )
            response.raise_for_status()
            return parse_bilibili_creator_response(response.json())


def parse_sogou_search_html(payload: str) -> list[DiscoveredExternalItem]:
    soup = BeautifulSoup(payload, "lxml")
    containers = soup.select(".vrwrap, .rb")
    if not containers:
        raise RuntimeError("Sogou search returned no result DOM; possible protection/shell page")
    found: list[DiscoveredExternalItem] = []
    for element in containers:
        anchor = element.select_one("h3 a, .vr-title a, .vrTitle a")
        if anchor is None:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        href = str(anchor.get("href") or "").strip()
        if not title or not href:
            continue
        ref = urljoin("https://www.sogou.com", href)
        snippet_node = element.select_one(".space-txt, .str-text-info, .str_info, .text-layout, p")
        snippet = " ".join(snippet_node.get_text(" ", strip=True).split()) if snippet_node else title
        found.append(
            DiscoveredExternalItem(
                ref=ref,
                title=title,
                metadata={
                    "delivery_mode": "URL_FETCH",
                    "item_type": "ARTICLE",
                    "fallback_content_text": snippet or title,
                    "platform": "SOGOU_SEARCH",
                },
            )
        )
    if not found:
        raise RuntimeError("Sogou result DOM contained no usable results")
    return found


class SogouSearchAdapter:
    source_type = "SOGOU_SEARCH"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        query = locator.strip()
        if not query:
            raise ValueError("SOGOU_SEARCH locator must be a non-empty query")
        url = f"https://www.sogou.com/web?query={quote_plus(query)}&ie=utf-8"
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                url,
                headers={"User-Agent": _BROWSER_UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            )
            response.raise_for_status()
            return parse_sogou_search_html(response.text)
