# Phase 10D.6J — Relation-Support Directness / Canonical Grounding

**Status:** PREREGISTERED / REFERENCE FROZEN / NO 10D.6J OUTCOMES SAMPLED
**Date:** 2026-09-11

## Question

Given a support-bound, cardinal-free cognitive relation, does the cited evidence directly justify the stated operation on the exact target proposition and scope?

This is distinct from source reliability. A secondary source can be directly about a proposition but still receive weaker epistemic authority later; a primary measurement can be high-quality evidence yet still be irrelevant to a different target scope.

## Fit classes

- `DIRECT`: support directly bears on the target proposition at matching scope and in the stated operation direction.
- `PARTIAL`: materially relevant but requires a bounded extrapolation or has a meaningful scope gap.
- `INSUFFICIENT`: topical/related evidence does not justify the operation on that target.
- `CONTRADICTS_OPERATION`: the support more naturally points opposite the proposed REINFORCE/CHALLENGE direction.

No numeric score is emitted.

## Frozen calibration reference

`eval/live/phase10d6j_relation_support_directness_reference_v0_1.json` freezes 16 manually audited relation instances from the already-frozen 10D.6H cardinal-free support-bound artifact before any 10D.6J classifier result. This is a calibration reference, not Human Gold.

The set intentionally contrasts A/D scope extrapolations, X operation-direction errors, and N4 direct latency/control evidence.

## Measurement

Run six batch classifications of the same 16 reference relations. Inputs contain only operation, exact Kernel target proposition, cited support-unit statements/excerpts, and the relation reason. Do not show historical Attention or reference labels.

Gates:
1. 6/6 structural success and complete identifiers.
2. Modal exact agreement >=0.875 (14/16).
3. >=90% items have modal stability >=5/6.
4. No `DIRECT` reference is modally `INSUFFICIENT`/`CONTRADICTS_OPERATION`; no `CONTRADICTS_OPERATION` reference is modally `DIRECT`.

Passing licenses the fit category as an input to offline epistemic-authority replay only. It does not itself change production or Attention. Phase 9A remains paused.
