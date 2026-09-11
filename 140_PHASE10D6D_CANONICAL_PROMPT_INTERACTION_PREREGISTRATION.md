# Phase 10D.6D — Canonical Input × Reconciled Prompt Interaction Preregistration

**Status:** PREREGISTERED / NO 10D.6D OUTCOMES YET  
**Date:** 2026-09-11

## Question

10D.6B showed prompt-only reconciliation fails under the flattened Impact payload; 10D.6C showed canonical input is decision-bearing but insufficient under the current production prompt. Does the combination of canonical audited input and reconciled non-argmax prompt recover richer legal Relation Mapping without critical Attention regressions?

## Controlled arms

Both arms consume the exact same Phase 10D.4 frozen audited semantic units directly, the same Kernel, modal Locate, DeepSeek Flash path, current production importance resolver, production `ground_effects`, feature projection, runtime and `pareto-multidelta-magnitude-free-anchored-open-new` strategy.

- **C0:** canonical input + current production `IMPACT_SYSTEM`.
- **C1:** canonical input + `IMPACT_SYSTEM_VNEXT`.

Only the system prompt changes. This is the interaction complement to 10D.6B/10D.6C; no `ExtractionResult` Impact payload is used as the LLM input in either arm.

Sampling: A, D, X, N4; N=6 per arm per case; interleaved C0/C1; no expansion or prompt edits.

Persist raw pre-grounding effects and grounded effects separately, then Decision-Causal Core and Article Attention.

## Evaluation

The objective is **not** exact equality with previous Phase-10 native samples. The candidate should instead satisfy semantic invariants and improve the measured failure modes:
- avoid the A/D systematic empty-effect regime seen in bridged production input;
- avoid the X `DROP 6/6` over-suppression seen in prompt-only 10D.6B P1;
- preserve N4's stable non-DROP handling;
- preserve Location != Update and production grounding legality;
- retain multiple distinct legal effects when supported rather than collapsing to one winner.

Phase-10 native maps may be shown as a non-gold reference distribution only.

No production promotion is allowed from 10D.6D alone. If C1 passes, target-importance authority still requires a separate controlled calibration before combined promotion.
