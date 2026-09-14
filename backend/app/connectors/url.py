from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.connectors.base import DiscoveredItem, ParsedSource, RawSource
from app.services.fingerprint import NormalizedSource, fingerprint as make_fingerprint

BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}


class SSRFBlocked(ValueError):
    pass


def _host_is_private(hostname: str) -> bool:
    host = hostname.strip("[]").lower()
    if host in BLOCKED_HOSTS or host.endswith(".localhost"):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFBlocked(f"Cannot resolve host: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SSRFBlocked("Only http/https URLs are allowed")
    if not parsed.hostname:
        raise SSRFBlocked("URL has no hostname")
    if _host_is_private(parsed.hostname):
        raise SSRFBlocked("Internal/private URLs are blocked")
    return url


def _normalized_media_identity(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    return f"{parsed.netloc.lower()}{parsed.path}"


def _image_url(tag, base_url: str) -> str | None:
    for key in ("src", "data-src", "data-lazy-src"):
        value = tag.get(key)
        if value and not str(value).startswith("data:"):
            return urljoin(base_url, str(value).strip())
    srcset = tag.get("srcset") or tag.get("data-srcset")
    if srcset:
        candidates = [part.strip().split()[0] for part in str(srcset).split(",") if part.strip()]
        if candidates:
            return urljoin(base_url, candidates[-1])
    return None


def _context_text(tag) -> str | None:
    context_tag = tag.find_previous("p") or tag.find_next("p")
    if context_tag is None:
        return None
    text = context_tag.get_text(" ", strip=True)
    return text[:700] or None


def _media_caption(tag) -> str | None:
    for parent in tag.parents:
        if getattr(parent, "name", None) != "figure":
            continue
        caption_tag = parent.find("figcaption")
        if caption_tag is not None:
            text = caption_tag.get_text(" ", strip=True)
            if text:
                return text
    return None


def _extract_article_images(soup: BeautifulSoup, url: str, hero_image_url: str | None) -> list[dict]:
    hero_identity = _normalized_media_identity(hero_image_url)
    images: list[dict] = []
    seen: set[str] = set()
    for figure in soup.find_all("figure"):
        # A video's poster/fallback is not a substantive article image.
        if figure.find("video") is not None or figure.find("iframe") is not None:
            continue
        image = figure.find("img")
        if image is None or image.get("role") == "presentation" or image.get("aria-hidden") == "true":
            continue
        image_url = _image_url(image, url)
        identity = _normalized_media_identity(image_url)
        if not image_url or not identity or identity == hero_identity or identity in seen:
            continue
        alt = str(image.get("alt") or "").strip() or None
        caption = _media_caption(image)
        images.append({"url": image_url, "alt": alt, "caption": caption, "context_text": _context_text(figure)})
        seen.add(identity)
        if len(images) >= 6:
            break
    return images


def _trusted_embed(src: str) -> tuple[str, str] | None:
    parsed = urlparse(src)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtube-nocookie.com"} and parsed.path.startswith("/embed/"):
        return "YOUTUBE", src
    if host == "player.vimeo.com" and parsed.path.startswith("/video/"):
        return "VIMEO", src
    return None


def _extract_media_assets(soup: BeautifulSoup, url: str, article_images: list[dict]) -> list[dict]:
    assets: list[dict] = []
    seen: set[str] = set()
    for image in article_images:
        identity = _normalized_media_identity(image.get("url"))
        if identity:
            seen.add(identity)
        assets.append({"type": "IMAGE", **image})

    for iframe in soup.find_all("iframe"):
        src = str(iframe.get("src") or "").strip()
        if not src:
            continue
        embed = _trusted_embed(urljoin(url, src))
        if embed is None:
            continue
        provider, embed_url = embed
        identity = f"embed:{embed_url}"
        if identity in seen:
            continue
        assets.append({
            "type": "EMBED",
            "provider": provider,
            "embed_url": embed_url,
            "title": str(iframe.get("title") or "").strip() or None,
            "context_text": _context_text(iframe),
            "aspect_ratio": "16:9",
        })
        seen.add(identity)

    for video in soup.find_all("video"):
        if video.find_parent("noscript") is not None:
            continue
        source = video.find("source")
        media_url = str(video.get("src") or "").strip()
        if not media_url and source is not None:
            media_url = str(source.get("src") or source.get("data-src") or "").strip()
        if not media_url:
            continue
        media_url = urljoin(url, media_url)
        identity = _normalized_media_identity(media_url)
        if not identity or identity in seen:
            continue
        poster = None
        if str(video.get("data-poster-is-fallback") or "").lower() != "true":
            raw_poster = str(video.get("poster") or "").strip()
            poster = urljoin(url, raw_poster) if raw_poster else None
        assets.append({
            "type": "VIDEO",
            "url": media_url,
            "mime_type": str(source.get("type") or "").strip() or None if source is not None else None,
            "poster_url": poster,
            "caption": _media_caption(video),
            "context_text": _context_text(video),
        })
        seen.add(identity)
    return assets[:10]


def _cache_presentation_media(metadata: dict) -> None:
    from app.services.media_cache import cache_remote_media

    hero = metadata.get("hero_image_url")
    if hero:
        metadata["hero_image_cached_url"] = cache_remote_media(hero)
    for image in metadata.get("article_images") or []:
        image["cached_url"] = cache_remote_media(image.get("url"))
    for asset in metadata.get("media_assets") or []:
        if asset.get("type") in {"IMAGE", "VIDEO"}:
            asset["cached_url"] = cache_remote_media(asset.get("url"))
        if asset.get("poster_url"):
            asset["poster_cached_url"] = cache_remote_media(asset.get("poster_url"))


def _extract_readable(html: str, url: str) -> tuple[str | None, str | None, dict]:
    soup = BeautifulSoup(html, "lxml")
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    canonical = None
    link = soup.find("link", rel=lambda value: value and "canonical" in value)
    if link and link.get("href"):
        canonical = urljoin(url, link["href"])
    author = None
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = author_meta["content"]
    published = None
    time_meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find(
        "meta", attrs={"name": "date"}
    )
    if time_meta and time_meta.get("content"):
        published = time_meta["content"]

    hero_image_url = None
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"}, {"property": "og:image:url"}):
        image_meta = soup.find("meta", attrs=attrs)
        if image_meta and image_meta.get("content"):
            hero_image_url = urljoin(url, image_meta["content"].strip())
            break
    hero_image_alt = None
    for attrs in ({"property": "og:image:alt"}, {"name": "twitter:image:alt"}):
        alt_meta = soup.find("meta", attrs=attrs)
        if alt_meta and alt_meta.get("content"):
            hero_image_alt = alt_meta["content"].strip()
            break
    article_images = _extract_article_images(soup, url, hero_image_url)
    media_assets = _extract_media_assets(soup, url, article_images)
    try:
        import trafilatura

        extracted = trafilatura.extract(html, url=url, include_comments=False) or ""
    except Exception:
        extracted = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
    metadata = {
        "origin_url": url,
        "canonical_url": canonical,
        "author": author,
        "published": published,
        "hero_image_url": hero_image_url,
        "hero_image_alt": hero_image_alt,
        "article_images": article_images,
        "media_assets": media_assets,
        "parser": "url-html-v4-media-assets",
    }
    return title, extracted, metadata


class URLConnector:
    def discover(self, query_or_config) -> list[DiscoveredItem]:
        return []

    def fetch(self, item: DiscoveredItem) -> RawSource:
        url = validate_public_url(item.ref)
        with httpx.Client(follow_redirects=True, timeout=settings.url_fetch_timeout_seconds) as client:
            response = client.get(url, headers={"User-Agent": "RAOS/1.1"})
            response.raise_for_status()
            final_url = str(response.url)
            validate_public_url(final_url)
            return RawSource(
                payload=response.content,
                content_type=response.headers.get("content-type", "text/html"),
                origin=final_url,
                metadata={"requested_url": url, "final_url": final_url},
            )

    def parse(self, raw: RawSource) -> ParsedSource:
        html = raw.payload.decode("utf-8", errors="replace") if isinstance(raw.payload, bytes) else raw.payload
        title, text, metadata = _extract_readable(html, raw.origin)
        _cache_presentation_media(metadata)
        metadata.update(raw.metadata)
        return ParsedSource(title=title, text=text, metadata=metadata, reference_candidates=[])

    def normalize(self, parsed: ParsedSource) -> NormalizedSource:
        authors = []
        if parsed.metadata.get("author"):
            authors = [parsed.metadata["author"]]
        return NormalizedSource(
            source_type="URL",
            title=parsed.title,
            canonical_url=parsed.metadata.get("canonical_url") or parsed.metadata.get("final_url"),
            content_text=parsed.text,
            author_entities=authors,
            publisher=parsed.metadata.get("publisher"),
            raw_metadata=parsed.metadata,
            ingestion_method="URL_FETCH",
        )

    def fingerprint(self, normalized: NormalizedSource) -> str:
        return make_fingerprint(normalized)

    def ingest(self, url: str) -> NormalizedSource:
        raw = self.fetch(DiscoveredItem(ref=url, metadata={}))
        return self.normalize(self.parse(raw))
