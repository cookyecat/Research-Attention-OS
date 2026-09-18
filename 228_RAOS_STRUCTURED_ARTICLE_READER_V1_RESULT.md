# RAOS Structured Article Reader V1 — Result

Status: **DOGFOOD READY / PRESENTATION CONTRACT ESTABLISHED**  
Date: 2026-09-17

## 1. Problem

Generic URL acquisition historically flattened publisher articles into canonical plain text. This preserved cognition input but destroyed reading structure: section headings, lists, quotations, figure order, and some body images were lost. Conversely, directly preserving publisher DOM also preserved newsletter, share, related-story, author-card, and recirculation chrome.

The required split is:

```text
canonical content_text
→ stable cognition input

clean article_blocks
→ presentation-only reading structure
```

Therefore:

> **Source fidelity is not publisher DOM fidelity.**

> **Cognition consumes canonical text; Reader consumes cleaned presentation structure.**
## 2. V1 architecture

URL presentation extraction now uses two complementary views:

```text
Publisher HTML
├─ Trafilatura cleaned main-content XML
│  └─ headings / paragraphs / lists / quotes / graphics
└─ cleaned DOM fallback
   └─ captions / list leads / missing body images

→ structural arbitration
→ article_blocks
→ RAOS Reader
```

Trafilatura is preferred when it recovers a real multi-paragraph article body. Cleaned DOM is used when the XML degenerates and loses visible semantic structure. DOM media is filtered for byline/author, related, newsletter, share, promo, recirculation, sidebar/footer chrome and small presentation graphics.

Current presentation contract:

```text
parser                    url-html-v9-publisher-adapters
article_structure_version structured-blocks-v3-tables
```

`content_text` remains unchanged by this presentation layer.

### 2.1 Media continuity invariant

Structured text is not the complete media universe. `article_blocks` owns cleaned text structure and inline still images, while `media_assets` may additionally carry `VIDEO`, `EMBED`, and other live media that are not representable as text blocks. Enabling structured reading must never hide those assets.

```text
article_blocks  → headings / paragraphs / lists / quotes / inline images
media_assets    → supplemental video / trusted embeds / live media
                  ↓
             merged Reader flow
```

Media placement should use the nearest non-empty semantic heading/paragraph when the publisher wraps an iframe/video in an otherwise empty container. Legacy media without a placement anchor must still remain visible through conservative fallback placement rather than disappear.
## 3. Real dogfood validation

NVIDIA Vera Rubin NVL72 article:

```text
4 H2 sections preserved
1 semantic list preserved
3/3 substantive body images preserved
list lead emphasis preserved
publisher navigation/chrome excluded
```

The Verge Google Home MCP article:

```text
article body preserved
2 substantive body images preserved
newsletter / Follow / Share removed
Related / Most Popular / More in removed
author avatar removed
```

Reader typography was simultaneously tuned for long-form legibility using a high-clarity system sans stack, clearer section rhythm, more scannable lists, stronger captions, stable image spacing, and optional bionic reading without mutating source text.

## 4. Historical presentation backfill

A reusable maintenance tool was added:

`scripts/backfill-structured-articles.py`

It fails closed unless the freshly fetched canonical `content_text` is exactly equal to the historical Source text. Only presentation metadata may then be updated.
Observed V2-clean backfill:

```text
eligible  168
hydrated  132
changed    35  → skipped, historical semantics preserved
failed      1  → current OpenAI 403, old presentation preserved
```

Before/after safety counts were identical:

```text
Sources          573 → 573
AnalysisRuns     238 → 238
AttentionPlans   241 → 241
```

No historical cognition was rerun and no AttentionPlan was regenerated.

The maintenance tool now targets `structured-blocks-v3-tables`. It remains dry-run by default and currently sees 189 pre-v3 URL Sources as candidates; no bulk V3 apply was performed during dogfood. Eligibility is not permission to mutate: each candidate must still pass exact canonical-text equality before presentation metadata can change. Historical `raw_metadata.parser` is preserved as acquisition provenance; the newer presentation parser/version is recorded under `presentation_hydration` instead. VIDEO/poster caching is kept aligned with normal URL ingestion so presentation maintenance cannot silently regress media continuity.

## 4.1 WARDOGS media-continuity regression and repair

A real NVIDIA dogfood article (`geforce-now-thursday-wardogs`) exposed a V1 regression: both YouTube embeds remained correctly preserved in `media_assets`, but the structured Reader rendered only `article_blocks`, so the videos disappeared from User Space. Acquisition truth was intact; presentation composition was incomplete.

The repair keeps structured images inside `article_blocks` while merging non-image `media_assets` back into the structured reading flow. Fresh acquisition also records semantic placement context for media inside empty wrapper paragraphs. Real browser validation restored both embeds at their intended sections: `WARDOGS | Gameplay Trailer` after `Who Let the ‘WARDOGS’ Out?`, and the Valheim trailer after `Ice, Ice in the Deep North, Baby`.


## 4.2 Semantic-body / table / long-text fidelity residuals — 2026-09-17

Real dogfood exposed three distinct acquisition-fidelity failures that must remain upstream of Cognition:

```text
Nature semantic article body
→ outer compatibility / access-wall chrome had leaked into canonical text
→ explicit publisher article-body containers now outrank whole-page heuristics

Elastic semantic tables
→ Trafilatura XML preserved <table>, but RAOS dropped it while building article_blocks
→ table is now a first-class structured block with headers + rows

Weibo long-text preview
→ public timeline preview ending in “... 全文” had been persisted after detail hydration failed
→ explicit truncation markers now trigger detail hydration even when isLongText is unreliable
```

