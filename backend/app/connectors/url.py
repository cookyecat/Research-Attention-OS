from __future__ import annotations

import difflib
import ipaddress
import re
import socket
import time
from urllib.parse import parse_qs, urljoin, urlparse

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


def _reference_url_identity(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}".rstrip("/")


def _unwrap_reference_transport_url(value: str) -> str:
    """Recover the publisher target from known transport-only redirect wrappers."""
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if "wechat2rss" in host and "link-proxy" in parsed.path:
        target = (parse_qs(parsed.query).get("u") or [None])[-1]
        if target and _reference_url_identity(target):
            return target
    return value


def _extract_explicit_references(root, base_url: str, *, limit: int = 80) -> list[dict]:
    """Extract literal outbound links as high-confidence CITES candidates.

    This proves only that the article explicitly links the target. It does not
    claim DERIVED_FROM, SAME_EVENT, independence, or original-source status.
    """
    base_identity = _reference_url_identity(base_url)
    refs: list[dict] = []
    seen: set[str] = set()
    for link in root.find_all("a"):
        raw_href = str(link.get("href") or link.get("data-href") or "").strip()
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        href = _unwrap_reference_transport_url(urljoin(base_url, raw_href))
        identity = _reference_url_identity(href)
        if not identity or identity == base_identity or identity in seen:
            continue
        parsed = urlparse(href)
        if parsed.path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".mp3")):
            # Linked media assets are not article-level provenance candidates.
            # PDFs remain references because papers/reports are commonly linked directly.
            continue
        anchor_text = re.sub(r"\s+", " ", link.get_text(" ", strip=True)).strip()
        context = _context_text(link, root)
        raw_text = anchor_text or context or href
        refs.append(
            {
                "raw_text": raw_text[:2000],
                "title": (anchor_text or None),
                "authors": None,
                "year": None,
                "venue": None,
                "doi": None,
                "arxiv_id": None,
                "url": href,
                "confidence": 1.0,
                "evidence_kind": "explicit_href",
                "relation_hint": "CITES",
                "anchor_text": anchor_text or None,
                "context_text": context,
            }
        )
        seen.add(identity)
        if len(refs) >= max(1, int(limit)):
            break
    return refs


def _context_text(tag, boundary=None) -> str | None:
    """Return the nearest non-empty semantic text around media.

    Media is often wrapped in an otherwise-empty <p>. Treating that wrapper as
    context loses the real placement anchor, so walk to nearby headings/paragraphs
    and ignore the media's own empty ancestor container.
    """
    semantic_names = ["p", "h2", "h3", "h4"]

    def within_boundary(candidate) -> bool:
        if boundary is None:
            return True
        node = candidate
        while node is not None:
            if node is boundary:
                return True
            node = getattr(node, "parent", None)
        return False

    for candidate in tag.find_all_previous(semantic_names, limit=12):
        if candidate is tag or tag in candidate.descendants or not within_boundary(candidate):
            continue
        text = candidate.get_text(" ", strip=True)
        if text:
            return text[:700]
    for candidate in tag.find_all_next(semantic_names, limit=12):
        if candidate is tag or tag in candidate.descendants or not within_boundary(candidate):
            continue
        text = candidate.get_text(" ", strip=True)
        if text:
            return text[:700]
    return None


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


def _semantic_hero_image(soup: BeautifulSoup, base_url: str) -> tuple[str | None, str | None]:
    """Prefer a publisher-visible title hero over social-card metadata.

    OG/Twitter images are distribution assets and may differ from what the reader
    sees in the article. A bounded container that contains both the article H1 and
    a substantive image is stronger presentation evidence.
    """
    for node in soup.find_all(["header", "section", "div"]):
        attrs = " ".join([
            *[str(value) for value in (node.get("class") or []) if value],
            str(node.get("id") or ""),
        ]).casefold()
        if "hero" not in attrs and "article-header" not in attrs and "post-header" not in attrs:
            continue
        if node.find("h1") is None:
            continue
        image = node.find("img")
        if image is None or _inside_editorial_boilerplate(image):
            continue
        image_url = _image_url(image, base_url)
        if not image_url or _small_graphic_url(image_url):
            continue
        return image_url, str(image.get("alt") or "").strip() or None
    return None, None


