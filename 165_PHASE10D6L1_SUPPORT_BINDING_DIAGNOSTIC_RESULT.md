# Phase 10D.6L.1 — Combined Support-Binding Diagnostic Result

**Status:** CLOSED / COMBINED TASK NOT PROMOTED
**Date:** 2026-09-12
**Measurement SHA:** `14f3ca5`
**Artifact SHA256:** `3986baf95cbe25f442fbfc6486923e2c320cdd338f398c860f64375b08b1cba1`

## Question

When both prompt arms receive the same explicit `support_unit_ids` / `jurisdiction_anchor_ids` obligation, does provenance binding behave like bookkeeping, or does it alter weak-model Relation Mapping?

## Result

48/48 structured calls succeeded and every emitted identifier passed deterministic legality. However, provenance obligation was **not behavior-neutral** for DeepSeek-Flash.

Most strikingly, Case A was empty 6/6 in both arms of the primary prompt shadow, but the combined relation+binding task emitted `OPEN_NEW` in 6/6 P0 and 5/6 P1 samples. Case D similarly shifted toward multiple `OPEN_NEW` branches. Therefore support binding cannot be treated as pure plumbing when bundled into the same weak-model generation task.

## Strong/weak evaluator interpretation

The strong-model reference was frozen before this diagnostic outcome. It judged A and D empty, X core as `REINFORCE(M1)`, and N4 core as `REINFORCE(B1) + REINFORCE(BT1) + REINFORCE(M1)`.

Against that reference, the combined P1 task showed both beneficial and harmful weak-model coupling:

- X recovered `M1` in 5/6 samples, but also emitted weaker BT1/Q1 branches.
- N4 recovered B1/BT1/M1 in 6/6 samples, matching the strong core, while also emitting Q1 6/6.
- A/D created new OPEN_NEW branches that were absent from the strong reference and absent from the primary A relation mapping.

Therefore isolated weak-model errors are not architecture failures. But the fact that adding a second responsibility changes relation topology is an architectural separation signal.

## Decision

Do not promote a combined `Relation Mapping + Support Binding` LLM contract as the production architecture.

Next gate: decouple the responsibilities. Freeze Relation Mapping output first; then run a separate Support Binding stage that may only attach exact evidence/jurisdiction identifiers to the frozen relations. It must not add, remove, retarget, or change operation.

Grounding remains the later stage that decides whether the bound evidence actually licenses the relation at the target scope. This preserves the single-responsibility pipeline and lets weak-model robustness be measured without treating the weak evaluator as Gold.

Production default remains unchanged. Phase 9A remains paused.
