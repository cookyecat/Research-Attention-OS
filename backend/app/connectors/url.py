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
        "parser": "url-html-v1",
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
