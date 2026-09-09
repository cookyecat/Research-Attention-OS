# Phase 8C.2 — Decision Stability Attribution Result

Status: **ATTRIBUTED / PHASE 8C.2 REMAINS ACTIVE / PRODUCTION PROMOTION BLOCKED**  
Date: 2026-09-09

## 1. Question

After the bridge v0.2 repair, Tier-2 real-world continuity passed, but a fresh Tier-1 RS15 rerun produced a stable-looking `REINFORCE(B2)` divergence instead of the Phase 7A canonical `REINFORCE(Q2)` landing.

The attribution question was therefore:

> Is RS15 a deterministic bridge regression, an event-projection duplication effect, a Sensor/Auditor representation failure, or a downstream decision-boundary instability?

No Sensor prompt, Auditor prompt, Delta semantics, Attention Policy semantics, or production default was changed during this attribution series.

## 2. Frozen semantic baseline

The Phase 7A working formulation remains unchanged:

$$
\boxed{
\text{Decision-Sufficient Semantic Precision}
=
\text{Evidence Fidelity}
+
\text{Scope Fidelity}
+
\text{Relational Fidelity}
}
$$

This attribution does **not** provide evidence sufficient to replace or extend that formulation. Stability is treated here as a production measurement property of a stochastic implementation, not as a fourth semantic-fidelity term.
## 3. Event projection ablation

Exact measurement SHA: `ea710ff7d5d387425f90d1005bfe4f93a6e5c272`

Artifact: `eval/live/results/phase8c2_rs15_event_projection_ablation_v0_1/phase8c2_rs15_event_projection_ablation_v0.1_20260909T080250Z.json`  
SHA256: `def0b2a986b2b8d4d74608c0100803216be656cb440e5ec6f999845b28afa28a`

One Sensor/Auditor realization was frozen and reused downstream:

```text
N  audited non-event only       -> B2, B2, Q2
E  audited event only           -> NONE, NONE, NONE
EN audited event + non-event    -> B2, B2, B2
```

Therefore event projection can perturb or stabilize a nearby landing, but it is not the sole RS15 cause: removing event projection does not restore stable Q2.

The stronger hypothesis

```text
semantic duplication -> deterministic Q2-to-B2 flip
```

is **not supported** by this evidence.

## 4. Historical Phase 7A semantics vs current semantics

Exact measurement SHA: `e65560b80f533315bd27fd144864fb9e872cb901`

Artifact SHA256: `82289dc92b947bbb8cd9c03fabb65a1b9ce7731549133db55b3d34d36d5ee99b`

Under the same current downstream:

```text
Phase 7A HIST7 target: Q2 6/6
Current frozen non-event: B2 4/6, Q2 2/6
```

Thus current representation composition materially changes the RS15 decision margin. Pure historical-vs-current downstream drift is not sufficient to explain the divergence.
## 5. Sensor model probe and repeated Flash realizations

A one-pair Sensor-model-only probe did not support a simple `Flash weak -> B2 / Pro strong -> Q2` explanation:

```text
Pro   -> B2 / WATCH
Flash -> Q2 / ENGAGE
```

Artifact SHA256: `73a374762a09cb449f54aff5148afc753374daf6b90eafb8d3c91beeb5366809`.

The stronger stability measurement then held source, Sensor v0.2.6 prompt, Flash model, Auditor version, Kernel fixture, and downstream code fixed while allowing six independent Sensor realizations.

Measurement SHA: `9ab0a57f22743807534efbcb676e69d6ba68386a`  
Artifact SHA256: `207878ba7fe23758cb0a8009e38f52b9d38452cc72e0f52d35a44a121d202490`

Observed:

```text
unique Sensor semantic realizations   6 / 6
unique audited semantic realizations  6 / 6

Sensor pre-audit targets:
Q2 3, B2 2, OPEN_NEW 1

Audited non-event targets:
Q2 2, B2 3, OPEN_NEW 1

Audited event+non-event targets:
Q2 2, B2 2, OPEN_NEW 2
```

Therefore the same v0.2.6 semantic contract does not currently yield a stable realized semantic basis on RS15. Sensor realization variance is real; Auditor and event projection can further perturb the final represented world.
## 6. Fixed-Sensor Auditor/downstream isolation

Measurement SHA: `978e93858fc7ef20b482099a73dd2dc5b132a2e8`  
Artifact SHA256: `329887451fdf4c3f7f70bd5c4a8a03be44a25942bd2d6ea2f30b3dd88d1157e9`

A single 11-unit Sensor realization was frozen.

First, with **no new Sensor or Auditor call**, the exact same pre-audit semantic world was sent through current downstream six times:

```text
Q2 3/6
B2 3/6
```

This establishes a genuine RS15 downstream decision-boundary oscillation:

$$
\boxed{
\text{same semantic input} \not\Rightarrow \text{stable RS15 target}
}
$$

Next, the same frozen Sensor output was audited six times. Auditor produced only two admitted semantic worlds: five runs admitted the same 7-unit hash and one admitted an 8-unit variant.

Across 12 downstream runs of those audited worlds:

```text
B2 10/12
Q2  2/12
```

The critical Q2 relation — shared physical world as coordination interface, reducing dependence on explicit communication/unified scheduling — remained admitted in every 7/8-unit world. Therefore this is **not** an Auditor deletion of Q2. The filtering changes the relative semantic composition/margin while preserving the Q2 predicate itself.

