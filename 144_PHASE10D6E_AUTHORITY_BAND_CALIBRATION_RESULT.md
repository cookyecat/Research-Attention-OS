# Phase 10D.6E — Authority Band Calibration Result

**Status:** CLOSED / C1 DIRECTION SUPPORTED / EPISTEMIC POLICY INCOMPLETE / NO PRODUCTION PROMOTION

## Frozen measurement

Measurement SHA: `c69e163`

Artifact:
`eval/live/results/phase10d6e_authority_band_calibration_v0_1/phase10d6e_authority_band_calibration_v0.1_20260911T060409Z.json`

SHA256: `c41db5070b79a030efb84213d2e1b66d2729f873b0285340638b13c331105ad2`

The candidate policies were frozen before outcome replay in `143_PHASE10D6E_AUTHORITY_POLICY_CANDIDATES.md`. No LLM, acquisition, Sensor, Auditor, Locate, Relation Mapping, or grounding call was made. The exact 168 stored Phase 10D.4 semantic realizations were replayed.

Two fail-closed instrument checks passed before candidate interpretation:

1. `NATIVE_RAW` reproduced all 168 historical Phase 10D.4 outputs exactly.
2. `PRODUCTION_IMPORTANCE` reproduced all 168 Phase 10D.5 production-importance projections exactly.

## Results

| Case | Native | Production importance | C1 conservative authority | C2 Auditor-trust upper bound |
|---|---|---|---|---|
| A t1 | AWARE 4 / WATCH 14 / DROP 6 | WATCH 4 / ENGAGE 14 / DROP 6 | WATCH 18 / DROP 6 | ENGAGE 17 / WATCH 1 / DROP 6 |
| A t2 | WATCH 8 / AWARE 6 / DROP 10 | ENGAGE 9 / WATCH 5 / DROP 10 | WATCH 14 / DROP 10 | ENGAGE 12 / WATCH 2 / DROP 10 |
| D t1 | WATCH 22 / AWARE 2 | ENGAGE 24 | WATCH 24 | WATCH 22 / ENGAGE 2 |
| D t2 | WATCH 23 / AWARE 1 | ENGAGE 24 | WATCH 24 | WATCH 15 / ENGAGE 9 |
| X t1 | ENGAGE 11 / WATCH 1 | ENGAGE 12 | WATCH 12 | ENGAGE 12 |
| X t2 | ENGAGE 7 / WATCH 5 | ENGAGE 9 / WATCH 3 | WATCH 12 | ENGAGE 12 |
| N4 t1 | ENGAGE 15 / WATCH 9 | ENGAGE 15 / WATCH 9 | WATCH 24 | ENGAGE 13 / WATCH 11 |
| N4 t2 | ENGAGE 14 / WATCH 10 | ENGAGE 14 / WATCH 10 | WATCH 24 | ENGAGE 13 / WATCH 11 |

C1 changed 60/168 decisions relative to the historical native projection, but introduced **zero new DROP and zero new ENGAGE**. C2 changed 54/168 and introduced **46 new ENGAGE**, so C2 is rejected as a promotion candidate.

C1 retained null-compatible Attention basins in all four real-web cases. C2 produced a supported Attention-basin shift on D (`JSD=0.09243`, tail probability `0.03599`), which is additional evidence that treating every Auditor-admitted relation as epistemically sufficient is too aggressive.

## Interpretation

The C1 importance direction is promising: explicit Kernel/user importance remains authoritative, active QUESTION/BOTTLENECK/DECISION roles can carry high responsibility, and ordinary BELIEF/MODEL nodes no longer become automatically HIGH merely because fixed type priors sit above the 0.55 threshold. This removes the production-importance ENGAGE inflation visible in A and D without creating new DROP.

The C1 epistemic rule is too coarse. It treats a targeted relation grounded in a single `SOURCE_CLAIM` source as WEAK unless there is direct observation or independent corroboration. That collapses N4 from a persistent ENGAGE/WATCH basin to WATCH 24/24.

This is not evidence that N4 should be hard-coded as strong. It exposes a representation problem: the current canonical epistemic-status vocabulary uses `SOURCE_CLAIM` for very different evidence classes. The same label covers product announcements and media reports, but also primary technical reports containing explicit experiments and measurements. The RS05 reference representation likewise labels concrete profiler measurements such as the 64x64 CPU/CUDA timing evidence as `SOURCE_CLAIM`.

Therefore:

> `SOURCE_CLAIM` is an attribution category, not a sufficient epistemic-authority category for Attention.

The next policy must bind each CognitiveEffect to the exact supporting semantic units and derive epistemic authority from a categorical evidence role / provenance contract rather than from LLM decimals, source count alone, or publisher-domain heuristics.

## Decision

- **Reject C2** as over-attending.
- **Do not promote C1** unchanged; its importance design is retained as the leading direction, while its epistemic mapping remains provisional.
- Do not restore LLM `epistemic_strength` or `target_importance` as decision authority.
- Do not hard-code publisher/domain rules to recover N4.
- Next gate: **Phase 10D.6F — Effect Support Binding / Evidence-Class Authority**.
- Production default remains unchanged. Phase 9A remains paused.
