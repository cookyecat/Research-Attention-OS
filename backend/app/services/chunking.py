from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings

HEADING_RE = re.compile(r"(?m)^(#{1,6}\s+\S.*)$")


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    text: str
    start: int
    end: int


def split_source(
    text: str,
    *,
    max_chars: int | None = None,
    overlap: int | None = None,
) -> list[SourceChunk]:
    """Heading-aware split with character fallback and small overlap.

    Not RAG. Provenance only: later Claim/Observation rows keep chunk_id + span.
    """
    text = text or ""
    max_chars = max_chars if max_chars is not None else settings.long_source_chunk_chars
    overlap = overlap if overlap is not None else settings.long_source_chunk_overlap
    if len(text) <= max_chars:
        return [SourceChunk(chunk_id="c0", text=text, start=0, end=len(text))]

    sections = _heading_sections(text)
    if len(sections) <= 1:
        sections = _paragraph_sections(text)

    packed: list[tuple[int, str]] = []
    buf = ""
    buf_start = sections[0][0] if sections else 0
    for start, sec in sections:
        if buf and len(buf) + len(sec) > max_chars:
            packed.append((buf_start, buf))
            ov = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = ov + sec
            buf_start = start - len(ov)
            if buf_start < 0:
                buf_start = start
        else:
            if not buf:
                buf_start = start
            buf += sec
    if buf:
        packed.append((buf_start, buf))

    chunks: list[SourceChunk] = []
    idx = 0
    for start, body in packed:
        if len(body) <= max_chars:
            chunks.append(SourceChunk(chunk_id=f"c{idx}", text=body, start=start, end=start + len(body)))
            idx += 1
            continue
        pos = 0
        while pos < len(body):
            endp = min(pos + max_chars, len(body))
            piece = body[pos:endp]
            abs_start = start + pos
            chunks.append(SourceChunk(chunk_id=f"c{idx}", text=piece, start=abs_start, end=abs_start + len(piece)))
            idx += 1
            if endp >= len(body):
                break
            pos = max(endp - overlap, pos + 1)
    return chunks or [SourceChunk(chunk_id="c0", text=text, start=0, end=len(text))]


def locate_span(full: str, snippet: str, hint: int | None = None) -> tuple[int | None, int | None]:
    if not snippet or not full:
        return None, None
    needle = snippet.strip()
    if not needle:
        return None, None
    if hint is not None:
        window_start = max(0, hint - 80)
        window = full[window_start : hint + len(needle) + 240]
        rel = window.find(needle[: min(120, len(needle))])
        if rel >= 0:
            start = window_start + rel
            end = min(len(full), start + len(needle))
            return start, end
    idx = full.find(needle)
    if idx >= 0:
        return idx, idx + len(needle)
    short = needle[: min(40, len(needle))]
    idx = full.find(short)
    if idx >= 0:
        return idx, idx + len(short)
    return None, None


def _heading_sections(text: str) -> list[tuple[int, str]]:
    bounds = [0]
    for match in HEADING_RE.finditer(text):
        if match.start() > 0:
            bounds.append(match.start())
    bounds.append(len(text))
    uniq = sorted(set(bounds))
    return [(uniq[i], text[uniq[i] : uniq[i + 1]]) for i in range(len(uniq) - 1)]


def _paragraph_sections(text: str) -> list[tuple[int, str]]:
    parts = re.split(r"(\n{2,})", text)
    sections: list[tuple[int, str]] = []
    pos = 0
    buf = ""
    buf_start = 0
    for part in parts:
        if not buf:
            buf_start = pos
        buf += part
        pos += len(part)
        if part.strip() == "" and "\n" in part and buf.strip():
            sections.append((buf_start, buf))
            buf = ""
    if buf:
        sections.append((buf_start, buf))
    return sections or [(0, text)]
