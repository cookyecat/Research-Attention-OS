# Phase 8C.5 — Pareto / Partial-Order Decision Strategy Result

Status: EXPERIMENTALLY COMPLETE / NOT PRODUCTION DEFAULT
Date: 2026-09-10

## Question

Does replacing the frozen `one-delta-v1` decision geometry with `pareto-multidelta-v0.1`, while holding CognitiveEffects and all other decision inputs fixed, preserve multi-channel cognitive structure and change article-level Attention behavior?

## Exact measurement

Implementation commit:
`f9480acc54a360cdfd6b005b6b61b1eadd6126a2`

Measurement runner commit / measurement SHA:
`8d34da092c5caae20d62f5f70a03963cbe6ca415`

Canonical artifact:
`eval/live/results/phase8c5_pareto_decision_strategy_ab_v0_1/phase8c5_pareto_decision_strategy_ab_v0.1_20260909T170906Z.json`

Artifact SHA256:
`78127e5f91b9a202a279a6856e608d92ab5a3505bc53d156a415aaad0c002ba0`

## Frozen input

Source artifact:
`eval/live/results/phase8c3_native_interface_probe_v0_1/phase8c3_native_interface_probe_v0.1_20260909T135412Z.json`

Source SHA256:
`3f68c034b55fd8a132c282027f87fe3665a388ed94e8be2e653bfba6aaf55d9e`

The A/B made no LLM calls. Frozen across arms:

- native canonical CognitiveEffect realization;
- Kernel fixture / Locate matches;
- neutral runtime;
- current Attention thresholds;
- raw `change_magnitude`, `epistemic_strength`, and `target_importance` values.

Only the Decision Strategy changed:

```text
A = one-delta-v1
B = pareto-multidelta-v0.1
```

Raw native `OPEN_NEW` effects were normalized to `target=None`, matching the canonical production invariant.

## Results

Article-level Attention was unchanged in all 12 frozen runs:

```text
RS05  one-delta: ENGAGE 3/3   Pareto: ENGAGE 3/3
RS15  one-delta: AWARE 2/3, ENGAGE 1/3
      Pareto:    AWARE 2/3, ENGAGE 1/3
RS11  one-delta: AWARE 3/3    Pareto: AWARE 3/3
RS12  one-delta: AWARE 3/3    Pareto: AWARE 3/3
```

No run crossed an Attention disposition boundary solely because of Pareto selection.

Decision geometry changed materially. RS15 repeat 1 retained three REINFORCE channels on the Pareto frontier; repeat 2 retained five. The one-delta arm projected only the Q2 primary winner in both runs. In repeat 3, Q2 moved into the MAJOR change band and dominated weaker REINFORCE channels, so the Pareto frontier contracted to Q2 alone.

RS05 remained strongly ENGAGE. In one realization, CHALLENGE and several OPEN_NEW effects coexisted on the frontier because the operation axes are intentionally incomparable.

## Interpretation

The experiment supports a narrow conclusion:

$$
\boxed{\text{Pareto improves decision geometry / multi-channel preservation, not cardinal calibration.}}
$$

It removes unnecessary winner-take-all compression when several effects are incomparable or occupy the same ordinal band. It does not alter the frozen raw magnitude estimates, so RS15 still crosses the AWARE/ENGAGE boundary when its magnitude realization changes.

Therefore the remaining RS15 instability is not evidence against Multi-Delta or Pareto. It is consistent with the already identified calibration problem:

$$
\boxed{\text{stable Semantic topology} + \text{unstable pseudo-cardinal magnitude} \rightarrow \text{Attention boundary crossing}.}
$$

A design residual also appeared: weak CHALLENGE / OPEN_NEW effects can remain nondominated because operation type is an independent axis. Current Attention thresholds prevented escalation in RS11/RS12, but future calibration should distinguish material from merely legal effects before or jointly with Pareto competition.

## Limitation and next gate

This A/B intentionally used frozen Phase 8C.3 native CognitiveEffects. It is a decision-geometry experiment, not a test of full production grounding or of better magnitude estimation.

Production default remains:

```text
one-delta-v1
```

The Pareto strategy remains an experimental chip and can be inserted through the versioned Decision Strategy seam.

The next research variable should be calibration rather than further Pareto tuning. Candidate chips include ordinal/margin calibration that replaces raw 0.01-level LLM magnitude arithmetic with explicit semantic bands or distance-to-Attention-boundary judgments. Pareto can then be re-tested with calibration held fixed.

Do not tune the current Pareto frontier after seeing this result. Preserve this v0.1 as the causal baseline.