ARTICLE_BODY_SELECTORS = (
    ".entry-content",
    "[itemprop='articleBody']",
    ".post-content",
    ".article-content",
    ".article-body",
    ".c-article-body",
)


def _is_openai_url(url: str | None) -> bool:
    try:
        host = (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return False
    return host in {"openai.com", "www.openai.com"}


def _article_root(soup: BeautifulSoup, url: str | None = None):
    # OpenAI's current article shell exposes a stable semantic body through
    # data-toc-content even when the outer <article> also includes hero, author,
    # footnotes and recirculation cards. Treat it as publisher policy.
    if _is_openai_url(url):
        node = soup.select_one("article [data-toc-content]")
        if node is not None:
            return node
    # Prefer the publisher's semantic body over the outer <article>, which often
    # also contains hero art, sidebars, related stories, comments and navigation.
    for selector in ARTICLE_BODY_SELECTORS:
        node = soup.select_one(selector)
        if node is not None:
            return node
    return soup.find("article") or soup.find("main") or soup.body or soup


def _has_explicit_article_body(soup: BeautifulSoup, root, url: str | None = None) -> bool:
    if _is_openai_url(url) and soup.select_one("article [data-toc-content]") is root:
        return True
    return any(soup.select_one(selector) is root for selector in ARTICLE_BODY_SELECTORS)


def _extract_article_images(root, url: str, hero_image_url: str | None, author: str | None = None, *, limit: int = 12) -> list[dict]:
    hero_identity = _normalized_media_identity(hero_image_url)
    images: list[dict] = []
    seen: set[str] = set()
    for image in root.find_all("img"):
        # A video's poster/fallback, tracking pixel, icon or explicitly hidden image
        # is not substantive article evidence.
        if image.find_parent(["video", "noscript"]) is not None:
            continue
        if image.get("role") == "presentation" or image.get("aria-hidden") == "true":
            continue
        try:
            width = int(str(image.get("width") or "0").replace("px", ""))
            height = int(str(image.get("height") or "0").replace("px", ""))
            if width and height and (width < 120 or height < 90):
                continue
        except ValueError:
            pass
        image_url = _image_url(image, url)
        identity = _normalized_media_identity(image_url)
        if (
            not image_url
            or not identity
            or identity == hero_identity
            or identity in seen
            or _small_graphic_url(image_url)
            or _inside_editorial_boilerplate(image)
        ):
            continue
        alt = str(image.get("alt") or "").strip() or None
        if alt and author and _normalized_block_text(alt) == _normalized_block_text(author):
            continue
        caption = _media_caption(image)
        context_node = image.find_parent("figure") or image.parent or image
        images.append({"url": image_url, "alt": alt, "caption": caption, "context_text": _context_text(context_node, root)})
        seen.add(identity)
        if len(images) >= max(1, int(limit)):
            break
    return images


def _extract_article_blocks(root, url: str, article_images: list[dict], *, text_getter=None) -> list[dict]:
    """Preserve presentation structure without changing canonical cognition text."""
    images_by_identity = {
        _normalized_media_identity(image.get("url")): image
        for image in article_images
        if _normalized_media_identity(image.get("url"))
    }
    blocks: list[dict] = []
    block_tags = {"h2", "h3", "h4", "p", "ul", "ol", "blockquote", "figure", "table"}

    def text_of(tag) -> str:
        if text_getter is not None:
            return str(text_getter(tag) or "").strip()
        return tag.get_text(" ", strip=True)

    def nested_in_block(tag) -> bool:
        parent = tag.parent
        while parent is not None and parent is not root:
            if getattr(parent, "name", None) in block_tags:
                return True
            parent = parent.parent
        return False

    def add_image(image_tag) -> None:
        image_url = _image_url(image_tag, url)
        identity = _normalized_media_identity(image_url)
        image = images_by_identity.get(identity)
        if not image:
            return
        if any(block.get("type") == "image" and block.get("url") == image.get("url") for block in blocks):
            return
        blocks.append({"type": "image", **image})

    for tag in root.find_all(list(block_tags)):
        if nested_in_block(tag) or _inside_editorial_boilerplate(tag):
            continue
        name = tag.name.lower()
        if name in {"h2", "h3", "h4"}:
            text = text_of(tag)
            if text:
                blocks.append({"type": "heading", "level": int(name[1]), "text": text})
            continue
        if name in {"ul", "ol"}:
            items = []
            for item in tag.find_all("li", recursive=False):
                text = text_of(item)
                if not text:
                    continue
                lead_tag = item.find(["strong", "b"])
                lead = text_of(lead_tag) if lead_tag is not None else None
                items.append({"text": text, "lead": lead or None})
            if items:
                blocks.append({"type": "list", "ordered": name == "ol", "items": items})
            continue
        if name == "blockquote":
            text = text_of(tag)
            if text:
                blocks.append({"type": "quote", "text": text})
            continue
        if name == "table":
            rows = []
            for row in tag.find_all("tr"):
                if row.find_parent("table") is not tag:
                    continue
                cells = [text_of(cell) for cell in row.find_all(["th", "td"], recursive=False)]
                if any(cells):
                    rows.append(cells)
            if rows:
                first_row = tag.find("tr")
                has_header = bool(first_row and first_row.find("th"))
                headers = rows[0] if (has_header or len(rows) > 1) else []
                body_rows = rows[1:] if headers else rows
                blocks.append({"type": "table", "headers": headers, "rows": body_rows})
            continue
        if name == "figure":
            image = tag.find("img")
            if image is not None:
                add_image(image)
            continue
        if name == "p":
            text = text_of(tag)
            if text:
                blocks.append({"type": "paragraph", "text": text})
            for image in tag.find_all("img"):
                add_image(image)
    return blocks



def _trim_editorial_tail(blocks: list[dict]) -> list[dict]:
    """Stop before conventional publisher recirculation sections."""
    stop_headings = {
        "related content", "related stories", "recommended", "recommended for you",
        "most popular", "more in", "more from", "latest", "latest stories",
    }
    for index, block in enumerate(blocks):
        if str(block.get("type") or "").lower() != "heading":
            continue
        heading = _normalized_block_text(block.get("text"))
        if heading in stop_headings:
            return blocks[:index]
    return blocks


def _blocks_to_text(blocks: list[dict]) -> str:
    """Project cleaned presentation structure back to canonical readable text."""
    lines: list[str] = []
    for block in blocks:
        kind = str(block.get("type") or "").lower()
        if kind in {"paragraph", "heading", "quote"}:
            text = str(block.get("text") or "").strip()
            if text:
                lines.append(text)
        elif kind == "list":
            for item in block.get("items") or []:
                text = str(item if isinstance(item, str) else item.get("text") or "").strip()
                if text:
                    lines.append(text)
        elif kind == "table":
            headers = block.get("headers") or []
            rows = block.get("rows") or []
            for row in ([headers] if headers else []) + list(rows):
                values = [str(cell or "").strip() for cell in row]
                if any(values):
                    lines.append(" | ".join(values))
    return "\n".join(lines).strip()


def _normalized_block_text(value: str | None) -> str:
    return " ".join(str(value or "").split()).strip().casefold()


def _small_graphic_url(url: str | None) -> bool:
    if not url:
        return True
    try:
        query = parse_qs(urlparse(url).query)
        for key in ("w", "width"):
            raw = query.get(key, [None])[-1]
            if raw is not None and int(float(raw)) <= 160:
                return True
    except (TypeError, ValueError):
        pass
    return False



def _inside_editorial_boilerplate(tag) -> bool:
    tokens = (
        "byline", "author", "related", "newsletter", "share", "sharing",
        "promo", "recirc", "recommend", "sidebar", "footer",
        "access-wall", "registration-wall", "paywall", "login-wall",
        # Publisher image viewers duplicate body media for zoom/lightbox UI.
        # These are interaction chrome, not additional article evidence.
        "image-modal", "modal-slide", "media-modal", "gallery-modal", "lightbox",
    )
    node = tag
    depth = 0
    while node is not None and depth <= 3:
        attrs = []
        attrs.extend(str(value) for value in (node.get("class") or []) if value)
        for key in ("id", "role", "aria-label", "data-testid", "data-component"):
            value = node.get(key)
            if value:
                attrs.append(str(value))
        normalized_attrs = [value.casefold() for value in attrs]
        haystack = " ".join(normalized_attrs)
        for token in tokens:
            if token != "sidebar":
                if token in haystack:
                    return True
                continue
            # Layout wrappers such as NVIDIA's ``post-with-sidebar`` describe
            # the article grid, not the semantic identity of every descendant.
            # Only treat sidebar as boilerplate when the attribute actually
            # names a sidebar region; ``with-sidebar`` / ``has-sidebar`` are
            # layout modifiers and must not erase the article body hierarchy.
            for value in normalized_attrs:
                if "sidebar" not in value:
                    continue
                if "with-sidebar" in value or "has-sidebar" in value:
                    continue
                return True
        node = getattr(node, "parent", None)
        depth += 1
    return False


def _insert_missing_dom_images(blocks: list[dict], images: list[dict], dom_images: list[dict]) -> tuple[list[dict], list[dict]]:
    seen = {_normalized_media_identity(image.get("url")) for image in images}
    for image in dom_images:
        identity = _normalized_media_identity(image.get("url"))
        if not identity or identity in seen:
            continue
        image_block = {"type": "image", **image}
        context = _normalized_block_text(image.get("context_text"))
        insert_at = None
        if context:
            paragraph_candidates: list[tuple[float, int]] = []
            for index, block in enumerate(blocks):
                if block.get("type") != "paragraph":
                    continue
                text = _normalized_block_text(block.get("text"))
                if text == context or (len(context) >= 32 and (context in text or text in context)):
                    insert_at = index + 1
                    break
                if text and len(context) >= 32:
                    # Publishers frequently normalize smart quotes/spacing between the
                    # DOM and their cleaned article representation. A high sequence
                    # similarity is a placement anchor, not semantic inference.
                    paragraph_candidates.append((difflib.SequenceMatcher(None, context, text).ratio(), index))
            if insert_at is None and paragraph_candidates:
                score, index = max(paragraph_candidates)
                if score >= 0.78:
                    insert_at = index + 1
        if insert_at is None:
            blocks.append(image_block)
        else:
            blocks.insert(insert_at, image_block)
        images.append(image)
        seen.add(identity)
    return blocks, images


def _list_leads(root) -> dict[str, str]:
    leads: dict[str, str] = {}
    for item in root.find_all("li"):
        text = item.get_text(" ", strip=True)
        lead_tag = item.find(["strong", "b"])
        lead = lead_tag.get_text(" ", strip=True) if lead_tag is not None else ""
        if text and lead:
            leads[_normalized_block_text(text)] = lead
    return leads


def _extract_trafilatura_blocks(
    xml: str | None,
    url: str,
    hero_image_url: str | None,
    dom_images: list[dict],
    root,
) -> tuple[list[dict], list[dict]]:
    """Build presentation blocks from Trafilatura's cleaned main-content tree.

    The XML main tree is intentionally used as the editorial boundary: it keeps
    headings/lists/graphics while dropping newsletter, share, related-story and
    author-card chrome that frequently lives inside publisher <article> nodes.
    """
    if not xml:
        return [], []
    tree = BeautifulSoup(xml, "xml")
    main = tree.find("main")
    if main is None:
        return [], []
    hero_identity = _normalized_media_identity(hero_image_url)
    dom_by_identity = {
        _normalized_media_identity(image.get("url")): image
        for image in dom_images
        if _normalized_media_identity(image.get("url"))
    }
    lead_by_text = _list_leads(root)
    blocks: list[dict] = []
    images: list[dict] = []
    seen_images: set[str] = set()
    block_tags = {"p", "head", "list", "quote", "blockquote", "graphic", "table"}

    def nested_in_block(tag) -> bool:
        parent = tag.parent
        while parent is not None and parent is not main:
            if getattr(parent, "name", None) in block_tags:
                return True
            parent = parent.parent
        return False

    for tag in main.find_all(list(block_tags)):
        if nested_in_block(tag):
            continue
        name = tag.name.lower()
        if name == "head":
            rend = str(tag.get("rend") or "h2").lower()
            if rend == "h1":
                continue
            try:
                level = int(rend.removeprefix("h"))
            except ValueError:
                level = 2
            text = tag.get_text(" ", strip=True)
            if text:
                blocks.append({"type": "heading", "level": max(2, min(4, level)), "text": text})
            continue
        if name == "p":
            text = tag.get_text(" ", strip=True)
            if text:
                blocks.append({"type": "paragraph", "text": text})
            continue
        if name == "list":
            items = []
            for item in tag.find_all("item", recursive=False):
                text = item.get_text(" ", strip=True)
                if text:
                    items.append({"text": text, "lead": lead_by_text.get(_normalized_block_text(text))})
            if items:
                blocks.append({"type": "list", "ordered": str(tag.get("rend") or "ul").lower() == "ol", "items": items})
            continue
        if name in {"quote", "blockquote"}:
            text = tag.get_text(" ", strip=True)
            if text:
                blocks.append({"type": "quote", "text": text})
            continue
        if name == "table":
            rows = []
            for row in tag.find_all("row", recursive=False):
                cells = [cell.get_text(" ", strip=True) for cell in row.find_all("cell", recursive=False)]
                if any(cells):
                    rows.append(cells)
            if rows:
                headers = rows[0] if len(rows) > 1 else []
                body_rows = rows[1:] if headers else rows
                blocks.append({"type": "table", "headers": headers, "rows": body_rows})
            continue
        if name == "graphic":
            raw_url = str(tag.get("src") or "").strip()
            image_url = urljoin(url, raw_url) if raw_url else None
            identity = _normalized_media_identity(image_url)
            if not image_url or not identity or identity == hero_identity or identity in seen_images or _small_graphic_url(image_url):
                continue
            base = dict(dom_by_identity.get(identity) or {})
            image = {
                "url": image_url,
                "alt": str(tag.get("alt") or base.get("alt") or "").strip() or None,
                "caption": base.get("caption"),
                "context_text": base.get("context_text"),
            }
            blocks.append({"type": "image", **image})
            images.append(image)
            seen_images.add(identity)
    return blocks, images


def _trusted_embed(src: str) -> tuple[str, str] | None:
    parsed = urlparse(src)
    host = (parsed.hostname or "").lower()
    if host in {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtube-nocookie.com"} and parsed.path.startswith("/embed/"):
        return "YOUTUBE", src
    if host == "player.vimeo.com" and parsed.path.startswith("/video/"):
        return "VIMEO", src
    if host == "mp.weixin.qq.com" and parsed.path == "/mp/readtemplate":
        query = parse_qs(parsed.query)
        if (query.get("action") or [""])[-1] == "mpvideo" and (query.get("vid") or [""])[-1]:
            return "WECHAT_VIDEO", src
    return None


def _extract_media_assets(soup: BeautifulSoup, url: str, article_images: list[dict], *, limit: int = 10) -> list[dict]:
    assets: list[dict] = []
    seen: set[str] = set()
    for image in article_images:
        identity = _normalized_media_identity(image.get("url"))
        if identity:
            seen.add(identity)
        assets.append({"type": "IMAGE", **image})

    for iframe in soup.find_all("iframe"):
        src = str(iframe.get("src") or iframe.get("data-src") or "").strip()
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
            "context_text": _context_text(iframe, soup),
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
            "context_text": _context_text(video, soup),
        })
        seen.add(identity)
    return assets[: max(1, int(limit))]


