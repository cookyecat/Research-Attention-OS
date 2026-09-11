# Phase 10D.5 — Scope Audit and Replay Boundary

Status: PRE-MEASUREMENT AMENDMENT
Date: 2026-09-11

## Static code-path finding

The discovered `target_importance` authority mismatch is real, but it is not the only structural difference between Phase-10 native research cognition and the deployed production `ModelProvider` path.

Production `ModelProvider` performs, after its Impact LLM response:

1. `resolve_target_importance(...)`;
2. `ground_effects(...)` legality / epistemic-cap grounding;
3. production feature projection.

The native Phase-10 research interface uses a different canonical-unit Impact prompt and directly constructs CognitiveEffects before the frozen research decision stack.

## Formal replay scope

Phase 10D.5 v0.1 therefore makes a narrower causal claim:

> Given the exact same stored Relation-Mapping realization, does replacing the research-path LLM `target_importance` estimate with the deployed production target-importance authority preserve the Phase 10D.4 basin-persistence conclusion?

Only that authority seam changes in Arm P. `ground_effects` and production Impact prompting are not silently introduced into the same replay because doing so would change multiple causal variables at once.

The historical Arm R remains an exact replay check over topology, necessary core, sufficient supports, and article Attention.

## What 10D.5 v0.1 can establish

- whether the known importance-authority mismatch changes individual decisions;
- whether it changes the load-bearing distribution;
- whether t1/t2 Attention or load-bearing basin persistence survives this production authority rule.

## What it cannot establish

- equivalence of `native_assess` and production Impact prompts;
- equivalence of all production `ground_effects` outcomes;
- full end-to-end production decision-frequency parity.

Those require a separate fresh full-path validation because the missing production LLM realization cannot be recovered deterministically from the Phase 10D.4 artifact.

This amendment is recorded before the formal 10D.5 replay artifact is produced. The exploratory diagnostic remains excluded from formal evidence.
