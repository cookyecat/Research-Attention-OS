# Phase 10D.6H — Cardinal-Field Removal Parity Result

**Status:** COMPLETE / CARDINAL-FREE RELATION CONTRACT SUPPORTED / NOT YET PRODUCTION-PROMOTED
**Date:** 2026-09-11

Measurement SHA: `e449001`.

Artifact: `eval/live/results/phase10d6h_cardinal_field_removal_parity_v0_1/phase10d6h_cardinal_field_removal_parity_v0.1_20260911T071632Z.json`, SHA256 `86e1dc644aa0b7a8e6f559b2fd674357268ba12ecd82b586ed626b655965e29c`.

## Result

All 24 preregistered calls completed successfully after removing `change_magnitude`, `epistemic_strength`, and `target_importance` from every Relation-Mapping effect. No replacement score or threshold was introduced.

The stable 10D.6G relation core broadly survived. A recovered all 4/4 G sentinels at least once and 3/4 in a majority of samples; D recovered 7/7 at least once and 6/7 by majority; X recovered 5/5 by majority; N4 recovered 5/5 in all 6/6 samples. N4's cardinal-free topology was especially stable: `OPEN_NEW`, `REINFORCE(B1)`, `REINFORCE(BT1)`, `REINFORCE(M1)`, and `REINFORCE(Q1)` each appeared 6/6.

The run emitted 141 raw effects and retained 133 after deterministic legality. A had three `OPEN_NEW_TARGET_NOT_NULL` violations; X had five `TARGET_NOT_UPDATE_ELIGIBLE` violations. D and N4 were 100% identifier/legal-target valid. No duplicate relation identities required normalization.

The legality failures are evidence for keeping deterministic constitutional guards, not for restoring numeric fields. The cardinal-free model still generated rich multi-effect topology while the system rejected malformed target semantics explicitly.

## Interpretation

The three legacy effect-level cardinal fields are not required for semantic Relation Mapping on this frozen real-web corpus. Removing them does not reproduce the 10D.6F empty-topology failure when native semantics and support binding are preserved. The 10D.6F collapse is therefore not evidence that numeric fields are needed; it was primarily a semantic-prompt/schema rewrite effect.

This supports the vNext separation:

```text
Relation LLM -> operation + target/jurisdiction + support_unit_ids + reason
Authoritative enrichment -> importance band + epistemic band + active role
Decision policy -> Anchored + Magnitude-Free + Pareto + article join
```

## Decision

Promote the **cardinal-free support-bound relation contract** to the leading research contract, but do not switch production default yet. The next unresolved authority is epistemic evidence class: `SOURCE_CLAIM` is too coarse to distinguish primary technical measurement from product assertion or secondary reporting.

Next gate: **Phase 10D.6I — Effect-Specific Evidence-Class Authority**. Production defaults remain unchanged; Phase 9A remains paused.
