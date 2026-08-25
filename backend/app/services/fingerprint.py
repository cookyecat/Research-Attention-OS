from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def content_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(normalize_ws(text).lower().encode("utf-8")).hexdigest()


def _clean_id(value: str) -> str:
    return normalize_ws(value).lower()


@dataclass
class NormalizedSource:
    source_type: str
    title: str | None = None
    canonical_url: str | None = None
    content_text: str | None = None
    published_at: datetime | None = None
    author_entities: list[str] = field(default_factory=list)
    publisher: str | None = None
    language: str | None = None
    external_ids: dict[str, str] = field(default_factory=dict)
    raw_metadata: dict = field(default_factory=dict)
    binary_object_ref: str | None = None
    ingestion_method: str = "MANUAL_TEXT"
    reference_candidates: list[dict] = field(default_factory=list)


def fingerprint(normalized: NormalizedSource, version: str = "fp-v1") -> str:
    doi = normalized.external_ids.get("doi")
    arxiv_id = normalized.external_ids.get("arxiv_id")
    if doi:
        key = f"doi:{_clean_id(doi)}"
    elif arxiv_id:
        key = f"arxiv:{_clean_id(arxiv_id)}"
    elif normalized.canonical_url:
        key = f"url:{_clean_id(normalized.canonical_url.rstrip('/'))}"
    elif normalized.title and normalized.publisher and normalized.published_at:
        published = normalized.published_at.date().isoformat()
        key = (
            "tpp:"
            f"{_clean_id(normalized.title)}|{_clean_id(normalized.publisher)}|{published}"
        )
    else:
        hashed = content_hash(normalized.content_text) or content_hash(normalized.title) or "empty"
        key = f"hash:{hashed}"
    return f"{version}:{key}"
