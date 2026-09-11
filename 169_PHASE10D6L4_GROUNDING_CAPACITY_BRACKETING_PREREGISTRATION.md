# Phase 10D.6L.4 — Grounding Capacity Bracketing Preregistration

**Status:** PREREGISTERED / NO WEAK-MODEL OUTCOME YET
**Date:** 2026-09-12

## Research question

Given a frozen semantic relation, frozen support binding, frozen target/jurisdiction, and frozen Kernel proposition, can Grounding correctly classify whether the evidence licenses that relation without changing the relation itself?

This gate explicitly separates evaluator capacity from RAOS architecture quality.

- Strong-model manual adjudication = architecture-capability upper bound.
- DeepSeek-Flash = robustness lower bound / stress test.
- A weak-model error alone is not evidence that RAOS architecture is wrong.

## Frozen input

Use the valid 10D.6L.3 artifact only:
`phase10d6l3_decoupled_support_binding_v0.1_20260911T195829Z.json`, SHA256 `67a97a323ac426693ffb96d9ff57cf7141faf8af29f73c38aafb18857d90448f`.

For each of its 28 frozen relation instances, use exactly the artifact-recorded `modal_support_signature` and `modal_anchor_signature`. No relation generation and no support rebinding occur in this gate.

Grounding input per item:
`relation + target proposition (or OPEN_NEW jurisdiction) + frozen support units + frozen jurisdiction anchors + original relation reason`.

Grounding output is one categorical class only: `DIRECT | PARTIAL | INSUFFICIENT | CONTRADICTS_OPERATION`, plus a short reason. The evaluator cannot alter operation, target, support IDs, or jurisdiction anchors.

## Class semantics

- `DIRECT`: the frozen support directly addresses the target proposition / OPEN_NEW branch at matching scope and supports the stated operation.
- `PARTIAL`: the support is genuinely relevant and directionally compatible but covers only part of the target scope or only partially licenses the operation.
- `INSUFFICIENT`: the support is topical/adjacent, based on absence of discussion, lacks required jurisdiction, or otherwise does not license the relation.
- `CONTRADICTS_OPERATION`: the supplied support points in the opposite direction from the frozen operation.

Strong-model labels and rationales must be frozen before any 10D.6L.4 Flash call. Flash then evaluates the identical frozen items in three repeated case-level batches per case with non-empty items (D/X/N4), for 9 calls total.

Primary measurements: structural success; per-item modal class and stability (>=2/3); exact modal agreement with strong reference; confusion matrix; and critical errors (`strong DIRECT -> Flash INSUFFICIENT/CONTRADICTS` or `strong INSUFFICIENT/CONTRADICTS -> Flash DIRECT`). No Attention policy or production switch is evaluated.