def _cache_presentation_media(metadata: dict) -> None:
    from app.services.media_cache import cache_remote_media

    hero = metadata.get("hero_image_url")
    if hero:
        metadata["hero_image_cached_url"] = cache_remote_media(hero)
    cached_by_url: dict[str, str | None] = {}
    for image in metadata.get("article_images") or []:
        cached = cache_remote_media(image.get("url"))
        image["cached_url"] = cached
        if image.get("url"):
            cached_by_url[str(image["url"])] = cached
    for block in metadata.get("article_blocks") or []:
        if block.get("type") == "image" and block.get("url"):
            block["cached_url"] = cached_by_url.get(str(block["url"])) or cache_remote_media(block.get("url"))
    for asset in metadata.get("media_assets") or []:
        if asset.get("type") in {"IMAGE", "VIDEO"}:
            asset["cached_url"] = cached_by_url.get(str(asset.get("url") or "")) or cache_remote_media(asset.get("url"))
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
    semantic_hero_url, semantic_hero_alt = _semantic_hero_image(soup, url)
    if semantic_hero_url:
        hero_image_url = semantic_hero_url
        hero_image_alt = semantic_hero_alt or hero_image_alt
    article_root = _article_root(soup, url)
    explicit_article_body = _has_explicit_article_body(soup, article_root, url)
    reference_candidates = _extract_explicit_references(article_root, url)
    dom_article_images = _extract_article_images(article_root, url, hero_image_url, author)
    dom_article_blocks = _extract_article_blocks(article_root, url, dom_article_images)
    if _is_openai_url(url):
        lead = soup.select_one("article [data-article-hero-copy-region='subhead']")
        lead_text = lead.get_text(" ", strip=True) if lead is not None else ""
        if lead_text and not any(_normalized_block_text(block.get("text")) == _normalized_block_text(lead_text) for block in dom_article_blocks[:2]):
            dom_article_blocks.insert(0, {"type": "paragraph", "text": lead_text})
    structure_xml = ""
    try:
        import trafilatura

        extraction_html = str(article_root) if explicit_article_body else html
        extracted = trafilatura.extract(extraction_html, url=url, include_comments=False, include_tables=True) or ""
        structure_xml = trafilatura.extract(
            extraction_html,
            url=url,
            include_comments=False,
            output_format="xml",
            include_images=True,
            include_links=False,
            include_tables=True,
        ) or ""
    except Exception:
        extracted = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
    article_blocks, article_images = _extract_trafilatura_blocks(
        structure_xml, url, hero_image_url, dom_article_images, article_root
    )
    dom_structure = sum(block.get("type") in {"heading", "list", "quote", "table"} for block in dom_article_blocks)
    xml_paragraphs = sum(block.get("type") == "paragraph" for block in article_blocks)
    if explicit_article_body and dom_article_blocks:
        # A publisher-provided semantic body is a stronger structural boundary
        # than whole-page heuristics. Keep its cleaned hierarchy and use it to
        # derive canonical text so compatibility banners/paywalls never become
        # cognition input.
        article_images = dom_article_images
        article_blocks = dom_article_blocks
        extracted = _blocks_to_text(article_blocks)
    elif article_blocks and not (xml_paragraphs <= 1 and dom_structure > 0):
        article_blocks, article_images = _insert_missing_dom_images(
            article_blocks, article_images, dom_article_images
        )
    else:
        article_images = dom_article_images
        article_blocks = dom_article_blocks
    article_blocks = _trim_editorial_tail(article_blocks)
    # Keep article_images consistent with the surviving image blocks after any
    # publisher-recirculation tail is trimmed.
    surviving_image_ids = {
        _normalized_media_identity(block.get("url"))
        for block in article_blocks
        if block.get("type") == "image" and block.get("url")
    }
    article_images = [
        image for image in article_images
        if _normalized_media_identity(image.get("url")) in surviving_image_ids
    ]
    media_assets = _extract_media_assets(article_root, url, article_images)
    metadata = {
        "origin_url": url,
        "canonical_url": canonical,
        "author": author,
        "published": published,
        "hero_image_url": hero_image_url,
        "hero_image_alt": hero_image_alt,
        "article_images": article_images,
        "article_blocks": article_blocks,
        "article_structure_version": "structured-blocks-v3-tables",
        "media_assets": media_assets,
        "reference_candidates": reference_candidates,
        "parser": "url-html-v9-publisher-adapters",
    }
    return title, extracted, metadata


