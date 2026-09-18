import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "backfill-structured-articles.py"
spec = importlib.util.spec_from_file_location("structured_backfill", SCRIPT)
assert spec and spec.loader
backfill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill)


def _db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE sources (
          id TEXT PRIMARY KEY,
          canonical_url TEXT,
          content_text TEXT,
          raw_metadata TEXT,
          ingestion_method TEXT,
          ingested_at TEXT
        )
    """)
    return conn


def test_backfill_eligibility_targets_only_pre_v3_sources():
    conn = _db()
    rows = [
        ("missing", "https://example.com/a", "A", "{}"),
        ("v2", "https://example.com/b", "B", json.dumps({"article_structure_version": "structured-blocks-v2-clean"})),
        ("v3", "https://example.com/c", "C", json.dumps({"article_structure_version": backfill.CURRENT_STRUCTURE_VERSION})),
    ]
    conn.executemany(
        "INSERT INTO sources(id, canonical_url, content_text, raw_metadata, ingestion_method, ingested_at) VALUES (?, ?, ?, ?, 'URL_FETCH', '2026-09-17')",
        rows,
    )
    eligible = backfill.eligible_rows(conn, 0)
    assert [row["id"] for row in eligible] == ["missing", "v2"]


def test_merge_presentation_preserves_nonpresentation_metadata():
    old = {"acquisition": {"external_item_id": "x"}, "custom": 7, "parser": "old"}
    fresh = {"parser": "new", "article_structure_version": backfill.CURRENT_STRUCTURE_VERSION, "article_blocks": [{"type": "table"}]}
    merged = backfill.merge_presentation(old, fresh)
    assert merged["acquisition"] == {"external_item_id": "x"}
    assert merged["custom"] == 7
    assert merged["parser"] == "old"
    assert merged["presentation_hydration"]["version"] == backfill.BACKFILL_VERSION
    assert merged["presentation_hydration"]["presentation_parser"] == "new"
    assert merged["presentation_hydration"]["article_structure_version"] == backfill.CURRENT_STRUCTURE_VERSION


def test_cache_reader_images_keeps_video_and_poster_local(monkeypatch):
    monkeypatch.setattr(backfill, "cache_remote_media", lambda url: f"/cached/{url.rsplit('/', 1)[-1]}")
    metadata = {
        "article_images": [{"url": "https://cdn.example/a.jpg"}],
        "article_blocks": [{"type": "image", "url": "https://cdn.example/a.jpg"}],
        "media_assets": [
            {"type": "IMAGE", "url": "https://cdn.example/a.jpg"},
            {"type": "VIDEO", "url": "https://cdn.example/v.mp4", "poster_url": "https://cdn.example/p.jpg"},
            {"type": "EMBED", "embed_url": "https://www.youtube.com/embed/x"},
        ],
    }
    backfill.cache_reader_images(metadata)
    assert metadata["article_blocks"][0]["cached_url"] == "/cached/a.jpg"
    assert metadata["media_assets"][0]["cached_url"] == "/cached/a.jpg"
    assert metadata["media_assets"][1]["cached_url"] == "/cached/v.mp4"
    assert metadata["media_assets"][1]["poster_cached_url"] == "/cached/p.jpg"
    assert "cached_url" not in metadata["media_assets"][2]
