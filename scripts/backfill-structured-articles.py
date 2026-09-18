#!/usr/bin/env python3
"""Safely hydrate legacy URL sources with structured presentation metadata."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.connectors.url import _extract_readable, validate_public_url
from app.services.media_cache import cache_remote_media

CURRENT_STRUCTURE_VERSION = "structured-blocks-v3-tables"
BACKFILL_VERSION = "structured-article-backfill-v3-tables"

PRESENTATION_KEYS = {
    "hero_image_url", "hero_image_alt", "hero_image_cached_url",
    "article_images", "article_blocks", "article_structure_version",
    "media_assets",
}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(BACKEND / "raos.db"))
    parser.add_argument("--limit", type=int, default=0, help="0 means all eligible rows")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--apply", action="store_true", help="persist metadata updates")
    return parser.parse_args()


def eligible_rows(conn: sqlite3.Connection, limit: int) -> list[dict]:
    sql = """
    SELECT id, canonical_url, content_text, raw_metadata
    FROM sources
    WHERE ingestion_method = 'URL_FETCH'
      AND canonical_url IS NOT NULL
      AND COALESCE(json_extract(raw_metadata, '$.article_structure_version'), '') != ?
    ORDER BY ingested_at ASC
    """
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    return [dict(row) for row in conn.execute(sql, (CURRENT_STRUCTURE_VERSION,))]

def fetch_metadata(url: str, timeout: float) -> tuple[str, dict]:
    safe_url = validate_public_url(url)
    headers = {"User-Agent": "RAOS/1.1 (+structured-presentation-backfill)"}
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = client.get(safe_url)
        response.raise_for_status()
    _title, text, metadata = _extract_readable(response.text, str(response.url))
    return text or "", metadata


def cache_reader_images(metadata: dict) -> None:
    hero = metadata.get("hero_image_url")
    if hero:
        metadata["hero_image_cached_url"] = cache_remote_media(hero)
    cached: dict[str, str | None] = {}
    for image in metadata.get("article_images") or []:
        url = image.get("url")
        if not url:
            continue
        image["cached_url"] = cache_remote_media(url)
        cached[str(url)] = image.get("cached_url")
    for block in metadata.get("article_blocks") or []:
        if block.get("type") == "image" and block.get("url"):
            block["cached_url"] = cached.get(str(block["url"])) or cache_remote_media(block["url"])
    for asset in metadata.get("media_assets") or []:
        if asset.get("type") in {"IMAGE", "VIDEO"} and asset.get("url"):
            asset["cached_url"] = cached.get(str(asset["url"])) or cache_remote_media(asset["url"])
        if asset.get("poster_url"):
            asset["poster_cached_url"] = cache_remote_media(asset["poster_url"])


def merge_presentation(old: dict, fresh: dict) -> dict:
    merged = dict(old or {})
    for key in PRESENTATION_KEYS:
        if key in fresh:
            merged[key] = fresh[key]
    merged["presentation_hydration"] = {
        "version": BACKFILL_VERSION,
        "content_text_unchanged": True,
        "presentation_parser": fresh.get("parser"),
        "article_structure_version": fresh.get("article_structure_version"),
    }
    return merged


def fetch_one(row: dict, timeout: float) -> tuple[dict, str | None, dict | None, Exception | None]:
    try:
        fresh_text, fresh_meta = fetch_metadata(row["canonical_url"], timeout)
        return row, fresh_text, fresh_meta, None
    except Exception as exc:
        return row, None, None, exc

def main() -> int:
    args = parse_args()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = eligible_rows(conn, args.limit)
    counts = {"eligible": len(rows), "hydrated": 0, "changed": 0, "failed": 0}
    workers = max(1, min(12, int(args.workers)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch_one, row, args.timeout) for row in rows]
        for future in as_completed(futures):
            row, fresh_text, fresh_meta, error = future.result()
            if error is not None:
                counts["failed"] += 1
                print(f"FAIL {row['id']} {type(error).__name__}: {error}", flush=True)
                continue
            if fresh_text != (row["content_text"] or ""):
                counts["changed"] += 1
                print(f"SKIP changed {row['id']} {row['canonical_url']}", flush=True)
                continue
            old_meta = json.loads(row["raw_metadata"] or "{}")
            if args.apply:
                cache_reader_images(fresh_meta or {})
                merged = merge_presentation(old_meta, fresh_meta or {})
                conn.execute("UPDATE sources SET raw_metadata=? WHERE id=?", (json.dumps(merged, ensure_ascii=False), row["id"]))
                conn.commit()
            counts["hydrated"] += 1
            print(f"{'APPLY' if args.apply else 'DRY'} {row['id']} blocks={len((fresh_meta or {}).get('article_blocks') or [])} images={len((fresh_meta or {}).get('article_images') or [])}", flush=True)
    conn.close()
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    return 0 if counts["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
