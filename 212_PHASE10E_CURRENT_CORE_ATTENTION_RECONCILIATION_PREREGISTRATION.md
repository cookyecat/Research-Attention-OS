# Phase 10E — Attention Core Validity Gate Preregistration

Date: 2026-09-15 / amended 2026-09-16 before canonical Phase-10E measurement
Status: **IMPLEMENTATION ACTIVE / CANONICAL MEASUREMENT NOT YET RUN**
Production impact: **none; validation-only gate**

## 1. Purpose

Phase 10E is not a new RAOS runtime module, state variable, policy layer, or attempt to make the theory complete over every imaginable corner case. It is a short pre-Phase-12 health check on the existing Phase 1–10 Attention Core.

The working principle is:

```text
Theory defines the invariant.
Engineering estimates enough state to preserve the invariant.
The flywheel reveals where that approximation actually fails.
```

The gate therefore validates the common operating regime rather than every logically constructible state.

## 2. Why this gate is necessary

The historical `Oracle-Delta` harness can silently route frozen Delta through legacy `one-delta-v1`, while current dogfood explicitly uses:

```text
research-aligned-cognition-v1
+ pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
```

Therefore the historical 30-case replay is not evidence about the current active Attention Core and may not justify current Core or Phase-12 changes.

Phase 10E restores a strategy-explicit, no-LLM measurement path for the current Core.

## 3. Theory / engineering boundary

Let `Z*` denote the ideal decision-relevant state and `Z_hat` the state actually estimated and persisted by the engineering system.

```math
A^* = \pi^*(Z^*, R)
```

Production instead operates approximately:

```math
\hat Z \rightarrow \hat\pi \rightarrow \hat A
```

A Human-Gold mismatch under the same `Z_hat` does not automatically prove missing theory. It may be estimator error, representation coarseness, runtime capture error, policy error, or a genuine missing universal factor.

Approximate state estimation is allowed; semantic shortcutting is not.

## 4. Occam constraints

Phase 10E may add measurement / replay code only. It may not add:

```text
new production state variables
new database tables
new scheduler parameters
new personalization parameters
new LLM stages
new Attention dispositions
```

A new Core variable is justified only by repeated evidence that is reachable, reproducible, decision-bearing, and non-negligible in frequency or consequence.

Synthetic corner cases are diagnostic only. They do not block Phase 12 and do not authorize Core redesign unless they become materially reachable or observed.

## 5. Gate I — Deterministic Integrity

Gate I requires no Human Gold and no LLM call.

### I-A. Strategy-explicit replay parity

For persisted current-strategy AnalysisRuns, replay only the frozen decision state using the exact stored decision-strategy id and version.

Fail closed on missing or mismatched strategy identity. Bare `scheduler.route()` defaults are forbidden.

Required invariant:

```text
same persisted decision state + same strategy snapshot
→ same disposition
→ same decision cause
```

Canonical gate:

```text
exact disposition parity = 100%
exact strategy identity parity = 100%
exact decision-cause parity = 100%
upstream model calls = 0
```

### I-B. Main-regime policy coherence

On actually observed non-empty current-strategy effect sets, compare:

```text
current: admitted effects → Pareto → channel policy → article join
counterfactual: admitted effects → same channel policy → article join
```

This is not a proposal to remove Pareto. It asks whether the currently observed operating regime contains a material order-policy conflict.

A synthetic algebraic counterexample remains a watch item unless canonical reachability and material decision consequence are established.

Decision-cause differences with the same disposition are recorded as causal-geometry differences, not automatically labeled failures.

## 6. Gate II — Operating-Regime Adequacy

Only after Gate I passes, collect a small fresh Human-Gold probe over common/high-value operating regimes.

Initial scope should be deliberately small, for example 6–10 matched pairs spanning ordinary REINFORCE, important QUESTION/BOTTLENECK reinforcement, strong CHALLENGE, valid OPEN_NEW, no-Delta D/S/P, and representative Runtime behavior.

The question is not whether `Z_hat` is a mathematically complete sufficient statistic. The practical question is:

> Does the current approximate state representation support stable, reasonable Attention decisions in the operating regimes RAOS actually cares about?

Mismatch attribution order:

```text
ESTIMATION_ERROR
REPRESENTATION_TOO_COARSE
RUNTIME_CAPTURE_ERROR
POLICY_ERROR
CANDIDATE_UNIVERSAL_MISSING_FACTOR
USER_SPECIFIC_RESIDUAL
UNRESOLVED
```

Only a repeated `CANDIDATE_UNIVERSAL_MISSING_FACTOR` may reopen Core theory. Only a residual remaining after Core attribution may proceed to Phase 12 personalization.

## 7. Long-tail rule

Long-tail and rare corner-case discovery belongs primarily to the operating flywheel:

```text
real usage
→ feedback / residuals
→ recurrence + severity
→ causal attribution
→ only then theory / estimator / policy amendment
```

The Core must not be expanded pre-emptively to cover low-probability imagined states.

## 8. Relation to Pareto and Stability Theory

Pareto remains part of the current policy `pi`; it is not an axiom of Distributional Cognitive Stability Theory. Stability metrics and Decision-Causal Core are policy-relative.

The current stance is:

```text
Pareto = KEEP + MEASURE
```

Its original motivations remain valid: avoid scalar winner-take-all, preserve incomparable cognitive effects, and avoid inventing pseudo-cardinal precision after Magnitude-Free. Any simplification or repair requires evidence from reachable operating states, not synthetic counterexamples alone.

## 9. Exit rule

Phase 10E is intentionally short.

It closes when:

```text
Gate I deterministic integrity passes;
Gate II common-regime Human Gold shows no material universal Core omission,
or any observed mismatch has been attributed without requiring a new Core variable.
```

No observed material failure means no Core redesign.

Phase 12 may then resume with identity/no-op personalization as the default.

## 10. Pre-canonical implementation note

During implementation preflight, non-canonical exploratory checks were used only to verify that the proposed instrument can reconstruct current persisted state and to expose schema/plumbing issues. Those checks are not the canonical Phase-10E result. The canonical artifact must be produced only by the versioned instrument committed for this gate.