If a newly recovered body changes canonical semantic content, RAOS does **not** rewrite the historical Source or AnalysisRun. It appends a corrected `InformationSnapshot` / Source and routes that snapshot through canonical Execution-Integrity-gated cognition. The historical Source may receive an explicitly labelled presentation correction (`display_content_text` or corrected `article_blocks`) so old shared Reader links are not forced to keep displaying a known-bad preview.

Observed repairs:

```text
Nature  d41586-026-02899-2
  cleaned canonical text     2881 chars
  structure                  2 headings / 7 paragraphs / 1 body image
  compatibility + access wall removed

Elastic ai-code-optimization...
  canonical content_text     unchanged
  semantic tables            3 restored
  publisher Related Content  trimmed

Weibo RibYOwVh7
  historical cognition text  206-char truncated preview preserved
  corrected detail body      981 chars
  old Reader link            displays corrected body
  corrected snapshot         canonical reconciliation completed
```

## 5. Validation

```text
focused acquisition regression 29 passed
full backend regression     811 passed / 63 skipped / 1 pre-existing Case-K PREEMPT residual
frontend typecheck          PASS
production build            PASS
Execution Integrity         ATTESTED / all capabilities READY
```

The remaining full-suite failure is the previously attributed `test_case_k_preempt` (`PRIORITY` vs historical `PREEMPT`) and is outside URL acquisition / Reader presentation.

## 6. Frozen Reader principle

> **Preserve the information object, not the publisher machinery.**

Acquisition should retain enough structure and media evidence to reconstruct a high-quality reading object. Reader may improve typography, hierarchy, spacing and progressive disclosure, but presentation metadata must never silently become cognitive evidence or rewrite historical canonical text.

## Publisher diversity — generic semantics first, adapters when evidence demands them

Dogfood on NVIDIA exposed a recurring layout ambiguity: a semantic article body may live inside a layout wrapper named `post-with-sidebar`. A substring-based boilerplate filter incorrectly treated every descendant as sidebar content and erased valid H2 hierarchy.

The acquisition rule is now:

```text
generic semantic article-body detection
→ cleaned structural extraction
→ publisher layout semantics / adapter only when repeated dogfood evidence requires it
```

A layout modifier such as `with-sidebar` or `has-sidebar` is not itself a sidebar region. True sidebar / recirculation regions remain excluded.

The long-term goal is not one parser per URL. It is a stable generic acquisition contract plus a small set of publisher policies for recurrent DOM conventions. Publisher-specific logic must improve presentation fidelity without changing frozen canonical source text unless an append-only acquisition correction is explicitly warranted.

## OpenAI publisher adapter — 2026-09-18

Dogfood exposed an OpenAI-specific acquisition failure mode: publisher-direct article fetches may return a Cloudflare 403 challenge even though the public article is readable interactively. The URL presentation contract therefore advanced to `url-html-v9-publisher-adapters` while retaining `structured-blocks-v3-tables`.

The OpenAI policy is fail-explicit and provenance-preserving: publisher-direct fetch is attempted first; only OpenAI article URLs that are blocked by 403/429 may use the rendered fallback. Metadata records `publisher_fetch_mode`, the direct status, and the fallback provider so rendered evidence is never misrepresented as publisher-direct acquisition.

OpenAI article hierarchy is taken from the publisher's semantic `article [data-toc-content]` region when available. This preserves H2/H3, paragraphs, lists and quotations while excluding Author, Footnotes and Keep reading recirculation. Generic media extraction remains authoritative for standard image/video/embed elements; opaque client-only media is not fabricated when no stable asset URL is exposed.

Historical repair obeys the same immutability rule as earlier Reader migrations: frozen cognition text is never silently replaced by current publisher text. The existing full-body v4 article received presentation-only heading projection, while ten historical RSS-fallback summaries were upgraded append-only through new full-body Sources and InformationSnapshots, then reconciled under canonical ATTESTED cognition.

## OpenAI publisher adapter hardening — 2026-09-18

OpenAI article pages may return a JS/cookie challenge to non-browser fetchers. `url-html-v9-publisher-adapters` therefore treats publisher-direct 403/429 as a recoverable transport condition, uses a rendered fallback only when semantic completeness (`<article>` + `data-toc-content`) is present, and records the fallback provenance explicitly. The fallback is retried with bounded backoff because the rendering provider can transiently return the publisher challenge itself. Challenge/interstitial HTML is never persisted as article truth.

`article [data-toc-content]` is the OpenAI semantic-body contract. H2/H3/list/quote structure is preserved while author, footnotes, navigation and recirculation remain outside the Reader body. If the rendered fallback cannot verify client-hydrated media, `publisher_dynamic_media_status=unverified_from_rendered_fallback` is persisted and Reader shows a non-alarming `MEDIA PARTIAL` notice rather than silently implying media completeness. Historical captures may use `not_preserved_by_historical_capture` for the same user-facing transparency without rewriting frozen cognition input.

RSS fallback is now self-healing. A fallback Snapshot remains append-only historical evidence, but later polls retry the publisher URL; a successful fetch creates a new full-body Snapshot with `recovered_from_feed_fallback=true`, while a failed retry leaves the existing summary intact and records `fallback_recovery_last_error`. Degraded acquisition is therefore a recoverable state rather than a permanent downgrade.
