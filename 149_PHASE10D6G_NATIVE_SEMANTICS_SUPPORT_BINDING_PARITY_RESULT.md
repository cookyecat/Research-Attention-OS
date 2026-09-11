# Phase 10D.6G — Native-Semantics Support-Binding Parity Result

**Status:** COMPLETE / SUPPORT BINDING COMPATIBLE WITH NATIVE RELATION SEMANTICS / NOT PROMOTED
**Date:** 2026-09-11

Measurement SHA: `754a7832baa9b87a4dcf5e1a772b3450dc58a996`.

Artifact: `eval/live/results/phase10d6g_native_support_binding_parity_v0_1/phase10d6g_native_support_binding_parity_v0.1_20260911T070844Z.json`, SHA256 `e4b9409414fc4c6f08cb5ba651eb1ad58dece7ff7636e0dd1d6582c2bfdaf63b`.

## Result

All 24 preregistered calls completed. Across A/D/X/N4 the model emitted 144 raw effects; 136 passed deterministic identifier/target legality. The only eight rejected effects were in X and attempted to update non-update-eligible location nodes (`G1` six times, `P1` twice). The legality guard therefore correctly preserved `Location != Update` without rewriting the effect.

Historical native relation families substantially returned once the historical `NATIVE_IMPACT_SYSTEM` semantics were retained and provenance fields were merely added. Descriptive historical-sentinel recovery was A `3/4`, D `7/7`, X `3/5`, N4 `5/7`; D recovered six sentinel families in all 6/6 samples and the seventh in 5/6. These are contract-parity references, not semantic Gold.

Support binding itself can be stable for concrete evidence. N4 `REINFORCE(BT1)` occurred 6/6 and bound exactly to `neu-002` in 6/6; N4 `REINFORCE(Q1)` also had one support signature in 6/6. X `CHALLENGE(BT1)` occurred 6/6 with one support signature in 6/6. A/D support signatures were materially more diffuse, exposing rather than hiding the weaker relation-to-evidence alignment of several historical relations.

No exact duplicate relation identities survived normalization in this run. Multiple OPEN_NEW effects may still coexist when they have distinct support signatures; this is consistent with the established branch-identity rule.

## Interpretation

10D.6F's A/D empty-effect collapse was not caused by support provenance as such. Explicit `support_unit_ids` and jurisdiction anchors can coexist with the historical native relation topology. The 10D.6F collapse is therefore attributed primarily to its stricter rewritten semantic contract / schema combination rather than to provenance binding alone.

This result also strengthens the case for canonical grounding after Relation Mapping: support IDs expose which exact audited units supposedly justify a relation, while deterministic legality already blocks location nodes from becoming cognitive targets. Historical frequency remains distinct from semantic correctness; A/D contain several frequent but scope-questionable relations that future grounding must evaluate rather than preserve blindly.

## Decision

Preserve relation-level `support_unit_ids` / `jurisdiction_anchor_ids` in the vNext direction. Do not promote the historical native semantics unchanged. Next isolate whether removing the three compatibility cardinal effect fields itself changes topology while keeping native semantics and provenance otherwise fixed.

Next gate: **Phase 10D.6H — Cardinal-Field Removal Parity Shadow**. Production defaults remain unchanged; Phase 9A remains paused.
