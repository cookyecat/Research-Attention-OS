# Phase 8C.5 — Pareto / Partial-Order Decision Strategy Preregistration

Status: PREREGISTERED / EXPERIMENTAL CHIP
Date: 2026-09-10

## Question

Can RAOS avoid lossy one-winner compression by preserving a partial order over decision-bearing CognitiveEffects, while keeping the frozen one-Delta production strategy available for controlled A/B?

This experiment does **not** claim to solve raw `change_magnitude` calibration. It isolates decision geometry first.

## Frozen inputs

- Sensor / Auditor semantics unchanged.
- CognitiveEffect schema unchanged.
- Existing production grounding/caps unchanged.
- Existing Attention thresholds unchanged.
- Production default remains `one-delta-v1`.

Candidate chip:

```text
strategy_id = pareto-multidelta
version     = pareto-multidelta-v0.1
```
## Ordinal decision vector

Each legal positive effect is mapped to a coarse vector rather than a scalar weighted sum:

```text
(change_band, epistemic_band, importance_band, is_challenge, is_open_new)
```

Bands reuse already-frozen boundaries only:

```text
change_band:
  0 = zero / no positive Delta
  1 = 0 < m < 0.35
  2 = 0.35 <= m < 0.55
  3 = m >= 0.55

epistemic_band:
  0 = e < 0.45
  1 = e >= 0.45

importance_band:
  0 = I < 0.55
  1 = I >= 0.55
```

No new 0.01-level arithmetic is introduced. The bands are not claimed to be final calibration; they are a controlled ordinalization of the existing policy boundaries.
## Partial order

Effect `a` dominates effect `b` only if every decision axis is no worse and at least one is strictly better.

`CHALLENGE` and `OPEN_NEW` are separate binary axes. Therefore they are naturally incomparable with each other, and a plain REINFORCE cannot erase either solely by having a larger scalar score.

The complete CognitiveEffect set is never deleted. Pareto filtering applies only to the **Attention competition frontier**.

Per-frontier effect Attention still uses the existing production policy semantics. Article disposition is the join over channel dispositions:

```text
DROP < AWARE < WATCH < ENGAGE
article_attention = max(channel_attention)
```

If multiple frontier channels share the winning disposition, a single representative effect may still be used only for the legacy public update/artifact compatibility projection. It must not be interpreted as the sole cognitive meaning of the article.

## Hypotheses

H1: RS15-like multi-effect sources preserve simultaneous Q2/B2-style channels rather than oscillating solely because of `argmax(magnitude * importance)`.

H2: strong unambiguous RS05-like CHALLENGE remains ENGAGE.

H3: weak incidental RS11-like relations do not gain Attention merely because there are many of them.

H4: remaining instability after Pareto selection is attributed to calibration / threshold crossing, not silently blamed on topology.
