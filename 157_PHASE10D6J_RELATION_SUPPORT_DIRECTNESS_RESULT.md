# Phase 10D.6J — Relation-Support Directness / Canonical Grounding Result

**Status:** CLOSED / INSTRUMENT NOT PROMOTED / CONSERVATIVE SHADOW USE ONLY  
**Date:** 2026-09-11

## Result

Measurement SHA: `342b4b9487417308c581e593a5d56799a6c9ca34`  
Artifact SHA256: `1db72a6e068384d7eadd17fb01d22a36a4f81019a5dd21de789c17fa78fcd7c8`

Six repeated classifications completed with 6/6 structural success. All 16 frozen reference relations were modally stable at >=5/6, and no preregistered critical confusion occurred. Modal exact agreement was 13/16 = 81.25%, below the preregistered 14/16 gate, so the classifier is not promoted as a grounding oracle.

The three disagreements were all on X boundary relations: `CHALLENGE(BT1)` was classified `INSUFFICIENT` rather than reference `CONTRADICTS_OPERATION`; `REINFORCE(Q1)` was conservatively downgraded from `DIRECT` to `PARTIAL`; and `CHALLENGE(B1)` was `PARTIAL` rather than reference `CONTRADICTS_OPERATION`. There was no `DIRECT <-> CONTRADICTS_OPERATION` catastrophic reversal.

## Decision

Do not tune the directness prompt on this calibration set. For the next shadow replay only, use the instrument conservatively:

- `DIRECT`: eligible for strong epistemic authority subject to source provenance.
- `PARTIAL`: retain only as weak epistemic support.
- `INSUFFICIENT`: reject from the canonical grounded effect set.
- `CONTRADICTS_OPERATION`: reject from the canonical grounded effect set.

This use is deliberately asymmetric: uncertainty should downgrade or reject, never create stronger Attention. It remains research-only until a broader holdout validates the grounding contract.

Production defaults remain unchanged. Phase 9A remains paused.
