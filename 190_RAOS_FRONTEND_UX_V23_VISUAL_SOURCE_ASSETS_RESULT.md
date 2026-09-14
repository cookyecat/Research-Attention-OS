# 190 — RAOS Frontend UX V2.3 Visual Source Assets Result

Date: 2026-09-14
Status: **IMPLEMENTED / DOGFOOD READY**

## Dogfood residual

Reader preserved article text but discarded the visual layer of URL Sources. Real media pages therefore became long text-only documents in RAOS, producing an unnecessarily sparse and database-like reading experience.

## Minimal correction

`URLConnector` now preserves standard page-level visual metadata during normal URL ingestion:

```text
og:image / twitter:image -> hero_image_url
og:image:alt / twitter:image:alt -> hero_image_alt
```

The metadata stays in `Source.raw_metadata`; no schema migration is required. Cognition input, extracted text, fingerprint semantics, Attention policy, and Kernel authority are unchanged.

## User Space presentation

Reader renders the preserved hero image between article header and Attention note. Today and the default Attention newsroom use the same visual when available, giving media Sources a natural visual anchor while text/PDF/manual Sources remain text-native.

RAOS does not reproduce the original site's DOM or visual design. The goal is a calm native reading surface, not webpage cloning.

## Existing dogfood backfill

A one-time presentation-only backfill fetched visual metadata for all 22 current `URL_FETCH` Sources. Result: **22 updated, 0 failed**. No Source body, AnalysisRun, AttentionPlan, Kernel object, or cognitive result was recomputed.

## Validation

- URL visual-metadata regression: PASS (`7 passed, 1 warning` with acquisition test)
- frontend typecheck/build: PASS
- production dogfood CSS/routes: healthy
- real The Verge Reader: hero image rendered with alt text
- Today and Attention: image-aware editorial layouts visually checked

No canonical cognition architecture changed.
