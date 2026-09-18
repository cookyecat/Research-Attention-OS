from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.connectors.url import (
    _blocks_to_text,
    _cache_presentation_media,
    _extract_article_blocks,
    _extract_article_images,
    _extract_explicit_references,
    _extract_media_assets,
    validate_public_url,
)
from app.services.fingerprint import NormalizedSource

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153 Safari/537.36"
)

def wechat_url_identity(url: str) -> tuple[str | None, str | None, str | None]:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != "mp.weixin.qq.com":
        return None, None, None
    query = parse_qs(parsed.query)
    return (
        (query.get("__biz") or [None])[-1],
        (query.get("mid") or [None])[-1],
        (query.get("idx") or [None])[-1],
    )


def is_wechat_challenge(final_url: str, html: str) -> bool:
    parsed = urlparse(final_url)
    if "/mp/wappoc_appmsgcaptcha" in parsed.path:
        return True
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    return "环境异常" in text and "验证" in text


def _font_px(value: str) -> float | None:
    match = re.search(r"font-size\s*:\s*([0-9.]+)px", value, flags=re.I)
    return float(match.group(1)) if match else None


def _wechat_text(tag) -> str:
    """Preserve literal whitespace without inventing spaces at inline span boundaries."""
    raw = tag.get_text("", strip=False)
    return re.sub(r"\s+", " ", raw).strip()

def _promote_styled_headings(root) -> None:
    """Promote conservative WeChat visual section headings to semantic H2.

    Some publishers, especially 机器之心, encode section headings as centered
    bold paragraphs rather than H tags. Restrict inference to short, centered,
    visibly enlarged text so ordinary inline emphasis never becomes a heading.
    """
    for tag in list(root.find_all("p")):
        text = _wechat_text(tag)
        if not (8 <= len(text) <= 60):
            continue
        style = str(tag.get("style") or "")
        descendant_style = " ".join(
            str(node.get("style") or "") for node in tag.find_all(["span", "strong", "b"], limit=8)
        )
        combined = f"{style} {descendant_style}".lower()
        centered = "text-align: center" in combined or "text-align:center" in combined
        bold = bool(re.search(r"font-weight\s*:\s*(?:bold|[6-9]00)", combined))
        sizes = [size for size in (_font_px(style), _font_px(descendant_style)) if size is not None]
        enlarged = bool(sizes and max(sizes) >= 16)
        if not (centered and bold and enlarged):
            continue
        if text.startswith(("编辑", "作者", "来源", "原创", "关注")):
            continue
        tag.name = "h2"


def _restore_mirror_image_sources(root) -> dict[str, str]:
    """Restore Wechat2RSS image proxies to their original WeChat CDN URLs."""
    transport_by_original: dict[str, str] = {}
    for image in root.find_all("img"):
        value = str(image.get("src") or "").strip()
        if not value:
            continue
        parsed = urlparse(value)
        if "wechat2rss" not in (parsed.hostname or "") or "img-proxy" not in parsed.path:
            continue
        original = (parse_qs(parsed.query).get("u") or [None])[-1]
        if not original:
            continue
        transport_by_original[original] = value
        image["src"] = original
        image["data-raos-transport-url"] = value
    return transport_by_original


def _annotate_mirror_images(metadata: dict, transport_by_original: dict[str, str]) -> None:
    def annotate(node: dict) -> None:
        url = str(node.get("url") or "")
        transport_url = transport_by_original.get(url)
        if not transport_url:
            return
        node["original_url"] = url
        node["transport_url"] = transport_url
        node["transport"] = "wechat2rss-image-proxy"

    for image in metadata.get("article_images") or []:
        annotate(image)
    for block in metadata.get("article_blocks") or []:
        if block.get("type") == "image":
            annotate(block)
    for asset in metadata.get("media_assets") or []:
        if str(asset.get("type") or "").upper() == "IMAGE":
            annotate(asset)


