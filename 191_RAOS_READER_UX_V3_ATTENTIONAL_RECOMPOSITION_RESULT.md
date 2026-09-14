# 191 — RAOS Reader UX V3: Attentional Recomposition Result

Date: 2026-09-14
Status: **IMPLEMENTED / DOGFOOD READY**

## 1. Residual that motivated V3

Reader UX V2.3 established a major visual improvement by preserving publisher-declared hero images. Real use then exposed four further opportunities to reduce reading friction:

1. meaningful article-internal diagrams/figures were still discarded;
2. the right RAOS rail repeated static guidance while the user was already reading;
3. audited Claim evidence was visible only in Inspector instead of being anchored back to the original sentences;
4. half-bold/bionic reading required an external browser extension and therefore could not be relied on for RAOS Web/App users.

These are presentation/reading-layer residuals. No new cognition contract was required.

## 2. Reader design contract

The implementation is governed by `RAOS_FRONTEND_DESIGN_PRINCIPLES.md`.

Core principle:

```text
RAOS Reader is not a webpage mirror.
RAOS Reader re-composes the attentional structure of a source.
```

The Reader preserves source truth/provenance but does not reproduce publisher navigation, advertising, related-content modules, social controls, or arbitrary source DOM/layout.

Working visual model:

```math
Visual\ Value = Semantic\ Information + Attentional\ Structure + Reading\ Rhythm
```

## 3. Audited evidence anchors

Existing AnalysisResult Claims already preserve `source_span_text`. V3 maps those frozen evidence spans back onto preserved `Source.content_text` at render time.

```text
frozen Claim/Auditor result
→ presentation-only sentence alignment
→ subtle underline in original text
```

No claim is regenerated to support the UI. Clicking an anchored source sentence selects the corresponding Claim and exposes a concise human-readable evidence explanation in the Reader rail; raw structured Claim fields remain in RAOS Inspector.

Real OpenAI/RubyGems dogfood produced **11 source-text evidence anchors**.

## 4. Scroll-aware reading companion

The rail is now task-sensitive rather than permanently static.

Before the reader enters the body, the rail emphasizes:

- why the source matters to the user;
- the recommended next action;
- closest current context;
- explicit entry to RAOS Inspector.

Once reading begins, it adds live reading progress, paragraph position, and locally relevant audited evidence for the paragraph nearest the reading focus.

Production-browser validation on the OpenAI/RubyGems article observed:

```text
reading progress: 42%
paragraph: 3 / 5
nearby evidence: present
rail state: is-reading
```

## 5. Embedded half-bold reading

RAOS Preferences now provides an internal reading aid independent of browser extensions:

```text
Half-bold reading  Off / On
Half-bold weight   Soft / Medium / Strong
```

Only Latin-word prefixes receive presentation-only emphasis. Original Source text, copy/search semantics, cognition input, Claims, Attention decisions, and Kernel state are unchanged.

## 6. Semantic article-internal visuals

`URLConnector` now preserves conservative article-internal visual structure in `Source.raw_metadata.article_images`.

V3 deliberately does **not** copy every `<img>` from a webpage. It currently admits semantic `<figure>` assets, preserves URL / alt / caption / nearby textual context, deduplicates the publisher hero image, and caps the result set. Author avatars, sponsor logos, recommendation thumbnails, and unrelated page chrome remain outside Reader.

Reader uses the saved `context_text` to place a figure close to the paragraph it originally explained. If no semantic figure is present, the article remains text-first rather than receiving synthetic decoration.

Current dogfood backfill found real inline visual use cases in 3 of 22 URL_FETCH Sources: DeepMind AlphaGenome Atlas (1 explanatory figure), NVIDIA Robotaxi (2 charts), and NVIDIA GeForce NOW (1 article figure). No cognition was rerun.
## 7. Validation

Focused backend visual-metadata regression:

```text
8 passed, 1 existing warning
```

Frontend TypeScript and clean production build passed. Production-browser checks verified:

- 11 audited evidence anchors on the OpenAI/RubyGems article;
- scroll-aware rail transition with live progress (`42%`, paragraph `3 / 5`) and nearby evidence;
- Half-bold Strong mode produces computed `font-weight: 800` on fixation prefixes;
- DeepMind AlphaGenome renders one preserved inline figure immediately after its matching semantic-context paragraph;
- all new reading aids remain presentation-only and leave Source text / cognition authority unchanged.

## 8. Frozen boundary

Reader V3 changes reading composition, not RAOS cognition. `RAOS_CANONICAL_ARCHITECTURE.md`, D/S/P, Sensor/Auditor contracts, Attention policy, Watch semantics, Kernel authority, and human authorization boundaries are unchanged.

Future Reader changes should obey `RAOS_FRONTEND_DESIGN_PRINCIPLES.md` and be driven by observed reading residuals rather than source-site imitation.
