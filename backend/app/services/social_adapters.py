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
    marker = "__RAOS_WEIBO_BR__"
    for br in soup.find_all("br"):
        br.replace_with(marker)
    raw = soup.get_text(" ", strip=True)
    parts = [" ".join(part.split()) for part in raw.split(marker)]
    return "\n".join(parts).strip()


def _iter_weibo_mblogs(data: dict):
    for card in (data.get("data") or {}).get("cards") or []:
        for candidate in [card] + list(card.get("card_group") or []):
            mblog = candidate.get("mblog") or {}
            if mblog:
                yield mblog


def _weibo_preview_needs_hydration(mblog: dict) -> bool:
    if mblog.get("isLongText"):
        return True
    text = _clean_weibo_html(str(mblog.get("text") or ""))
    return bool(text and (text.endswith("全文") or re.search(r"(?:\.{3}|…)[ \u00a0]*全文$", text)))


def _fetch_weibo_long_texts(client: httpx.Client, data: dict, *, headers: dict[str, str]) -> dict[str, str]:
    hydrated: dict[str, str] = {}
    for mblog in _iter_weibo_mblogs(data):
        if not _weibo_preview_needs_hydration(mblog):
            continue
        post_id = str(mblog.get("id") or "").strip()
        bid = str(mblog.get("bid") or "").strip()
        if not post_id or post_id in hydrated:
            continue
        identifiers = [value for value in (post_id, bid) if value]
        preview = _clean_weibo_html(str(mblog.get("text") or ""))

        # The public extend endpoint accepts both the numeric status id and the
        # base62 bid. Treat either as a valid route because timeline payloads and
        # public detail behavior are not perfectly stable across posts.
        for identifier in identifiers:
            try:
                response = client.get("https://m.weibo.cn/statuses/extend", params={"id": identifier}, headers=headers)
                response.raise_for_status()
                payload = response.json()
                long_text = str(((payload.get("data") or {}).get("longTextContent") or "")).strip()
                if payload.get("ok") == 1 and long_text:
                    hydrated[post_id] = long_text
                    break
            except Exception:
                continue
        if post_id in hydrated:
            continue

        # Fall back to the public status detail payload. This is weaker than
        # longTextContent but is still preferable to persisting an explicit
        # "... 全文" preview when the detail body is materially longer.
        for identifier in identifiers:
            try:
                response = client.get("https://m.weibo.cn/statuses/show", params={"id": identifier}, headers=headers)
                response.raise_for_status()
                payload = response.json()
                status = payload.get("data") or {}
                detail_html = str(status.get("text") or "").strip()
                detail_text = _clean_weibo_html(detail_html)
                if payload.get("ok") == 1 and detail_html and len(detail_text) > len(preview) + 20:
                    hydrated[post_id] = detail_html
                    break
            except Exception:
                continue
    return hydrated



def _normalize_weibo_image_url(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url)
    parts = parsed.path.split("/")
    sizes = {"bmiddle", "large", "mw1024", "mw2000", "orj360", "orj480", "orj960", "original", "small", "square", "thumbnail", "wap180"}
    if len(parts) >= 3 and parts[-2].lower() in sizes:
        parts[-2] = "large"
        return parsed._replace(path="/".join(parts)).geturl()
    return url


def _weibo_video_score(key: str, url: str, details: dict | None = None) -> tuple[int, int, int]:
    details = details or {}
    descriptor = f"{key} {url}".lower()
    width = int(details.get("width") or details.get("video_width") or 0)
    height = int(details.get("height") or details.get("video_height") or 0)
    match = re.findall(r"(?<!\d)(\d{3,4})[xX](\d{3,4})(?!\d)", descriptor)
    if match:
        width = max(width, int(match[-1][0]))
        height = max(height, int(match[-1][1]))
    quality = 0
    for token, value in (("4k",2160),("2160",2160),("2k",1440),("1440",1440),("1080",1080),("720",720),("540",540),("480",480),("360",360)):
        if token in descriptor:
            quality = value
            break
    fps = int(float(details.get("fps") or details.get("frame_rate") or (60 if "60fps" in descriptor else 0)))
    return max(height, quality), max(width, height, quality), fps


