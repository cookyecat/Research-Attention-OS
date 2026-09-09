# Phase 8C.6 — Magnitude-Free Calibration Result

Status: EXPERIMENTALLY COMPLETE / NOT PRODUCTION DEFAULT
Date: 2026-09-10

## Question

Can RAOS remove raw LLM `change_magnitude` from decision authority while preserving useful Attention behavior under the Pareto Multi-Delta strategy?

The experiment freezes Semantic topology, operation/target, epistemic strength, target importance, Kernel fixture, matches, runtime and Pareto aggregation. The only changed variable is whether raw `change_magnitude` participates in decision geometry / routing.

## Implementation

Experimental calibration chip:

```text
calibration_id = magnitude-free
version        = magnitude-free-v0.1
strategy       = pareto-multidelta-magnitude-free-v0.1
```

Raw magnitude remains serialized for compatibility/debug but has zero authority over Pareto dominance, per-channel Attention, article Attention or compatibility-representative selection.

Implementation baseline: `9fbd8e31e4fff484d123c51c5c22063900a2dee4`.
Residual representative leakage removed at: `cc03c5010d71ea580838b5e141545ce5ac3e2837`.

## Experiment A — synthetic magnitude perturbation invariance

Measurement SHA: `2fdc362b413be4dde0e924b28847c0bc3169f4f3`.

Frozen Phase 8C.3 CognitiveEffects were replayed under four magnitude variants:

```text
original
all_low    = 0.01
all_high   = 0.99
complement = 1 - original (clamped to 0.01..0.99)
```

All operation/target/epistemic/importance/Kernel/matches/runtime values were unchanged.

Result across RS05 / RS15 / RS11 / RS12, 3 realizations each:

```text
Magnitude-Free article decision invariant: 12/12
Magnitude-Free Pareto frontier invariant:  12/12
Raw-Cardinal article decision changed:      12/12
```

Artifact:
`eval/live/results/phase8c6_magnitude_perturbation_invariance_v0_1/phase8c6_magnitude_perturbation_invariance_v0.1_20260909T181449Z.json`

SHA256: `73edc2fe83ce6cecd1342933df841a3a004a13a3437a87e63715f3ccbdad5152`.

## Experiment B — frozen real-realization A/B

Measurement SHA: `2fdc362b413be4dde0e924b28847c0bc3169f4f3`.

| Case | Pareto + Raw Cardinal | Pareto + Magnitude-Free |
|---|---|---|
| RS05 | ENGAGE 3/3 | ENGAGE 3/3 |
| RS15 | AWARE 2/3, ENGAGE 1/3 | WATCH 3/3 |
| RS11 | AWARE 3/3 | AWARE 3/3 |
| RS12 | AWARE 3/3 | WATCH 3/3 |

Artifact:
`eval/live/results/phase8c6_magnitude_free_calibration_ab_v0_1/phase8c6_magnitude_free_calibration_ab_v0.1_20260909T181522Z.json`

SHA256: `2f8a2e8b0a432c32507e307579388d5da75cffdd079db4519fb2e4dbda8ba17a`.

## Interpretation

The controlled perturbation establishes that `magnitude-free-v0.1` truly removes raw `change_magnitude` from decision authority; this is not merely coarse bucketing of the same float.

RS15 is the strongest positive signal. Its previously unstable raw-cardinal Attention (`AWARE/AWARE/ENGAGE`) becomes `WATCH 3/3` while preserving the same source-side Semantic topology. This supports the hypothesis that a substantial part of RS15 Attention instability was induced by uncalibrated pseudo-cardinal magnitude crossing hard thresholds.

RS05 remains a strong robust-basin control: important, sufficiently supported CHALLENGE remains `ENGAGE 3/3` without needing magnitude.

RS11 remains `AWARE 3/3`, so removing magnitude does not automatically promote weak low-importance CHALLENGE noise.

RS12 moves from `AWARE` to `WATCH` 3/3. This is not yet labeled improvement or regression. It is the current boundary case for deciding whether Magnitude-Free v0.1 is too permissive for active Question/Bottleneck reinforcement or whether raw magnitude was causing under-attention.

## Bounded conclusions

Supported:

- Raw LLM `change_magnitude` is a high-sensitivity control variable under the current cardinal policy.
- Magnitude-Free v0.1 can make Attention strictly invariant to arbitrary magnitude perturbation while retaining decision-relevant structure.
- RS15 stability improves from a three-tier-boundary oscillation to one stable tier without damaging RS05 or RS11 in this small canonical set.
- Continuous magnitude is not currently proven necessary for RAOS Attention allocation.

Not supported yet:

- Removing magnitude universally improves open-world accuracy.
- RS12 should definitively be WATCH rather than AWARE/DROP.
- Epistemic strength / target importance are already perfectly calibrated; they remain separate future calibration questions.
- Magnitude-Free v0.1 should replace production `one-delta-v1`.

Production default remains unchanged. The next evidence gate should broaden cases and, if Magnitude-Free lacks discrimination, test an ordinal Kernel-Transition / margin chip before reintroducing any continuous magnitude.
