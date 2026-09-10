# Phase 8C.12 — Locate vs Relation Mapping Longitudinal Attribution Result

**Status:** EXPERIMENTALLY COMPLETE  
**Measurement SHA:** `8180972ed3d5780767e686cf7a0f35681644ed56`  
**Artifact:** `eval/live/results/phase8c12_locate_relation_longitudinal_v0_1/phase8c12_locate_relation_longitudinal_v0.1_20260910T072032Z.json`  
**SHA256:** `a67d7e40e403c7ad9bd7dd6a82312fd5c720ada0f2bf683b506475eb3d92e8be`

## Controlled question

With the exact Phase 8C.8 audited semantic world and Kernel frozen, did longitudinal drift enter through Locate (`L`) or Relation Mapping (`R`)? Gate 12A re-ran Locate. Gate 12B reconstructed and froze the exact historical modal Locate fixture and re-ran only Relation Mapping / Impact.

## Results

| Case | Locate modal target Jaccard | Locate modal detail Jaccard | Relation modal Jaccard | Historical Attention | Current Attention |
|---|---:|---:|---:|---|---|
| RS05 | 1.00 | 0.50 | 1.00 | ENGAGE 6/6 | ENGAGE 6/6 |
| RS15 | 0.90 | 0.545 | 0.30 | WATCH 6/6 | ENGAGE 4/6, WATCH 2/6 |
| RS11 | 1.00 | 0.429 | 0.50 | AWARE 6/6 | WATCH 6/6 |
| RS12 | 1.00 | 0.667 | 0.375 | WATCH 6/6 | WATCH 6/6 |

## Attribution

RS05 is a stable positive control. Its Locate target set is invariant; `CHALLENGE(CF-B-PERF)` remains 6/6 and Article Attention remains ENGAGE.

RS15 retains critical `REINFORCE(Q2)` and `REINFORCE(B2)` at 6/6, but with historical Locate frozen the current Relation Mapping adds a new challenge/open-new regime. Therefore the historical WATCH basin to current WATCH/ENGAGE mixture cannot be attributed to Sensor, Auditor, or current Locate. The principal measured residual enters at Relation Mapping.

RS11 likewise keeps essentially the same Locate target basin, yet under exact historical Locate the current Relation Mapping moves historical AWARE 6/6 to WATCH 6/6. This is direct longitudinal evidence at the R stage.

RS12 demonstrates the complementary regime: Relation topology changes strongly, but Article Attention remains WATCH 6/6. Topology drift is therefore not equivalent to product-level instability.

## Important metric boundary

Locate target-set stability is materially higher than Locate relevance-type/detail stability. `TOPIC/EVIDENCE/STRUCTURAL/...` labels can drift while the same Kernel jurisdictions remain present. Jaccard remains a representation-level similarity measure only; it is not a decision metric.

## Decision

Phase 8C.12 closes with Relation Mapping as the primary current longitudinal residual. No downstream policy is changed. Proceed to Phase 8C.13 Decision-Causal Core: identify which current relations are load-bearing for the frozen Attention policy, rather than attempting to stabilize every topology edge.
