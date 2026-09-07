"""Raw-source loader for Semantic Evidence Extraction development.

Loads the pinned development corpus without silently truncating source content.
Text/Markdown sources are paragraph-numbered; PDFs are page-numbered using
pypdf text extraction. This is a sensor-input plumbing layer, not semantic
reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "eval" / "live" / "manifest.semantic_evidence_dev_corpus.v0.1.yaml"


@dataclass(frozen=True)
class LoadedSemanticSource:
    source_id: str
    path: str
    media_type: str
    git_blob_sha: str
    file_sha256: str
    text_sha256: str
    char_count: int
    page_count: int | None
    rendered_text: str


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha(path: Path) -> str:
    proc = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def load_dev_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("semantic evidence corpus manifest must be a mapping")
    if raw.get("status") != "DEVELOPMENT_ONLY_NOT_FRESH_VALIDATION":
        raise ValueError("semantic evidence corpus is not marked development-only")
    sources = raw.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("semantic evidence corpus manifest requires sources")
    ids = [str(item.get("id", "")) for item in sources]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("source ids must be unique and non-empty")
    return raw


def _render_text_paragraphs(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    parts = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    return "\n\n".join(f"[PARA {idx:04d}]\n{part}" for idx, part in enumerate(parts, start=1))


def _render_pdf_pages(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    rendered: list[str] = []
    for idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        rendered.append(f"[PAGE {idx:04d}]\n{text}")
    return "\n\n".join(rendered).strip(), len(reader.pages)


def load_manifest_source(entry: dict[str, Any]) -> LoadedSemanticSource:
    source_id = str(entry.get("id", "")).strip()
    rel_path = str(entry.get("path", "")).strip()
    media_type = str(entry.get("media_type", "")).strip()
    expected_blob = str(entry.get("git_blob_sha", "")).strip()
    if not source_id or not rel_path or not media_type or not expected_blob:
        raise ValueError("source entry missing id/path/media_type/git_blob_sha")

    path = ROOT / rel_path
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)

    actual_blob = _git_blob_sha(path)
    if actual_blob != expected_blob:
        raise ValueError(
            f"git blob mismatch for {source_id}: expected {expected_blob}, got {actual_blob}"
        )

    raw_bytes = path.read_bytes()
    suffix = path.suffix.lower()
    page_count: int | None = None
    if suffix == ".pdf":
        rendered_text, page_count = _render_pdf_pages(path)
    elif suffix in {".txt", ".md", ".markdown"}:
        rendered_text = _render_text_paragraphs(raw_bytes.decode("utf-8-sig"))
    else:
        raise ValueError(f"unsupported semantic source type: {suffix}")

    if not rendered_text.strip():
        raise ValueError(f"no extractable text for {source_id}")

    return LoadedSemanticSource(
        source_id=source_id,
        path=rel_path,
        media_type=media_type,
        git_blob_sha=actual_blob,
        file_sha256=_sha256_bytes(raw_bytes),
        text_sha256=_sha256_bytes(rendered_text.encode("utf-8")),
        char_count=len(rendered_text),
        page_count=page_count,
        rendered_text=rendered_text,
    )


def load_development_corpus(path: Path | None = None) -> list[LoadedSemanticSource]:
    manifest = load_dev_manifest(path)
    return [load_manifest_source(entry) for entry in manifest["sources"]]


def corpus_inventory(path: Path | None = None) -> list[dict[str, Any]]:
    """Load/verify every development source and return metadata only."""

    inventory: list[dict[str, Any]] = []
    for source in load_development_corpus(path):
        inventory.append(
            {
                "source_id": source.source_id,
                "path": source.path,
                "media_type": source.media_type,
                "git_blob_sha": source.git_blob_sha,
                "file_sha256": source.file_sha256,
                "text_sha256": source.text_sha256,
                "char_count": source.char_count,
                "page_count": source.page_count,
            }
        )
    return inventory