def _weibo_media_assets(status: dict) -> list[dict]:
    assets: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(asset: dict) -> None:
        url = str(asset.get("url") or "").strip()
        kind = str(asset.get("type") or "").upper()
        if not url or not kind or (kind, url) in seen:
            return
        seen.add((kind, url))
        assets.append(asset)

    def add_pic(pic: dict, fallback_id: str | None = None) -> None:
        pid = str(pic.get("pid") or pic.get("pic_id") or fallback_id or "image")
        largest = pic.get("largest") or pic.get("large") or {}
        largest_url = largest if isinstance(largest, str) else largest.get("url")
        url = largest_url or pic.get("original_pic") or pic.get("url") or pic.get("bmiddle_pic")
        image_url = _normalize_weibo_image_url(str(url)) if url else None
        geo = (largest.get("geo") if isinstance(largest, dict) else None) or pic.get("geo") or {}
        live = pic.get("video") or pic.get("video_url") or pic.get("livephoto_url") or pic.get("motion_url")
        if live:
            add({"type":"VIDEO", "url":str(live), "poster_url":image_url, "media_id":f"{pid}_live", "media_kind":"LIVEPHOTO",
                 "width":int(geo.get("width") or 0), "height":int(geo.get("height") or 0)})
        elif image_url:
            add({"type":"IMAGE", "url":image_url, "media_id":pid,
                 "width":int(geo.get("width") or 0), "height":int(geo.get("height") or 0)})

    mix = ((status.get("mix_media_info") or {}).get("items") or [])
    for item in mix:
        data = item.get("data") or {}
        if item.get("type") == "pic":
            add_pic(data)
        elif item.get("type") == "video":
            page = {"page_info": {"object_id": data.get("object_id"), "media_info": data.get("media_info") or {}, "urls": data.get("urls") or {}}}
            for asset in _weibo_video_assets(page):
                add(asset)

    if not mix:
        pics = status.get("pics") or []
        for pic in pics:
            add_pic(pic)
        if not pics:
            infos = status.get("pic_infos") or {}
            for pid in status.get("pic_ids") or infos.keys():
                if str(pid) in infos:
                    add_pic(infos[str(pid)], str(pid))
        for asset in _weibo_video_assets(status):
            add(asset)
    return assets


def _weibo_video_assets(status: dict) -> list[dict]:
    page = status.get("page_info") or {}
    media = page.get("media_info") or {}
    urls = page.get("urls") or media.get("urls") or {}
    candidates: list[tuple[tuple[int,int,int], str, str]] = []
    seen: set[str] = set()

    def consider(url: object, key: str, details: dict | None = None) -> None:
        if not isinstance(url, str) or not url or url in seen:
            return
        low = url.lower()
        host = urlparse(url).netloc.lower()
        if ".mp4" not in low and ",video" not in low and "weibocdn.com" not in host:
            return
        seen.add(url)
        candidates.append((_weibo_video_score(key, url, details), url, key))

    for mapping in (urls, media):
        if isinstance(mapping, dict):
            for key, value in mapping.items():
                if isinstance(value, str):
                    consider(value, str(key), mapping)
    for item in media.get("playback_list") or []:
        info = item.get("play_info") or item
        if str(info.get("mime") or "").startswith("audio/"):
            continue
        consider(info.get("url"), str(info.get("quality_desc") or info.get("quality_label") or item.get("type") or "playback"), info)
    if not candidates:
        return []
    score, url, key = max(candidates, key=lambda row: row[0])
    poster = page.get("page_pic") or page.get("page_pic_url") or media.get("poster")
    if isinstance(poster, dict):
        poster = poster.get("url")
    return [{"type":"VIDEO", "url":url, "media_id":str(media.get("media_id") or page.get("object_id") or status.get("id") or "video"),
             "quality_hint":key, "poster_url":poster, "width":score[1], "height":score[0]}]


