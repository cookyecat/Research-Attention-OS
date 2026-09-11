# Phase 10D.6I.1 — Compositional Evidence Form Fresh Holdout

**Status:** PREREGISTERED / FRESH HOLDOUT FROZEN / NO 10D.6I.1 OUTCOMES SAMPLED
**Date:** 2026-09-11

## Motivation

10D.6I produced perfectly stable labels but missed the single-form exact-agreement gate on two intrinsically mixed units. The reference is not relabeled after outcomes. Instead, evidence form becomes a small categorical set while provenance role remains a single orthogonal label.

## Representation

Each evidence object has:

- one `provenance_role`;
- one to three `evidence_forms` from the unchanged 10D.6I vocabulary.

This is compositional, not cardinal: there is still no confidence, strength, probability, importance, or Attention score.

## Fresh holdout

`eval/live/phase10d6i1_compositional_evidence_form_holdout_v0_1.json` freezes 20 units from B3/B4/F3/F4. None were in the 10D.6I 18-unit reference. B3/B4 are original Anthropic research sources; F3/F4 are institutional science-communication pages summarizing underlying research/measurements and are treated as secondary provenance relative to the reported scientific evidence.

## Measurement

Run six fresh batch classifications, temperature 0.1, thinking disabled. Output exactly one provenance role plus 1–3 evidence forms per unit. Unknown IDs, missing IDs, duplicate IDs, empty form sets, or out-of-vocabulary forms fail closed.

Descriptive gates:

1. 6/6 structural success and complete 20-ID coverage.
2. Provenance modal exact agreement >=0.90.
3. Evidence-form modal exact-set agreement >=0.85 and mean modal Jaccard >=0.90.
4. >=90% of units have the same modal form set in >=5/6 runs.
5. No critical modal confusion that drops `MEASUREMENT_RESULT` from a reference measurement-only item and replaces it only with `EVALUATIVE_ASSERTION`, or flips PRIMARY/SECONDARY provenance.

Passing licenses compositional evidence-form metadata as an input to later relation-specific epistemic-authority experiments only. It does not itself imply `SUFFICIENT`, ENGAGE, or production promotion.

Production defaults unchanged; Phase 9A remains paused.
