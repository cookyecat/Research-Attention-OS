# Phase 10D.6I.1 — Compositional Evidence Form Fresh Holdout Result

**Status:** CLOSED / NOT PROMOTED / PROVENANCE PASSES, FULL FORM-SET TAXONOMY TOO BRITTLE
**Date:** 2026-09-11

Measurement SHA: `359fcf0`

Canonical artifact:
`eval/live/results/phase10d6i1_compositional_evidence_form_holdout_v0_1/phase10d6i1_compositional_evidence_form_holdout_v0.1_20260911T080347Z.json`

Artifact SHA256:
`417b6ed1450f15fe77af00596590f2426fa0bd3ceeb4bc7c1de072b43c37e13b`

Fresh B3/B4/F3/F4 holdout result across six batch runs:

- structural success: 6/6;
- provenance-role modal exact agreement: `1.000`;
- evidence-form exact-set agreement: `0.700`;
- mean modal Jaccard: `0.8417`;
- >=5/6 modal-set stability: `0.900`;
- critical confusions: `0`.

The misses were mostly companion-form disagreements (for example protocol + event, measurement + interpretation/limitation), not measurement/assertion inversions. Provenance role remains highly stable; exact exhaustive evidence-form decomposition is not sufficiently robust or necessary to become an Attention authority.

Decision: retain categorical provenance as a promising authoritative world-model attribute; stop optimizing exhaustive evidence-form taxonomy. Move to relation-specific support directness/scope, which is the decision-bearing grounding question. No production policy changes. Phase 9A remains paused.