def _merge_weibo_status(preferred: dict, alternate: dict) -> dict:
    merged = dict(alternate)
    for key, value in preferred.items():
        other = alternate.get(key)
        if isinstance(value, dict) and isinstance(other, dict):
            merged[key] = _merge_weibo_status(value, other)
        elif isinstance(value, list) and isinstance(other, list) and key in {"items", "pic_ids", "pics", "playback_list"}:
            merged[key] = value + [item for item in other if item not in value]
        else:
            merged[key] = value
    return merged


def _fetch_weibo_media_details(client: httpx.Client, data: dict, *, headers: dict[str, str]) -> dict[str, dict]:
    details: dict[str, dict] = {}
    desktop_headers = {**headers, "User-Agent": _X_UA, "Referer": "https://weibo.com/"}
    for mblog in _iter_weibo_mblogs(data):
        if not (mblog.get("pics") or mblog.get("pic_infos") or mblog.get("page_info") or (mblog.get("mix_media_info") or {}).get("items")):
            continue
        post_id = str(mblog.get("id") or "").strip()
        if not post_id:
            continue
        mobile = None
        desktop = None
        try:
            response = client.get("https://m.weibo.cn/statuses/show", params={"id": post_id}, headers=headers)
            payload = response.json() if response.status_code == 200 else {}
            if payload.get("ok") == 1 and isinstance(payload.get("data"), dict):
                mobile = payload["data"]
        except Exception:
            pass
        try:
            response = client.get("https://weibo.com/ajax/statuses/show", params={"id": post_id}, headers=desktop_headers)
            payload = response.json() if response.status_code == 200 else {}
            if isinstance(payload, dict) and (payload.get("id") or payload.get("mid")):
                desktop = payload
        except Exception:
            pass
        details[post_id] = _merge_weibo_status(desktop, mobile or mblog) if desktop else (mobile or mblog)
    return details


def parse_weibo_cards(
    data: dict,
    *,
    uid: str,
    long_texts: dict[str, str] | None = None,
    media_details: dict[str, dict] | None = None,
) -> list[DiscoveredExternalItem]:
    cards = (data.get("data") or {}).get("cards") or []
    found: list[DiscoveredExternalItem] = []
    for card in cards:
        candidates = [card] + list(card.get("card_group") or [])
        for candidate in candidates:
            mblog = candidate.get("mblog") or {}
            if not mblog:
                continue
            post_id = str(mblog.get("id") or "").strip()
            hydrated_html = (long_texts or {}).get(post_id)
            text = _clean_weibo_html(str(hydrated_html or mblog.get("text") or ""))
            bid = str(mblog.get("bid") or post_id).strip()
            if not text or not post_id:
                continue
            try:
                published = datetime.strptime(mblog.get("created_at"), "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)
            except Exception:
                published = None
            user = mblog.get("user") or {}
            media_status = (media_details or {}).get(post_id) or mblog
            assets = _weibo_media_assets(media_status)
            hero = next((asset.get("url") for asset in assets if asset.get("type") == "IMAGE"), None)
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
                    "media_assets": assets,
                    "weibo_media_hydrated": bool((media_details or {}).get(post_id)),
                    "weibo_is_long_text": bool(mblog.get("isLongText")),
                    "weibo_text_length": mblog.get("textLength"),
                    "weibo_preview_truncated": _weibo_preview_needs_hydration(mblog),
                    "weibo_long_text_hydrated": bool(hydrated_html),
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
            long_texts = _fetch_weibo_long_texts(client, tdata, headers=headers)
            media_details = _fetch_weibo_media_details(client, tdata, headers=headers)
            return parse_weibo_cards(tdata, uid=uid, long_texts=long_texts, media_details=media_details)
