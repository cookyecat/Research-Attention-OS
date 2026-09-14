# RAOS Inbox / Attention UX Editorial Rhythm Result

Status: **DOGFOOD READY**
Date: 2026-09-14

## 1. Residual

After Acquisition source diversity increased, Inbox exposed a new product residual: the content pool was richer, but presentation remained a uniform card matrix. Repeated equal-size cards created fast visual habituation, flattened source identity, and made the page feel like storage rather than a living intake surface.

A second residual was state blindness. Inbox showed what RAOS had acquired but not whether a Source had already been judged `DROP`, `AWARE`, `WATCH`, or `ENGAGE`. Reader detail had the opposite problem: the disposition existed, but appeared after the hero image rather than at the beginning of the reading journey.

## 2. Design contract

The refinement freezes two principles:

```text
Inbox is a living intake landscape, not a storage grid.
The RAOS judgment should appear before the reading journey begins.
```

Inbox remains chronological and observational. Editorial sizing is a presentation rhythm, not a hidden recommender or importance score.

## 3. Inbox implementation

Inbox now reads `/sources` and the existing source-centric `/kernel/attention` ledger in parallel. It resolves the latest `AttentionPlan` per Source by `created_at` and exposes the current disposition directly on each analyzed Source card. Sources without a plan are marked `Not analyzed`; no judgment is fabricated.

The Source Library uses a deterministic 12-column editorial rhythm: a lead visual anchor, two secondary cards, then recurring wide / standard / compact forms. Hero media and text density adapt to the form. Cognition state remains a small semantic chip and subtle edge accent so RAOS state is legible without replacing the Source itself.

State filters (`ENGAGE / WATCH / AWARE / DROP / Not analyzed`) are available alongside source filters and search. Chronology remains the primary ordering rule.

## 4. Reader entry hierarchy

Reader now presents:

```text
source / author / time
→ title
→ RAOS disposition + plain-language action copy
→ Open original
→ source media
→ body
```

The previous duplicate disposition strip below hero media was removed. `Open original` remains available as a secondary action beside the disposition rather than occupying the primary post-title position.

## 5. Validation

Validation used the current production dogfood runtime, not a mock page.

- `npm run typecheck`: PASS
- clean `next build`: PASS
- production `next start`: PASS
- Inbox production screenshot: editorial lead/secondary hierarchy visible; latest cognition chips visible on cards
- AlphaGenome Reader production screenshot: `AWARE` appears immediately below title; `Open original` is secondary; hero media/body remain intact
- historical AttentionPlan check: Sources with multiple historical plans resolve to the most recent `created_at`

No backend cognition, D/S/P, Attention policy, Acquisition semantics, Watch responsibility, or Kernel authority changed.
