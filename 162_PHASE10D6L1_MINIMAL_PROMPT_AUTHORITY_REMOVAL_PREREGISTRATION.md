# Phase 10D.6L.1 — Minimal Prompt Authority Removal Shadow

**Status:** PREREGISTERED / NO OUTCOME OBSERVED
**Date:** 2026-09-11

## Question
Does removing only the two downstream-policy instructions from the mature production Impact prompt preserve Relation Mapping semantics while eliminating upstream single-winner / magnitude-threshold authority?

## Frozen comparison
Cases: A / D / X / N4 from the frozen Phase 10D.4 real-web corpus. Six fresh calls per arm per case, interleaved by ordinal.

- P0: current `IMPACT_SYSTEM` (`production-impact-v2.1-legacy`).
- P1: `IMPACT_SYSTEM_PARETO_COMPAT` (`production-impact-v2.1-pareto-compat-v0.1`).

The prompts must differ only by deleting exactly these two production instructions:
1. `Set OPEN_NEW change_magnitude >= 0.55 ...`
2. `When several legal effects exist, the public update is ... change_magnitude × target_importance ...`

## Everything else frozen
Same frozen audited semantic units, same audited-units→`ExtractionResult` bridge, same modal Locate, same Kernel, same ModelProvider, same grounding/normalization, same legacy-compatible effect schema, same Anchored + Magnitude-Free + Pareto decision strategy, same runtime. Production default remains P0.

## Measurements
Per case/arm: structured-call success, legal effect count, relation-family/topology distribution, duplicate family rate, final article Attention distribution, and Decision-Causal-Core consistency. Primary safety check: P1 must not cause topology collapse, new all-empty behavior, or Attention collapse relative to P0. This gate does not promote any prompt to production.

## Follow-up only if primary shadow is interpretable
A second diagnostic may add the same support/jurisdiction provenance obligation to both prompt arms to inspect support-binding legality. That diagnostic is not allowed to retroactively change the primary gate or its sample count.

## Stop conditions
Any plumbing/schema failure is retained and excluded from cognitive interpretation. No outcome-dependent prompt edits, sample expansion, or production switch. Phase 9A and 10D.6K outcome sampling remain paused.
