# Phase 10C — Temporal Regime Classifier Result

Status: COMPLETE / PERSISTENT REGIME PATTERNS DETECTED

## Artifact

- `eval/live/results/phase10c_temporal_regime_classifier_v0_1/phase10c_temporal_regime_classifier_v0.1_20260910T084415Z.json`
- SHA256: `562d33372dfd92fa9d829e724049f313b6450fcee4a3eeccf97ee61d787d5bcf`

The classifier consumes only the three null-calibrated pairwise drift booleans for `t0↔t1`, `t0↔t2`, and `t1↔t2`. No LLM calls and no stochastic-process model are used.

## Regime result

| Case | Attention | Load-bearing | Topology |
|---|---|---|---|
| RS05 | STABLE | INDETERMINATE | STABLE |
| RS15 | **PERSISTENT_SHIFT** | **PERSISTENT_SHIFT** | **PERSISTENT_SHIFT** |
| RS11 | **PERSISTENT_SHIFT** | **PERSISTENT_SHIFT** | **PERSISTENT_SHIFT** |
| RS12 | STABLE | **PERSISTENT_SHIFT** | **PERSISTENT_SHIFT** |

`PERSISTENT_SHIFT` is the pattern `[1,1,0]`: the historical checkpoint differs from both later checkpoints, while the two later checkpoints are mutually compatible under permutation-null calibration.

RS15 and RS11 therefore provide the first three-checkpoint evidence for a persistent system-level cognitive regime transition that reaches the final Attention distribution. RS12 provides the complementary robustness case: internal topology and load-bearing regime shift persist, while the Attention regime remains stable. RS05 does not support a persistent load-bearing shift; the earlier isolated load-bearing difference is classified INDETERMINATE rather than narrated as a basin transition.

## Theoretical status

These results strengthen the **Cognitive Basin / Distributional Structural Stability** model. They do not yet justify formal dynamical-attractor language or a Markov/HMM/stochastic-process fit. A formal attractor claim still lacks an explicit state-evolution law and more temporally separated checkpoints.

The next longitudinal action is to reuse the same checkpoint protocol at an independently later epoch with requested/response model identity recorded. Until then, keep the deterministic causal, static probabilistic, and temporal regime chips separate and composable. Production default remains `one-delta-v1`.