def _build_metadata(
    html: str,
    canonical_url: str,
    *,
    account: str,
    biz: str,
    fetch_mode: str,
    feed_url: str | None,
    direct_status: int | None,
) -> tuple[str, dict]:

    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one("#js_content, .rich_media_content")
    if root is None:
        root = soup.body or soup
    transport_by_original = _restore_mirror_image_sources(root)
    heading_decorative_images = list(root.select("h1 img, h2 img, h3 img, h4 img"))
    for image in heading_decorative_images:
        image.decompose()
    _promote_styled_headings(root)

    direct_title = soup.select_one("#activity-name")
    direct_account = soup.select_one("#js_name")
    reference_candidates = _extract_explicit_references(root, canonical_url, limit=120)
    article_images = _extract_article_images(root, canonical_url, None, account, limit=48)
    article_blocks = _extract_article_blocks(root, canonical_url, article_images, text_getter=_wechat_text)
    text = _blocks_to_text(article_blocks)
    if not text:
        text = "\n".join(
            " ".join(node.get_text(" ", strip=True).split())
            for node in root.find_all(["p", "h2", "h3", "h4"])
            if node.get_text(" ", strip=True)
        )

    metadata = {
        "origin_url": canonical_url,
        "canonical_url": canonical_url,
        "publisher": account,
        "author": account,
        "wechat_account": account,
        "wechat_biz": biz,
        "wechat_fetch_mode": fetch_mode,
        "wechat_direct_status": direct_status,
        "wechat_feed_url": feed_url,
        "wechat_heading_decorative_images_dropped": len(heading_decorative_images),
        "article_images": article_images,
        "article_blocks": article_blocks,
        "article_structure_version": "structured-blocks-v3-tables",
        "media_assets": _extract_media_assets(root, canonical_url, article_images, limit=64),
        "reference_candidates": reference_candidates,
        "parser": "wechat-article-v1",
    }

    if direct_title is not None:
        metadata["wechat_direct_title"] = " ".join(direct_title.get_text(" ", strip=True).split())
    if direct_account is not None:
        metadata["wechat_direct_account"] = " ".join(direct_account.get_text(" ", strip=True).split())
    if fetch_mode != "direct":
        metadata["wechat_mirror_role"] = "transport-fallback"
        metadata["wechat_mirror_is_independent_evidence"] = False
        _annotate_mirror_images(metadata, transport_by_original)

    _cache_presentation_media(metadata)
    return text, metadata


class WechatArticleConnector:
    def ingest(
        self,
        url: str,
        *,
        title: str | None,
        account: str,
        biz: str,
        published_at: datetime | None,
        fallback_html: str | None,
        feed_url: str | None,
    ) -> NormalizedSource:
        validate_public_url(url)
        actual_biz, mid, idx = wechat_url_identity(url)
        if actual_biz != biz or not mid or not idx:
            raise ValueError("WeChat article identity does not match configured account")

        direct_html = None
        direct_status = None
        final_url = url
        try:
            with httpx.Client(follow_redirects=True, timeout=max(20.0, settings.url_fetch_timeout_seconds)) as client:
                response = client.get(
                    url,
                    headers={
                        "User-Agent": _BROWSER_UA,
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
                        "Referer": "https://mp.weixin.qq.com/",
                    },
                )
                direct_status = response.status_code
                final_url = str(response.url)
                if response.status_code == 200 and not is_wechat_challenge(final_url, response.text):
                    direct_soup = BeautifulSoup(response.text, "lxml")
                    if direct_soup.select_one("#js_content, .rich_media_content") is not None:
                        direct_html = response.text
        except httpx.HTTPError:
            pass

        if direct_html is not None:
            html = direct_html
            fetch_mode = "direct"
        elif fallback_html:
            html = fallback_html
            fetch_mode = "wechat2rss-fallback-v1"
        else:
            raise RuntimeError("WeChat publisher page is blocked and no full-body feed snapshot is available")

        text, metadata = _build_metadata(
            html,
            url,
            account=account,
            biz=biz,
            fetch_mode=fetch_mode,
            feed_url=feed_url,
            direct_status=direct_status,
        )
        if len(text.strip()) < 120:
            raise RuntimeError("WeChat article extraction produced implausibly little content")

        metadata.update({
            "requested_url": url,
            "final_url": final_url,
            "wechat_mid": mid,
            "wechat_idx": idx,
            "wechat_direct_blocked": direct_html is None,
        })
        return NormalizedSource(
            source_type="URL",
            title=metadata.get("wechat_direct_title") or title,
            canonical_url=url,
            content_text=text,
            published_at=published_at,
            author_entities=[account],
            publisher=account,
            language="zh-CN",
            external_ids={"wechat_biz": biz, "wechat_mid": mid, "wechat_idx": idx},
            raw_metadata=metadata,
            ingestion_method="WECHAT_FETCH",
            reference_candidates=list(metadata.get("reference_candidates") or []),
        )
