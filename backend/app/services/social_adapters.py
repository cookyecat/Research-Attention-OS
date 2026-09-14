from __future__ import annotations

import html as html_lib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.acquisition_types import DiscoveredExternalItem

_X_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/131 Safari/537.36"
_WEIBO_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
_WEIBO_HEADERS = {
    "User-Agent": _WEIBO_UA,
    "Referer": "https://m.weibo.cn/",
    "MWeibo-Pwa": "1",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
}


def _curl_text(url: str, *, proxychains: bool) -> str:
    command = ["curl", "-L", "-sS", "--max-time", "25", "-A", _X_UA, url]
    if proxychains and shutil.which("proxychains4"):
        command = ["proxychains4", "-q", *command]
    result = subprocess.run(command, capture_output=True, text=True, timeout=35, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl failed with code {result.returncode}")
    if not result.stdout.strip():
        raise RuntimeError("empty public timeline response")
    return result.stdout


def _x_handle(locator: str) -> str:
    value = locator.strip().rstrip("/")
    if "://" in value:
        path = urlparse(value).path.strip("/")
        value = path.split("/", 1)[0]
    value = value.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", value):
        raise ValueError("X_PUBLIC locator must be a public screen name")
    return value


def parse_x_syndication_html(payload: str, *, handle: str) -> list[DiscoveredExternalItem]:
    soup = BeautifulSoup(payload, "lxml")
    node = soup.find("script", id="__NEXT_DATA__")
    if node is None or not node.string:
        raise ValueError("X public syndication payload has no __NEXT_DATA__")
    data = json.loads(node.string)
    entries = (((data.get("props") or {}).get("pageProps") or {}).get("timeline") or {}).get("entries") or []
    found: list[DiscoveredExternalItem] = []
    for entry in entries:
        if entry.get("type") != "tweet":
            continue
        tweet = ((entry.get("content") or {}).get("tweet") or {})
        text = html_lib.unescape(str(tweet.get("full_text") or "")).strip()
        tweet_id = str(tweet.get("id_str") or "").strip()
        if not text or not tweet_id:
            continue
        try:
            published = datetime.strptime(tweet.get("created_at"), "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)
        except Exception:
            published = None
        media = ((tweet.get("entities") or {}).get("media") or [])
        hero = None
        if media:
            hero = media[0].get("media_url_https") or media[0].get("media_url")
        found.append(DiscoveredExternalItem(
            ref=f"https://x.com/{handle}/status/{tweet_id}",
            external_id=tweet_id,
            title=(text[:117] + "…") if len(text) > 120 else text,
            published_at=published,
            metadata={
                "social_platform": "X",
                "social_author": f"@{handle}",
                "content_text": text,
                "hero_image_url": hero,
                "engagement": {
                    "likes": tweet.get("favorite_count") or 0,
                    "reposts": tweet.get("retweet_count") or 0,
                    "replies": tweet.get("reply_count") or 0,
                    "quotes": tweet.get("quote_count") or 0,
                },
            },
        ))
    found.sort(key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return found


class XPublicAdapter:
    source_type = "X_PUBLIC"

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        handle = _x_handle(locator)
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
        payload = _curl_text(url, proxychains=True)
        return parse_x_syndication_html(payload, handle=handle)


def _clean_weibo_html(value: str) -> str:
    soup = BeautifulSoup(value or "", "lxml")
    return " ".join(soup.get_text(" ", strip=True).split())


def parse_weibo_cards(data: dict, *, uid: str) -> list[DiscoveredExternalItem]:
    cards = (data.get("data") or {}).get("cards") or []
    found: list[DiscoveredExternalItem] = []
    for card in cards:
        candidates = [card] + list(card.get("card_group") or [])
        for candidate in candidates:
            mblog = candidate.get("mblog") or {}
            if not mblog:
                continue
            text = _clean_weibo_html(str(mblog.get("text") or ""))
            post_id = str(mblog.get("id") or "").strip()
            bid = str(mblog.get("bid") or post_id).strip()
            if not text or not post_id:
                continue
            try:
                published = datetime.strptime(mblog.get("created_at"), "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)
            except Exception:
                published = None
            user = mblog.get("user") or {}
            pics = mblog.get("pics") or []
            hero = None
            if pics:
                hero = ((pics[0].get("large") or {}).get("url") or pics[0].get("url"))
            found.append(DiscoveredExternalItem(
                ref=f"https://weibo.com/{uid}/{bid}",
                external_id=post_id,
                title=(text[:77] + "…") if len(text) > 80 else text,
                published_at=published,
                metadata={
                    "social_platform": "WEIBO",
                    "social_author": user.get("screen_name") or uid,
                    "content_text": text,
                    "hero_image_url": hero,
                    "engagement": {
                        "likes": mblog.get("attitudes_count") or 0,
                        "reposts": mblog.get("reposts_count") or 0,
                        "comments": mblog.get("comments_count") or 0,
                    },
                },
            ))
    dedup = {item.external_id: item for item in found}
    values = list(dedup.values())
    values.sort(key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return values


class WeiboPublicAdapter:
    source_type = "WEIBO_PUBLIC"

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=20, follow_redirects=True, headers=_WEIBO_HEADERS)

    def discover(self, locator: str) -> list[DiscoveredExternalItem]:
        uid = locator.strip().rstrip("/").split("/")[-1]
        if not uid.isdigit():
            raise ValueError("WEIBO_PUBLIC locator must be a numeric UID")
        with self._client() as client:
            visitor = client.get(
                "https://visitor.passport.weibo.cn/visitor/genvisitor2",
                params={"cb": "visitor_callback", "from": "weibo.cn"},
                headers={"User-Agent": _WEIBO_UA},
            )
            visitor.raise_for_status()
            match = re.search(r"\((\{.*\})\)", visitor.text)
            if not match:
                raise RuntimeError("Weibo visitor session was not issued")
            payload = json.loads(match.group(1))
            sub = payload["data"]["sub"]
            subp = payload["data"]["subp"]
            headers = {**_WEIBO_HEADERS, "Cookie": f"SUB={sub}; SUBP={subp}"}
            profile = client.get("https://m.weibo.cn/api/container/getIndex", params={"type": "uid", "value": uid}, headers=headers)
            profile.raise_for_status()
            pdata = profile.json()
            if pdata.get("ok") != 1:
                raise RuntimeError(f"Weibo public profile rejected: ok={pdata.get('ok')}")
            tabs = (((pdata.get("data") or {}).get("tabsInfo") or {}).get("tabs") or [])
            container = next((tab.get("containerid") for tab in tabs if tab.get("tabKey") == "weibo"), f"107603{uid}")
            timeline = client.get(
                "https://m.weibo.cn/api/container/getIndex",
                params={"type": "uid", "value": uid, "containerid": container},
                headers=headers,
            )
            timeline.raise_for_status()
            tdata = timeline.json()
            if tdata.get("ok") != 1:
                raise RuntimeError(f"Weibo public timeline rejected: ok={tdata.get('ok')}")
            return parse_weibo_cards(tdata, uid=uid)
