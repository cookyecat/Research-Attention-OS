# Phase 10D.6I — Effect-Specific Evidence-Form Authority

**Status:** PREREGISTERED / REFERENCE FROZEN / NO 10D.6I CLASSIFIER OUTCOME SAMPLED
**Date:** 2026-09-11

## Question

Can RAOS replace effect-level LLM `epistemic_strength` with an auditable categorical evidence representation attached to the exact `support_unit_ids` established in 10D.6G/H?

This gate does **not** yet decide Attention. It first tests whether evidence form can be represented stably without a pseudo-cardinal score.

## Representation

Two orthogonal axes are frozen:

- provenance role: `PRIMARY_SOURCE | SECONDARY_SOURCE | DERIVED | UNKNOWN`;
- evidence form: `MEASUREMENT_RESULT | MEASUREMENT_PROTOCOL | TECHNICAL_DESCRIPTION | EVENT_OR_STATE_REPORT | EVALUATIVE_ASSERTION | LIMITATION_OR_UNCERTAINTY | ANALYTIC_INFERENCE`.

Provenance role answers *where the evidence comes from*. Evidence form answers *what kind of epistemic object it is*. Neither axis directly equals truth or Attention.

## Frozen reference

`eval/live/phase10d6i_evidence_form_reference_v0_1.json` contains 18 manually reviewed units from the already-frozen A/D/X/N4 worlds. It was written before any 10D.6I classifier outcome. It is a research reference, **not Human Gold**.

The set intentionally contrasts primary benchmark measurements, primary technical descriptions, first-party evaluative claims, secondary event reporting, and explicit limitations.

## Instrument test

Run six fresh batch classifications over the same 18 reference units, thinking disabled, temperature 0.1. The classifier may emit only the two categorical labels plus a reason; no numeric confidence or epistemic score is allowed. Unknown/missing unit IDs fail closed.

Primary descriptive gates:

1. 6/6 structural success and 18/18 identifier completeness per run.
2. Modal exact agreement with the frozen reference >= 0.90 on each axis.
3. >=90% of units have a modal label frequency >=5/6 on each axis.
4. No modal critical confusion:
   - reference `MEASUREMENT_RESULT` -> `EVALUATIVE_ASSERTION`;
   - reference `EVALUATIVE_ASSERTION` -> `MEASUREMENT_RESULT`;
   - reference `SECONDARY_SOURCE` -> `PRIMARY_SOURCE` or vice versa.

Passing this gate only licenses the categorical instrument for downstream authority experiments. It does not itself license `SUFFICIENT`, ENGAGE, or production promotion.

Production defaults remain unchanged; Phase 9A remains paused.
