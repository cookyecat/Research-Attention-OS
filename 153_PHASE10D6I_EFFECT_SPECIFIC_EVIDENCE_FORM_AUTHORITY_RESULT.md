# Phase 10D.6I — Effect-Specific Evidence-Form Authority Result

**Status:** CLOSED / NEAR-PASS / SINGLE-FORM TAXONOMY NOT PROMOTED
**Date:** 2026-09-11

## Result

Measurement SHA: `8dca45a`

Canonical artifact:
`eval/live/results/phase10d6i_evidence_form_authority_v0_1/phase10d6i_evidence_form_authority_v0.1_20260911T075621Z.json`

Artifact SHA256:
`608fbf1a3bac70ef9dda44e1bdc8b1abe375f18b429603ca890e5cbb664a8d88`

Six batch runs completed with 18/18 identifiers each time.

- provenance-role modal exact agreement: `18/18 = 1.000`;
- provenance-role 5/6 stability: `18/18 = 1.000`;
- evidence-form modal exact agreement: `16/18 = 0.8889`;
- evidence-form 5/6 stability: `18/18 = 1.000`;
- preregistered critical confusions: `0`.

The two disagreements were fully stable rather than stochastic:

1. `A::neu-003`: reference `EVALUATIVE_ASSERTION`, classifier `TECHNICAL_DESCRIPTION` 6/6. The unit mixes a product capability claim with a concrete description of intended model behavior.
2. `N4::neu-002`: reference `MEASUREMENT_RESULT`, classifier `MEASUREMENT_PROTOCOL` 6/6. The unit mixes simulator-pausing protocol with a quantitative 83 Hz vs 0.2–0.4 Hz latency gap.

## Interpretation

The two-axis idea is supported: provenance role is cleanly separable from evidence form, and categorical classification is highly stable without numeric confidence/strength scores.

However, forcing every unit into exactly one evidence form is too lossy for mixed evidence objects. The preregistered >=0.90 evidence-form agreement gate was not met, so v0.1 is not promoted.

Do not relabel the original 18 items after seeing outcomes. Instead, refine the representation to a compositional set of evidence forms and validate on fresh held-out units not used in 10D.6I.

No Attention policy or production default changed. Phase 9A remains paused.
