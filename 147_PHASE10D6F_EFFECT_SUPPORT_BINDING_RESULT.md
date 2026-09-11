# Phase 10D.6F — Effect Support Binding Result

**Status:** COMPLETE / SUPPORT BINDING FEASIBLE / RELATION CONTRACT NOT PROMOTED
**Date:** 2026-09-11

Measurement SHA: `8422271`.

Canonical valid artifact: `eval/live/results/phase10d6f_effect_support_binding_v0_1/phase10d6f_effect_support_binding_v0.1_20260911T065730Z.json`, SHA256 `6b7f5991a5840ccd5c7898040b7d03471673f4fe4cef518d387c5d0415458e35`.

The earlier 0/24 technical run is retained separately by amendment `146_PHASE10D6F_ENV_LOADING_FAILURE_AND_AMENDMENT.md` and is not a semantic outcome.

## Result

All 24 preregistered fresh Relation-Mapping calls completed structurally. A and D emitted no effects in all 6/6 repetitions. X emitted 35/35 valid effects and N4 emitted 33/33 valid effects; no emitted effect used an unknown support unit, target, or jurisdiction anchor.

X produced only OPEN_NEW branches. N4 recovered targeted relations: `REINFORCE(BT1)`, `REINFORCE(B1)`, and `REINFORCE(M1)` occurred 6/6; `REINFORCE(Q1)` occurred 4/6; `CHALLENGE(B1)` occurred 2/6. `REINFORCE(BT1)` bound to `neu-002` in 6/6 samples, demonstrating that relation-specific support identity can be stable when the evidence is concrete.

Support binding is therefore mechanically feasible and provides a usable provenance seam for later epistemic authority. However, this phase also changed Relation-Mapping semantics: the support-bound prompt removed compatibility cardinal fields and added stricter direct-support/scope language. Because A/D collapsed to empty and X lost the targeted relations seen under the historical native contract, these outcomes cannot be attributed to support binding alone.

The run also exposed deterministic duplicate identity work: X sometimes emitted multiple OPEN_NEW effects with the same support signature inside one realization. These should be normalized by the established support-signature branch identity, not resolved by another LLM score.

## Decision

Do not promote the 10D.6F Relation contract. Preserve `support_unit_ids` and `jurisdiction_anchor_ids` as the leading vNext provenance fields, but isolate their effect from prompt/schema semantic drift next.

Next gate: **Phase 10D.6G — Native-Semantics Support-Binding Parity Shadow**. Keep the historical native Relation semantics and compatibility fields, add support/jurisdiction binding only, and compare whether historical targeted topology can coexist with explicit provenance. Production defaults remain unchanged; Phase 9A remains paused.
