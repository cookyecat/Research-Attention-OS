# RAOS Reader UX V3.2 — Scholarly Paper Profile Result

Status: **DOGFOOD READY**
Date: 2026-09-15

## 1. Residual

arXiv Sources were previously ingested as ordinary `/abs/...` webpages. That preserved the arXiv abstract-page template rather than the scholarly object itself: the social-share arXiv logo became a repeated hero image, page utilities such as arXivLabs/citation tools leaked into Reader text, and the actual paper body, figures, equations and references were absent.

The first Paper Reader pass also exposed a frontend data race: list views intentionally loaded compact Source objects, while detail view fetched a full Source. A late compact response could overwrite the full detail object, making an already-backfilled paper incorrectly render `Full arXiv HTML is not available for this paper` and leaving its visible Contents controls with no body to navigate.

## 2. Design contract

RAOS now treats a paper as a scholarly object rather than as a generic publisher webpage:

```text
Paper fidelity = scholarly structure fidelity,
not arXiv page fidelity.
```

Preserve title, authors, affiliations, abstract, sections, figures, equations, tables, references, version and canonical scholarly links. Do not preserve arXivLabs chrome, recommendation widgets, citation-tool loading placeholders or the arXiv social-share logo as substantive paper content.
## 3. Paper-aware acquisition

`URLConnector` now detects arXiv `/abs`, `/html`, and `/pdf` paper URLs and delegates them to `ArxivPaperConnector`.

The connector reads citation metadata from `/abs/<id>[vN]`, resolves the version, then prefers official `/html/<id>vN` as the scholarly reading source. It extracts:

- citation title, authors, submitted date, arXiv ID/version and primary category;
- affiliations and abstract;
- top-level paper sections;
- sanitized scholarly HTML with MathML preserved;
- semantic figures with local RAOS media-cache URLs and captions;
- tables and bibliography/references;
- PDF, arXiv abstract, and HTML actions.

If arXiv HTML is unavailable, the Source remains a paper but falls back to an abstract-only profile with explicit PDF/arXiv actions. The arXiv `og:image` logo is never treated as a paper visual.
## 4. Paper Reader

Paper detail now uses a dedicated scholarly layout:

```text
PAPER · arXiv · category · date · reading time
→ title
→ authors / affiliations
→ RAOS judgment
→ PDF / arXiv / HTML
→ Abstract
→ sticky section navigator
→ full scholarly body
→ Figures / equations / tables
→ References
```

The section navigator is rendered only when a full body is present. It uses real buttons bound to the preserved section IDs, scrolls smoothly to the selected section, and follows the current section while the reader moves through the paper. Paper reading progress is section-based rather than paragraph-based.

The Reader keeps RAOS relevance/action context separate from the scholarly body; paper structure is presentation fidelity, not a new cognition authority.
## 5. Existing-library upgrade and provenance boundary

The 10 currently persisted arXiv Sources were upgraded with presentation metadata from official arXiv HTML; all 10 succeeded and none failed. Existing `content_text` was intentionally not overwritten, because some papers already have frozen AnalysisRuns derived from the old Source content. Replacing that cognition input in place would invalidate provenance.

Therefore:

```text
existing analyzed arXiv Source
→ presentation-only scholarly backfill
→ historical AnalysisRun remains frozen

future arXiv arrival
→ PAPER Source
→ full scholarly text becomes canonical cognition input
```

A future explicit reprocess may analyze the upgraded full paper, but Reader presentation does not silently rewrite a historical cognition run.

## 6. Compact list boundary

Full scholarly HTML is large and must not ride on every Inbox/Today/Attention list request. `/sources?compact=true` removes `paper_body_html` and bounds long `content_text`; detail view fetches `/sources/{id}` only when a Source is opened.

On the current dogfood library this reduced the Source-list response from about 2.77 MB to 313 KB (about 89%) while preserving titles, abstracts, paper metadata, lead figures and cognition-state presentation.
## 7. Validation

Focused backend regression:

```text
14 passed, 1 existing warning
```

Production frontend:

```text
typecheck     PASS
clean build   PASS
next start    PASS
```

RodForesight (`arXiv:2609.12103v1`) was used as the browser regression case after the compact/full race fix:

- erroneous `Full arXiv HTML is not available` state: absent;
- top-level paper sections in live DOM: 6;
- section-navigation buttons: 6;
- scholarly body HTML in live DOM: ~138 KB;
- clicking `III Problem Formulation`: `scrollY 0 → 5042`;
- selected section becomes active in the sticky navigator;
- MathML nodes: 102;
- figures: 9;
- references block: present;
- tables: 11.

No D/S/P, Attention policy, Auditor, Kernel authority, Watch semantics, or historical cognition result was changed.