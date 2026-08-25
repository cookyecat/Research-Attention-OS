from __future__ import annotations

import re

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
ARXIV_RE = re.compile(r"(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)
URL_RE = re.compile(r"https?://[^\s]+", re.I)


def extract_reference_candidates(text: str) -> list[dict]:
    if not text:
        return []
    lowered = text.lower()
    idx = None
    for marker in ("\nreferences\n", "\nreferences\f", "\nbibliography\n"):
        found = lowered.rfind(marker)
        if found != -1:
            idx = found + 1
            break
    if idx is None:
        return []
    section = text[idx:]
    section = re.sub(r"^(references|bibliography)\s*", "", section, flags=re.I)
    chunks = re.split(r"(?:^|\n)\s*(?:\[\d+\]|\(\d+\)|\d+\.)\s+", section)
    if len(chunks) < 5:
        chunks = re.split(r"\s*\[\d+\]\s+", section)
    candidates = []
    for raw in chunks:
        raw_text = re.sub(r"\s+", " ", raw).strip(" .;")
        if len(raw_text) < 20:
            continue
        doi_match = DOI_RE.search(raw_text)
        arxiv_match = ARXIV_RE.search(raw_text)
        url_match = URL_RE.search(raw_text)
        year_match = re.search(r"\b(19|20)\d{2}\b", raw_text)
        title = raw_text
        if "." in raw_text:
            parts = [p.strip() for p in raw_text.split(".") if p.strip()]
            if len(parts) >= 2:
                title = parts[1][:300]
        confidence = 0.4
        if doi_match or arxiv_match:
            confidence = 0.9
        elif year_match:
            confidence = 0.6
        candidates.append(
            {
                "raw_text": raw_text[:2000],
                "title": title[:500],
                "authors": None,
                "year": int(year_match.group(0)) if year_match else None,
                "venue": None,
                "doi": doi_match.group(0).rstrip(".") if doi_match else None,
                "arxiv_id": arxiv_match.group(1) if arxiv_match else None,
                "url": url_match.group(0).rstrip(".,)") if url_match else None,
                "confidence": confidence,
            }
        )
    return candidates[:200]
