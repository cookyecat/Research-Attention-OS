# Phase 10D.5 — Production Semantic Parity Audit Result

Status: COMPLETE / ATTENTION-BASIN PERSISTENCE SURVIVES TARGET-IMPORTANCE PRODUCTION AUTHORITY
Date: 2026-09-11

## Formal measurement

Measurement SHA: `e71e99f8a0450567069d5f83a557ce9dbe4dfa82`

Artifact:
`eval/live/results/phase10d5_production_semantic_parity_audit_v0_1/phase10d5_production_semantic_parity_audit_v0.1_20260911T021932Z.json`

SHA256: `e2ef93617f48e8d296e63eb6b0075b00986e764f8b46a46023837b2c0e5eb6af`

The formal corpus is exactly the 168 stored Phase 10D.4 real-web Relation-Mapping realizations from A, D, X, and N4. No acquisition, Sensor, Auditor, Locate, Relation-Mapping, or LLM call was made.

## Fail-closed historical replay

Arm R reconstructed the historical research-path CognitiveEffects and recomputed topology, Decision-Causal Core, and article Attention.

All `168/168` samples exactly reproduced:

- topology;
- `necessary_core`;
- `sufficient_supports`;
- article Attention.

Therefore the Phase 10D.4 stored artifact is internally self-consistent and the parity replay is operating on the intended historical semantics.

## Production target-importance projection

Arm P changed one variable only for targeted REINFORCE/CHALLENGE effects: stored LLM `target_importance` was replaced by production `resolve_target_importance(node, node_type, llm_estimate)` authority. OPEN_NEW retained its stored LLM estimate because it has no target node.

| Case | Historical t1 -> t2 Attention | Production-importance t1 -> t2 Attention | Attention changed R->P | Load-bearing set changed R->P |
|---|---|---|---:|---:|
| A | AWARE 4 / WATCH 14 / DROP 6 -> WATCH 8 / DROP 10 / AWARE 6 | WATCH 4 / ENGAGE 14 / DROP 6 -> ENGAGE 9 / DROP 10 / WATCH 5 | 32/48 | 32/48 |
| D | WATCH 22 / AWARE 2 -> WATCH 23 / AWARE 1 | ENGAGE 24/24 -> ENGAGE 24/24 | 48/48 | 48/48 |
| X | ENGAGE 11 / WATCH 1 -> ENGAGE 7 / WATCH 5 | ENGAGE 12/12 -> ENGAGE 9 / WATCH 3 | 3/24 | 12/24 |
| N4 | ENGAGE 15 / WATCH 9 -> ENGAGE 14 / WATCH 10 | unchanged | 0/48 | 0/48 |

The mismatch is therefore decision-bearing for A, D, and X, but not for N4.

## Basin persistence after production importance authority

| Case | Attention JSD | Attention null p95 / tail | Load-bearing JSD | Load-bearing drift? | Topology drift? |
|---|---:|---|---:|---|---|
| A | 0.03333 | 0.09711 / 0.36413 | 0.09071 | No | No |
| D | 0.00000 | 0.00000 / 1.00000 | 0.09879 | **Yes** (`p=0.03019`) | **Yes** (`p=0.04999`) |
| X | 0.13793 | 0.13793 / 0.22216 | 0.22378 | No | No |
| N4 | 0.00131 | 0.06533 / 1.00000 | 0.21897 | No | No |

Using the existing strict permutation gate (`observed > null_p95` and upper-tail `<= .05`), all four cases remain **Attention-basin compatible**. Thus the Phase 10D.4 product-level persistence result survives the discovered production target-importance authority seam: `4/4` selected real-web maps remain in the same Attention basin.

D changes at the internal causal layer. Under production importance authority, D remains `ENGAGE 24/24` at both checkpoints while its load-bearing-state distribution now shows supported drift. Its raw topology drift remains the same supported drift already observed in 10D.4 because topology identity was frozen by construction.

## Interpretation

This audit does **not** show that the historical 10D.4 Attention frequencies were the exact frequencies of the deployed production pipeline. It shows something narrower and important: the same real-web stochastic realizations, when reprojected through the deployed target-importance authority, still reproduce the same cross-checkpoint Attention basin conclusion.

The deployed dogfood system itself is not running the Phase-10 `native_assess()` harness. The production rollout changed decision-strategy selection only; the live pipeline continues to use production `ModelProvider`, including its importance authority. Therefore this finding is a research-to-production transfer boundary, not a newly introduced live production bug.

The stronger historical D claim that both load-bearing and Attention basins were stable does **not** survive this projection. For D, only the final Attention basin remains stable; internal load-bearing and topology drift are supported.

This strengthens the need to keep the three stability layers separate: Topology Stability, Load-Bearing Stability, and Attention Stability.

## Remaining parity boundary

Phase 10D.5 v0.1 does not establish full equivalence between the research `native_assess()` path and production `ModelProvider`. Static code audit found two additional differences that cannot be honestly collapsed into this one-variable replay:

- the production Impact prompt is not the native canonical-unit Impact prompt;
- production applies `ground_effects(...)` legality / epistemic-cap grounding after raw model output.

A full production-path distribution validation would therefore require fresh production-path Impact realizations under frozen real-web perception / Locate, rather than deterministic reinterpretation of old native outputs.

## Regression

Focused Phase 10D.5 / probability-distance contracts: `12 passed / 1 warning` before formal measurement.

Full backend regression after the audit: `620 passed / 63 skipped / 1 failed / 1 warning`. The sole failure remains the historical Case K `PREEMPT` expected vs `PRIORITY` actual residual; no new regression was introduced.

## Decision

Phase 10D.5 closes the known target-importance authority seam. Keep Phase 10D.4 as valid evidence for distributional structural stability, but narrow transfer language: its exact historical Attention frequencies belong to the native research path, while its `4/4` Attention-basin persistence conclusion survives production importance authority replay.
