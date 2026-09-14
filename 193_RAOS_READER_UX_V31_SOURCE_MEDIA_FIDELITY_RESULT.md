# RAOS Reader UX V3.1 — Source Media Fidelity Result

Date: 2026-09-14
Status: **CLOSED / DOGFOOD READY**

## Residual

The AlphaGenome Atlas dogfood Source contains both a YouTube embed and a native WebM animation. RAOS previously preserved only image-oriented visual metadata. The native video's generic fallback poster entered `article_images`, producing a large gray Reader block while both playable media assets disappeared.

## Contract

Reader preserves substantive source media without mirroring publisher page machinery. Acquisition stores presentation-only `media_assets[]` entries for semantic images, trusted embeds, and native video together with source-context/caption metadata. Publisher navigation, ads, avatars, related-story thumbnails, tracking assets, and generic video fallback posters remain excluded. Media preservation does not grant media any cognition authority.

## Implementation

- `IMAGE`: preserved as before, now with optional local cached URL.
- `EMBED`: trusted YouTube/Vimeo iframe URL, title/provider, aspect ratio, and nearby source context; Reader re-embeds lazily.
- `VIDEO`: source URL, MIME type, optional non-fallback poster, caption/context, and optional cached URL; Reader uses native controls with autoplay disabled.
- direct image/video assets are cached locally up to 12 MB per asset; failed/oversized caches fall back to original URLs.
- cached assets are served through `/media/{filename}` and the frontend `/api` rewrite; FileResponse provides byte-range playback.
- Reader inserts media by preserved `context_text`, retaining attentional flow rather than publisher DOM/layout.

## Validation

Focused URL metadata regression: 3 tests passed. Existing 22 URL_FETCH Sources were presentation-only backfilled: 22 updated, 0 failures, with no cognition rerun. AlphaGenome produced one `YOUTUBE` embed plus one cached WebM video (915,730 bytes). A browser-level Reader probe observed one embed iframe and one native `<video>`; the video loaded from `/api/media/...`, reported `readyState=4`, `duration=26`, `controls=true`, `autoplay=false`, and a 16:9 rendered frame. HTTP range probing returned `206 Partial Content`.

## Authority boundary

No `Source.content_text`, Sensor/Auditor output, Claim, D/S/P estimate, cognitive effect, Attention decision, Watch obligation, Kernel state, or human authorization semantics changed. This is a Source-fidelity and reading-experience improvement only.