class URLConnector:
    def discover(self, query_or_config) -> list[DiscoveredItem]:
        return []

    def fetch(self, item: DiscoveredItem) -> RawSource:
        url = validate_public_url(item.ref)
        with httpx.Client(follow_redirects=True, timeout=settings.url_fetch_timeout_seconds) as client:
            response = client.get(url, headers={"User-Agent": "RAOS/1.1"})
            final_url = str(response.url)
            validate_public_url(final_url)
            if _is_openai_url(final_url) and response.status_code in {403, 429}:
                # OpenAI currently fronts public article pages with a JS/cookie
                # challenge for non-browser clients. Preserve publisher identity,
                # but use a rendered reader fallback for the public article body.
                # The fallback itself can transiently return the publisher challenge,
                # so accept it only after semantic completeness checks.
                fallback_url = f"https://r.jina.ai/{final_url}"
                rendered = None
                fallback_attempts = 0
                for attempt, delay in enumerate((0.0, 0.8, 2.0), start=1):
                    if delay:
                        time.sleep(delay)
                    candidate = client.get(
                        fallback_url,
                        headers={
                            "X-Return-Format": "html",
                            "Accept": "text/plain",
                            "User-Agent": "RAOS/1.1",
                        },
                        timeout=max(float(settings.url_fetch_timeout_seconds), 45.0),
                    )
                    fallback_attempts = attempt
                    if candidate.status_code >= 400:
                        continue
                    rendered_text = candidate.text
                    if "<article" in rendered_text and "data-toc-content" in rendered_text:
                        rendered = candidate
                        break
                if rendered is None:
                    # Never persist a challenge/interstitial page as article truth.
                    response.raise_for_status()
                return RawSource(
                    payload=rendered.content,
                    content_type="text/html; charset=utf-8",
                    origin=final_url,
                    metadata={
                        "requested_url": url,
                        "final_url": final_url,
                        "publisher_fetch_mode": "openai-rendered-fallback-v1",
                        "publisher_direct_status": response.status_code,
                        "publisher_direct_blocked": True,
                        "publisher_fallback_provider": "jina-reader",
                        "publisher_fallback_attempts": fallback_attempts,
                    },
                )
            response.raise_for_status()
            return RawSource(
                payload=response.content,
                content_type=response.headers.get("content-type", "text/html"),
                origin=final_url,
                metadata={"requested_url": url, "final_url": final_url, "publisher_fetch_mode": "direct"},
            )

    def parse(self, raw: RawSource) -> ParsedSource:
        html = raw.payload.decode("utf-8", errors="replace") if isinstance(raw.payload, bytes) else raw.payload
        title, text, metadata = _extract_readable(html, raw.origin)
        _cache_presentation_media(metadata)
        metadata.update(raw.metadata)
        if metadata.get("publisher_fetch_mode") == "openai-rendered-fallback-v1":
            metadata["publisher_dynamic_media_status"] = "unverified_from_rendered_fallback"
            metadata["publisher_dynamic_media_note"] = (
                "Client-hydrated OpenAI media may not be exposed by the rendered fallback; "
                "standard VIDEO/EMBED assets are preserved when present."
            )
        return ParsedSource(
            title=title,
            text=text,
            metadata=metadata,
            reference_candidates=list(metadata.get("reference_candidates") or []),
        )

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
            reference_candidates=list(parsed.reference_candidates or []),
        )

    def fingerprint(self, normalized: NormalizedSource) -> str:
        return make_fingerprint(normalized)

    def ingest(self, url: str) -> NormalizedSource:
        from app.connectors.arxiv import ArxivPaperConnector, is_arxiv_url

        if is_arxiv_url(url):
            return ArxivPaperConnector().ingest(url)
        raw = self.fetch(DiscoveredItem(ref=url, metadata={}))
        return self.normalize(self.parse(raw))
