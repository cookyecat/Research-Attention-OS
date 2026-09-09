# Phase 8C.6 — Magnitude-Free Cognitive-Effect Calibration Design

Status: PREREGISTERED / EXPERIMENTAL CALIBRATION CHIP
Date: 2026-09-10

## Problem

Current `change_magnitude` is requested directly from the Cognitive Impact LLM as a `[0,1]` value. Production grounding only clamps it; it does not calibrate it against an external ruler.

The same pseudo-cardinal value then controls primary-effect selection, materiality thresholds, Attention routing, and Pareto `change_band`. This couples semantic topology to an uncalibrated stochastic estimate.

Working diagnosis:

```text
Semantic topology may be stable
while raw cardinal magnitude is not.
```

The next experiment should therefore test whether magnitude is needed at all as decision authority.## Proposed calibration seam

```text
CognitiveImpactResponse.effects[]
        ↓
Effect Calibration Strategy
        ↓
Calibrated Cognitive Effects
        ↓
Decision Strategy
        ↓
Attention Policy
```

Baseline chip remains `raw-cardinal-v1` for reproducibility.

Candidate chip: `magnitude-free-v0.1`.

`magnitude-free-v0.1` ignores `change_magnitude` entirely for ranking, Pareto dominance, and Attention routing. The raw field may remain stored only for compatibility/debug and must have no decision authority.## v0.1 Occam hypothesis

Do not immediately replace one pseudo-cardinal number with another.

Treat **existence of a legal CognitiveEffect** as the semantic materiality claim. Then route using categorical structure plus already-grounded context:

- operation: `REINFORCE | CHALLENGE | OPEN_NEW`
- target node type / active role
- grounded target-importance band
- epistemic-strength band
- D/S/P and runtime remain separate

No multiplication, averaging, softmax, or magnitude threshold is allowed in this chip.

If this loses necessary discrimination, only then introduce a later ordinal transition class / margin model.## Candidate magnitude-free Attention semantics

For a legal targeted `CHALLENGE`: high grounded importance + sufficient epistemic support → ENGAGE; otherwise WATCH/AWARE according to evidence and target role. A weak low-importance challenge must not be promoted merely because it is a CHALLENGE.

For `OPEN_NEW`: a genuinely new branch inside active jurisdiction is at least WATCH; stronger promotion depends on evidence/active anchor, not a raw magnitude float.

For `REINFORCE`: default is AWARE; promote to WATCH/ENGAGE only when the target role itself is decision-bearing (for example active QUESTION/BOTTLENECK/DECISION) and evidence warrants attention.

No-effect remains governed by the independent D/S/P awareness path.

This design intentionally separates semantic direction from attention severity.

## v0.1 frozen decision rules

`magnitude-free-v0.1` retains raw `change_magnitude` only for compatibility/debug. It must not affect Pareto dominance or channel Attention.

- CHALLENGE: important + sufficient epistemic support -> ENGAGE; important + weak support -> WATCH; low-importance -> AWARE.
- OPEN_NEW: important + sufficient -> ENGAGE; either important or sufficient -> WATCH; neither -> AWARE.
- REINFORCE: active Decision -> ENGAGE; important Question/Bottleneck -> WATCH; ordinary Belief/Model/Hypothesis reinforcement -> AWARE.
- Pareto vector: `(epistemic_band, importance_band, active_role_band, is_challenge, is_open_new)`. No magnitude dimension.
- Article aggregation remains `DROP < AWARE < WATCH < ENGAGE` join.

Focused/contract regression before measurement: `72 passed`. Broader backend regression: `333 passed, 4 skipped`; the only failure is the pre-existing excluded Case K PREEMPT-vs-PRIORITY residual.
