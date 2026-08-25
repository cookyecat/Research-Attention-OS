from __future__ import annotations

import io
import re
from pathlib import Path

from pypdf import PdfReader

from app.connectors.base import DiscoveredItem, ParsedSource, RawSource
from app.services.fingerprint import NormalizedSource, fingerprint as make_fingerprint
from app.services.references import extract_reference_candidates

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"\barxiv:(\d{4}\.\d{4,5}(?:v\d+)?)\b", re.I)


def _looks_like_paper(text: str, metadata: dict) -> bool:
    if metadata.get("doi") or metadata.get("arxiv_id"):
        return True
    head = text[:4000].lower()
    return "abstract" in head and ("references" in text.lower() or "bibliography" in text.lower())


class PDFConnector:
    def discover(self, query_or_config) -> list[DiscoveredItem]:
        return []

    def fetch(self, item: DiscoveredItem) -> RawSource:
        path = Path(item.ref)
        return RawSource(payload=path.read_bytes(), content_type="application/pdf", origin=str(path), metadata={})

    def parse(self, raw: RawSource) -> ParsedSource:
        data = raw.payload if isinstance(raw.payload, bytes) else raw.payload.encode("utf-8")
        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n\f\n".join(pages)
        info = reader.metadata or {}
        title = None
        if info and info.title:
            title = str(info.title)
        authors = []
        if info and info.author:
            authors = [str(info.author)]
        doi = None
        arxiv_id = None
        doi_match = DOI_RE.search(text)
        if doi_match:
            doi = doi_match.group(0).rstrip(".")
        arxiv_match = ARXIV_RE.search(text)
        if arxiv_match:
            arxiv_id = arxiv_match.group(1)
        refs = extract_reference_candidates(text)
        metadata = {
            "page_count": len(pages),
            "authors": authors,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "parser": "pdf-v1",
            **(raw.metadata or {}),
        }
        if not title:
            first_line = next((line.strip() for line in text.splitlines() if line.strip()), None)
            title = first_line[:200] if first_line else None
        return ParsedSource(title=title, text=text, metadata=metadata, reference_candidates=refs)

    def normalize(self, parsed: ParsedSource) -> NormalizedSource:
        source_type = "PAPER" if _looks_like_paper(parsed.text or "", parsed.metadata) else "PDF"
        external = {}
        if parsed.metadata.get("doi"):
            external["doi"] = parsed.metadata["doi"]
        if parsed.metadata.get("arxiv_id"):
            external["arxiv_id"] = parsed.metadata["arxiv_id"]
        return NormalizedSource(
            source_type=source_type,
            title=parsed.title,
            content_text=parsed.text,
            author_entities=list(parsed.metadata.get("authors") or []),
            external_ids=external,
            raw_metadata=parsed.metadata,
            ingestion_method="PDF_UPLOAD",
            reference_candidates=parsed.reference_candidates,
        )

    def fingerprint(self, normalized: NormalizedSource) -> str:
        return make_fingerprint(normalized)

    def ingest(self, data: bytes, filename: str | None = None) -> NormalizedSource:
        raw = RawSource(
            payload=data,
            content_type="application/pdf",
            origin=filename or "upload.pdf",
            metadata={"filename": filename},
        )
        return self.normalize(self.parse(raw))