Auditor admission stochasticity exists, but on this realization it is smaller than Sensor realization variance and sits on top of an already unstable downstream boundary.
## 7. Cross-case stability controls

To avoid treating one RS15 case as population-level evidence, RS05 and RS11 were each rerun six times through fresh current Sensor + Auditor + production downstream.

Measurement SHA: `49e3f494f395af87cb73293b0968ab3e24abc7f3`  
Artifact SHA256: `215e7fe1d2895478ef7c71835cb297137555d95ef0edbb3c068ce599584fc3ed`

```text
RS05:
canonical CHALLENGE(CF-B-PERF) / ENGAGE  3/6
NONE / DROP                               3/6

RS11:
NONE / DROP                               6/6
```

Therefore instability is neither universal nor unique to RS15. RS11 is a robust decision region under substantial representation/admission variation; RS05 is also unstable in the fresh end-to-end path.

A final RS05 attribution froze the exact four Auditor-admitted Phase 7A canonical units and repeated only the current downstream.

Measurement SHA: `e5b680e2929e1f8005ee28c0385801dce7ca7b09`  
Artifact SHA256: `9017b5fe43504177c53561137994ca509cdc0f9c8c760d26bbd83b316765c79d`

Result:

```text
CHALLENGE(CF-B-PERF) / ENGAGE  6/6
```

So RS05 does **not** show the same downstream-boundary instability as RS15. Its fresh 3/6 regression is primarily attributable upstream to realized Sensor/Auditor representation rather than to a stochastic decision boundary.
## 8. Causal interpretation

The observed cases now separate into three regimes:

```text
RS11 — robust basin
  representation varies
  decision remains NONE / DROP

RS05 — upstream representation instability
  Phase 7A frozen semantics -> canonical decision 6/6
  fresh Sensor/Auditor path -> canonical 3/6, DROP 3/6

RS15 — compound boundary amplification
  Sensor realization varies
  Auditor admission varies
  event projection can perturb the margin
  exact same semantic input still flips Q2/B2 3/6 vs 3/6
```

Therefore the original Tier-1 `B2 3/3` observation should not be interpreted as a deterministic bridge-specific regression. It is evidence that the candidate path is not production-stable on a decision-bearing boundary, but attribution spans multiple stochastic layers.

The most accurate current statement is:

$$
\boxed{
\text{Representation Variance}
\times
\text{Decision Sensitivity}
\rightarrow
\text{Landing Instability}
}
$$

This is an engineering/product-readiness finding, not a replacement for the Phase 7A semantic formula and not evidence for changing frozen Delta or Attention semantics.

## 9. Statistical scope

These measurements establish **existence and causal mechanism**, not open-world prevalence. Six repeats on three canonical cases cannot estimate how often arbitrary future articles will be unstable.

What is supported:

- a fixed semantic input can oscillate at the RS15 Q2/B2 boundary;
- fresh semantic realization/admission can destabilize RS05 even when its frozen canonical semantics are downstream-stable;
- some decisions such as RS11 remain robust despite upstream variation.

What is not supported:

- a population instability rate;
- a universal claim that event projection or semantic duplication is harmful;
- a universal claim that Flash is worse than Pro;
- a change to the 7A fidelity formulation.
## 10. Production decision

Phase 8C.2 remains **ACTIVE** and the production default remains legacy.

Do not tune Sensor v0.2.6, Auditor v0.1.1, Delta, or Attention Policy from RS15 alone. The immediate engineering requirement is a broader **decision-stability / representation-robustness gate** over multiple canonical decision-bearing and negative-control cases.

This gate should measure repeated realizations rather than certify a candidate from one stochastic pass. It should preserve the existing Phase 7A semantics and answer a narrower production question:

> When multiple admissible representations preserve Evidence, Scope, and Relational Fidelity, does the downstream decision remain sufficiently stable for the intended attention action?

Probabilistic redesign of Delta/Attention remains deferred to Phase 10 unless broader evidence proves that boundary uncertainty must become a first-class runtime semantic.

## 11. Regression

After all measurement-only runners were added, the broader exact-current regression passed:

```text
72 passed, 1 deselected, 1 warning
```

The deselected Case K residual remains pre-existing and outside Phase 8C.2 causality.

## 12. Product-level interpretation — cognitive target vs Attention action

The constitutional invariant `CognitiveChange != AttentionAction` matters directly in these results.

For the six fresh RS15 full candidate-path realizations (`AUDITED_EVENT_PLUS_NON`):

```text
cognitive target: Q2 2, B2 2, OPEN_NEW 2
Attention action: WATCH 6/6
```

So RS15 is clearly unstable at the cognitive landing/target level, but the full current candidate path is stable at the coarse Attention-allocation level in this six-run measurement. This makes RS15 a valuable boundary diagnostic without proving a catastrophic attention-allocation failure.

RS05 is more serious for the product objective:

```text
fresh current path:
ENGAGE 3/6
DROP   3/6

frozen Phase7A semantics:
ENGAGE 6/6
```

RS11 remains `DROP 6/6`.

Therefore the production-readiness gate must report at least two distinct stability dimensions:

1. **Cognitive landing stability** — does the represented world consistently locate the same decision-bearing cognitive change?
2. **Attention allocation stability** — does stochastic variation change how much scarce human attention is requested?

For RAOS product safety, `DROP <-> ENGAGE/WATCH` oscillation is more consequential than `Q2 <-> B2` oscillation when the final Attention tier remains unchanged. False DROP / severe under-attention should therefore remain a primary promotion guardrail without changing frozen cognitive semantics.
