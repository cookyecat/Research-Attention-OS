from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urldefrag, urlparse

import httpx

from app.config import settings

_MEDIA_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "video/webm": ".webm",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
}

def media_cache_dir() -> Path:
    configured = Path(settings.media_cache_dir).expanduser()
    if not configured.is_absolute():
        configured = Path(__file__).resolve().parents[2] / configured
    configured.mkdir(parents=True, exist_ok=True)
    return configured

def _extension(url: str, content_type: str | None) -> str:
    clean_type = (content_type or "").split(";", 1)[0].strip().lower()
    if clean_type in _MEDIA_EXTENSIONS:
        return _MEDIA_EXTENSIONS[clean_type]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix and len(suffix) <= 6:
        return suffix
    return mimetypes.guess_extension(clean_type) or ".bin"

def cache_remote_media(url: str | None, *, max_bytes: int | None = None) -> str | None:
    if not url:
        return None
    from app.connectors.url import validate_public_url

    fetch_url = urldefrag(url)[0]
    try:
        validate_public_url(fetch_url)
    except Exception:
        return None
    limit = max_bytes or settings.media_cache_max_bytes
    key = hashlib.sha256(fetch_url.encode("utf-8")).hexdigest()[:24]
    cache_dir = media_cache_dir()
    for existing in cache_dir.glob(f"{key}.*"):
        if existing.is_file():
            return f"/api/media/{existing.name}"
    temp = cache_dir / f".{key}.part"
    try:
        with httpx.Client(follow_redirects=True, timeout=settings.url_fetch_timeout_seconds) as client:
            with client.stream("GET", fetch_url, headers={"User-Agent": "RAOS/1.1"}) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if not (content_type.startswith("image/") or content_type.startswith("video/")):
                    return None
                announced = response.headers.get("content-length")
                if announced and int(announced) > limit:
                    return None
                total = 0
                with temp.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > limit:
                            handle.close()
                            temp.unlink(missing_ok=True)
                            return None
                        handle.write(chunk)
        target = cache_dir / f"{key}{_extension(fetch_url, content_type)}"
        temp.replace(target)
        return f"/api/media/{target.name}"
    except Exception:
        temp.unlink(missing_ok=True)
        return None

def cached_media_path(filename: str) -> Path | None:
    if not filename or Path(filename).name != filename:
        return None
    path = media_cache_dir() / filename
    return path if path.is_file() else None
