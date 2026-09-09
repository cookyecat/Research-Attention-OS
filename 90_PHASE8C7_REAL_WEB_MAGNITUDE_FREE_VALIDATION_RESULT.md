# Phase 8C.7 — Real-Web Magnitude-Free Validation Result

Status: EXPERIMENTALLY COMPLETE
Date: 2026-09-10

## Question

Does the Phase 8C.6 magnitude-free robustness result generalize beyond RS05/RS15/RS11/RS12 to exact real public-web sources, while keeping perception instability separate from calibration instability?

The experiment intentionally asks two different questions:

1. can the current Sensor/Auditor/native-cognition path form plausible real-web Semantic Topology;
2. once that topology is frozen, does raw LLM `change_magnitude` retain undesirable authority over Attention?

No new cognitive gold labels were invented for the four web articles, so Attention changes are stability/behavior evidence, not automatic correctness claims.

## Exact sources and continuity gate

The four Phase 8C.1 URLs were reacquired through the production URLConnector. All four matched the frozen production-normalized content hash and extracted character count before any model call:

- A — Microsoft Azure GPT-6 Astra GA;
- C — OpenAI Deployment Safety Astra Vision;
- D — The Verge Astra release;
- X — Google Research AgentHands control for the Astra event relation.
## Fresh native real-web pass

Measurement SHA:

`d49cef927f8edc877447d5869d04266244af64ef`

Artifact:

`eval/live/results/phase8c7_real_web_magnitude_free_validation_v0_1/phase8c7_real_web_magnitude_free_validation_v0.1_20260909T185631Z.json`

SHA256:

`db24df43e836f91cd76767b838e21af67a377b61d69a5801bbb5c6695a135ae1`

The fresh path was:

```text
URLConnector
→ Sensor v0.2.6
→ Auditor v0.1.1
→ canonical admitted semantic units
→ native Locate
→ native multi-effect Cognitive Impact
→ Pareto
→ Raw Cardinal vs Magnitude-Free
```

No legacy bridge / `ExtractionResult` was used as the cognitive interface.
Fresh one-pass results:

| Source | Audited units | Native CognitiveEffect topology | Raw Cardinal | Magnitude-Free |
|---|---:|---|---|---|
| A Azure | 14 | CHALLENGE(B1), REINFORCE(BT1/M1/Q1) | AWARE | AWARE |
| C OpenAI Safety | 16 | empty | DROP | DROP |
| D The Verge | 19 | empty | DROP | DROP |
| X AgentHands | 14 | CHALLENGE(Q1), REINFORCE(B1/BT1/M1) | AWARE | AWARE |

The original magnitude values happened not to cross policy boundaries in these four fresh realizations. Therefore this pass alone cannot establish a robustness advantage for Magnitude-Free.

It does establish two useful controls:

- large admitted information volume does not automatically imply a CognitiveEffect or Attention allocation;
- removing magnitude does not automatically promote real-web articles to WATCH/ENGAGE.

## Operational amendment

The preregistered `4 sources × 3 fresh perception repeats` was stopped before artifact creation because one fresh real-web realization expanded into roughly 15 admitted semantic units and many serial Auditor calls. The amendment was recorded before the bounded measurement at commit:

`d49cef927f8edc877447d5869d04266244af64ef`

The excluded partial stdout is not measurement evidence. Source diversity was retained as four distinct real-web sources; calibration robustness was expanded deterministically after freezing each real-web topology.
## Frozen real-web magnitude perturbation

Measurement SHA:

`a51ed707db15ee9772e51baf55adae631e3538f0`

Artifact:

`eval/live/results/phase8c7_real_web_magnitude_perturbation_v0_1/phase8c7_real_web_magnitude_perturbation_v0.1_20260909T192105Z.json`

SHA256:

`9a979fcda399137d302b5cd91ba97ff65acb0c65dcd432576991d81286e78636`

The exact fresh real-web CognitiveEffects were frozen. Four deterministic magnitude variants were applied without any LLM call:

```text
original
all_low  = .01
all_high = .99
inverse  = 1 - original
```

Operation, target, epistemic strength, importance, Kernel, Locate/matches, Pareto aggregation and runtime were unchanged. Only raw `change_magnitude` was altered.
Perturbation result:

| Source | Effects | Raw Cardinal under perturbation | Magnitude-Free under perturbation |
|---|---:|---|---|
| A Azure | 4 | AWARE ×2, ENGAGE ×2 | AWARE ×4 |
| C OpenAI Safety | 0 | DROP ×4 | DROP ×4 |
| D The Verge | 0 | DROP ×4 | DROP ×4 |
| X AgentHands | 4 | AWARE ×2, ENGAGE ×2 | AWARE ×4 |

Thus the two non-empty real-web topologies both reproduced the same failure mode:

```text
fixed Semantic Topology
+ changed raw magnitude only
→ Raw Cardinal crosses Attention tier
→ Magnitude-Free does not move
```

The two empty-topology controls remained DROP under both strategies for all variants.

Formally, on the real-web effects-bearing sources:

```text
RawCardinalInvariant = 0/2 sources
MagnitudeFreeInvariant = 2/2 sources
```

Across all four sources, Magnitude-Free article decisions were invariant under every magnitude perturbation.
## Interpretation

Phase 8C.7 generalizes the Phase 8C.6 calibration finding from canonical fixtures to exact public-web sources:

> Raw pseudo-cardinal magnitude is sufficient by itself to create an artificial Attention boundary even when Semantic Topology is frozen.

Magnitude-Free removes that particular authority cleanly. It does **not** prove that Magnitude-Free Attention is always correct, nor that all remaining instability is solved.

The current decomposition is therefore:

```text
Semantic Topology instability
  → perception / cognitive-relation realization problem

Magnitude instability with fixed topology
  → calibration / decision-boundary problem
```

These are separate causal layers and should not be repaired with the same intervention.

A non-measurement pilot observation before the operational amendment produced a different Azure effect set than the bounded formal run. Because that pilot produced no accepted artifact, it is excluded from evidence, but it motivates a future dedicated Semantic Topology stability experiment rather than further magnitude tuning.

## Decision

- Keep `one-delta-v1` as the production default.
- Freeze `pareto-multidelta-magnitude-free-v0.1` as an experimental research baseline.
- Do not restore raw LLM `change_magnitude` as decision authority merely to recover a scalar score.
- Do not invent a new continuous magnitude formula yet.
- Next research target is Semantic Topology stability / decision-bearing relation preservation in the perception-to-cognition path, with magnitude-free calibration held fixed where useful.

Phase 8C.7 is experimentally complete. No production promotion is authorized by this experiment alone.
## Regression

Full backend regression after measurement/documentation:

```text
576 passed
63 skipped
1 failed
1 warning
```

The sole failure is the pre-existing Case K urgency residual:

```text
expected PREEMPT
actual   PRIORITY
```

No new regression was introduced by Phase 8C.7 measurement code or the magnitude-free experimental path.
