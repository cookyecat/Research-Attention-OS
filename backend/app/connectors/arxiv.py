from __future__ import annotations

import re
from copy import copy
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.services.fingerprint import NormalizedSource
from app.services.media_cache import cache_remote_media

_ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org"}
_ARXIV_PATH = re.compile(r"^/(?:abs|html|pdf)/(?P<id>\d{4}\.\d{4,5})(?P<version>v\d+)?(?:\.pdf)?/?$")
_BLOCKED_TAGS = {"script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "canvas", "svg"}


def parse_arxiv_ref(url: str) -> tuple[str, str | None] | None:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() not in _ARXIV_HOSTS:
        return None
    match = _ARXIV_PATH.match(parsed.path)
    if not match:
        return None
    return match.group("id"), match.group("version")


def is_arxiv_url(url: str) -> bool:
    return parse_arxiv_ref(url) is not None


def _meta_all(soup: BeautifulSoup, name: str) -> list[str]:
    out: list[str] = []
    for node in soup.find_all("meta", attrs={"name": name}):
        value = str(node.get("content") or "").strip()
        if value:
            out.append(value)
    return out


def _meta_one(soup: BeautifulSoup, name: str) -> str | None:
    values = _meta_all(soup, name)
    return values[0] if values else None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _clean_affiliation(text: str) -> str:
    text = re.sub(r"^Affiliation:\s*", "", text.strip(), flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _paper_text(html_soup: BeautifulSoup, abstract: str | None) -> str:
    parts: list[str] = []
    if abstract:
        parts.extend(["Abstract", abstract])
    article = html_soup.select_one("article.ltx_document")
    if article is None:
        return "\n\n".join(parts)
    for section in article.find_all("section", class_="ltx_section", recursive=False):
        text = section.get_text(" ", strip=True)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _safe_href(value: str, base_url: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value.startswith("#"):
        return value
    resolved = urljoin(base_url, value)
    scheme = urlparse(resolved).scheme.lower()
    return resolved if scheme in {"http", "https"} else None


def _sanitize_fragment(fragment, *, base_url: str, figures: list[dict]) -> str:
    soup = BeautifulSoup(str(fragment), "lxml")
    root = soup.body or soup
    for tag in list(root.find_all(_BLOCKED_TAGS)):
        tag.decompose()
    for tag in root.find_all(True):
        attrs = dict(tag.attrs)
        for key in list(attrs):
            if key.lower().startswith("on") or key.lower() == "style":
                tag.attrs.pop(key, None)
        allowed = {"id", "class"}
        if tag.name == "a":
            allowed |= {"href", "title"}
            href = tag.get("href")
            if href:
                safe = _safe_href(str(href), base_url)
                if safe is None:
                    tag.attrs.pop("href", None)
                else:
                    tag["href"] = safe
                    if not safe.startswith("#"):
                        tag["target"] = "_blank"
                        tag["rel"] = "noreferrer"
                        allowed |= {"target", "rel"}
        elif tag.name == "img":
            allowed |= {"src", "alt", "width", "height"}
            src = str(tag.get("src") or "").strip()
            if src:
                original = urljoin(base_url, src)
                cached = cache_remote_media(original)
                tag["src"] = cached or original
                caption_tag = tag.find_parent("figure")
                caption_node = caption_tag.find("figcaption") if caption_tag else None
                caption = caption_node.get_text(" ", strip=True) if caption_node else None
                figures.append({
                    "url": original,
                    "cached_url": cached,
                    "alt": str(tag.get("alt") or "").strip() or None,
                    "caption": caption,
                })
        elif tag.name in {"td", "th"}:
            allowed |= {"colspan", "rowspan"}
        elif tag.name in {"math", "annotation"}:
            allowed |= {"display", "alttext", "intent", "encoding"}
        tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed}
    return "".join(str(child) for child in root.contents)


def _paper_body_html(html_soup: BeautifulSoup, *, base_url: str) -> tuple[str, list[dict], list[dict]]:
    article = html_soup.select_one("article.ltx_document")
    if article is None:
        return "", [], []
    figures: list[dict] = []
    sections: list[dict] = []
    chunks: list[str] = []
    for section in article.find_all("section", class_="ltx_section", recursive=False):
        heading = section.find(["h2", "h3"], recursive=False)
        title = heading.get_text(" ", strip=True) if heading else "Section"
        section_id = str(section.get("id") or "").strip() or f"section-{len(sections)+1}"
        sanitized = _sanitize_fragment(copy(section), base_url=base_url, figures=figures)
        chunks.append(sanitized)
        sections.append({"id": section_id, "title": title})
    bibliography = article.find(class_="ltx_bibliography", recursive=False) or html_soup.select_one(".ltx_bibliography")
    if bibliography is not None:
        chunks.append(_sanitize_fragment(copy(bibliography), base_url=base_url, figures=figures))
    dedup: list[dict] = []
    seen: set[str] = set()
    for figure in figures:
        key = figure.get("url") or figure.get("cached_url")
        if not key or key in seen:
            continue
        dedup.append(figure)
        seen.add(key)
    return "\n".join(chunks), sections, dedup


def _abs_metadata(abs_soup: BeautifulSoup, arxiv_id: str) -> dict:
    title = _meta_one(abs_soup, "citation_title")
    authors = _meta_all(abs_soup, "citation_author")
    abstract = _meta_one(abs_soup, "citation_abstract")
    published = _parse_date(_meta_one(abs_soup, "citation_date"))
    pdf_url = _meta_one(abs_soup, "citation_pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}"
    og_url_node = abs_soup.find("meta", attrs={"property": "og:url"})
    og_url = str(og_url_node.get("content") or "").strip() if og_url_node else ""
    version_match = re.search(r"(v\d+)$", og_url)
    version = version_match.group(1) if version_match else None
    primary = abs_soup.select_one(".primary-subject")
    primary_category = primary.get_text(" ", strip=True) if primary else None
    subjects_node = abs_soup.select_one(".subjects")
    subjects_text = subjects_node.get_text(" ", strip=True) if subjects_node else None
    submission = abs_soup.select_one(".submission-history")
    submission_history = submission.get_text(" ", strip=True) if submission else None
    comments = abs_soup.select_one("td.comments")
    journal_ref = abs_soup.select_one("td.journal-ref")
    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published_at": published,
        "pdf_url": pdf_url,
        "version": version,
        "primary_category": primary_category,
        "subjects": subjects_text,
        "submission_history": submission_history,
        "comments": comments.get_text(" ", strip=True) if comments else None,
        "journal_ref": journal_ref.get_text(" ", strip=True) if journal_ref else None,
    }


class ArxivPaperConnector:
    def ingest(self, url: str) -> NormalizedSource:
        parsed = parse_arxiv_ref(url)
        if parsed is None:
            raise ValueError("Not an arXiv paper URL")
        arxiv_id, requested_version = parsed
        abs_url = f"https://arxiv.org/abs/{arxiv_id}{requested_version or ''}"
        headers = {"User-Agent": "RAOS/1.1 PaperReader"}
        with httpx.Client(follow_redirects=True, timeout=settings.url_fetch_timeout_seconds) as client:
            abs_response = client.get(abs_url, headers=headers)
            abs_response.raise_for_status()
            abs_soup = BeautifulSoup(abs_response.content, "lxml")
            meta = _abs_metadata(abs_soup, arxiv_id)
            version = requested_version or meta.get("version")
            html_url = f"https://arxiv.org/html/{arxiv_id}{version or ''}"
            html_response = client.get(html_url, headers=headers)
            html_available = html_response.status_code == 200
            html_soup = BeautifulSoup(html_response.content, "lxml") if html_available else None

        affiliations: list[str] = []
        body_html = ""
        sections: list[dict] = []
        figures: list[dict] = []
        content_text = meta.get("abstract") or ""
        if html_soup is not None:
            for node in html_soup.select(".ltx_role_affiliation"):
                value = _clean_affiliation(node.get_text(" ", strip=True))
                if value and value not in affiliations:
                    affiliations.append(value)
            body_html, sections, figures = _paper_body_html(html_soup, base_url=html_url)
            content_text = _paper_text(html_soup, meta.get("abstract"))

        paper_meta = {
            "paper_profile": "ARXIV_HTML" if html_available else "ARXIV_ABS",
            "paper_title": meta.get("title") or f"arXiv:{arxiv_id}",
            "arxiv_id": arxiv_id,
            "arxiv_version": version,
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}{version or ''}",
            "html_url": html_url if html_available else None,
            "pdf_url": meta.get("pdf_url"),
            "abstract": meta.get("abstract"),
            "authors": meta.get("authors") or [],
            "affiliations": affiliations,
            "primary_category": meta.get("primary_category"),
            "subjects": meta.get("subjects"),
            "submission_history": meta.get("submission_history"),
            "comments": meta.get("comments"),
            "journal_ref": meta.get("journal_ref"),
            "paper_sections": sections,
            "paper_figures": figures,
            "paper_lead_figure_url": (figures[0].get("cached_url") or figures[0].get("url")) if figures else None,
            "paper_body_html": body_html,
            "paper_word_count": len((content_text or "").split()),
            "origin_url": url,
            "canonical_url": f"https://arxiv.org/abs/{arxiv_id}",
            "author": (meta.get("authors") or [None])[0],
            "published": meta.get("published_at").isoformat() if meta.get("published_at") else None,
            "hero_image_url": None,
            "hero_image_alt": None,
            "article_images": [],
            "media_assets": [],
            "parser": "arxiv-html-v1",
        }
        return NormalizedSource(
            source_type="PAPER",
            title=meta.get("title") or f"arXiv:{arxiv_id}",
            canonical_url=f"https://arxiv.org/abs/{arxiv_id}",
            content_text=content_text,
            published_at=meta.get("published_at"),
            author_entities=list(meta.get("authors") or []),
            publisher="arXiv",
            external_ids={"arxiv_id": arxiv_id},
            raw_metadata=paper_meta,
            ingestion_method="ARXIV_HTML" if html_available else "ARXIV_ABS",
        )
