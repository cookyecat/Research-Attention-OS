# Phase 10E — Pareto / Magnitude-Free / Stability Coherence Review

Date: 2026-09-15
Status: **ARCHITECTURE REVIEW / EXPLORATORY AUDIT**
Production impact: **none**

## 1. Historical correction

Pareto and Magnitude-Free are related, but the causal history is sequential rather than identical:

```text
one-delta scalar winner
→ Multi-Delta + Pareto partial order (Phase 8C.5)
→ raw magnitude still causes boundary jitter
→ Magnitude-Free ordinal authority (Phase 8C.6)
→ Cardinal-Free effect existence + authoritative enrichment
```

Phase 8C.5 introduced Pareto to preserve incomparable effects instead of forcing one scalar winner. Phase 8C.6 then removed raw LLM `change_magnitude` from decision authority while retaining a partial-order strategy over remaining ordinal dimensions.
## 2. Relation to Stability Theory

Distributional Cognitive Stability Theory does not require Pareto as an axiom. Its Decision-Causal Core is explicitly policy-relative: for a frozen topology `T`, load-bearing relations are defined under a specified downstream policy `pi`.

Therefore:

```text
Stability Theory validates behavior under a fixed policy;
it does not by itself prove that Pareto is the unique or necessary policy.
```

Pareto can nevertheless contribute a robustness mechanism by preventing clearly dominated effects from controlling the decision while preserving incomparable channels. That mechanism must be validated independently.
## 3. Necessary coherence condition

Let `v(e)` be the Pareto decision vector for effect `e`, and let `g(e)` be its per-effect Attention action under Magnitude-Free channel policy. Let Attention rank be:

```text
DROP < AWARE < WATCH < ENGAGE
```

Safe Pareto pruning requires isotonicity:

```math
v(e_1) \succeq v(e_2)
\Rightarrow
rank(g(e_1)) \ge rank(g(e_2))
```

If this holds, Pareto pruning cannot remove an effect that would have produced a stronger article-level action. Under max/join aggregation:

```math
join(g(Pareto(E))) = join(g(E))
```

Pareto then changes causal/provenance geometry without changing final disposition.
## 4. Exploratory algebra audit

An exploratory exhaustive check of the current code enumerated 44 atomic effect states and all 946 two-effect pairs using the live `MagnitudeFreeCalibration` and current Pareto vector.

Observed:

```text
25 / 946 pairs changed final disposition
when comparing:
Pareto → channel policy → join
vs
all admitted effects → same channel policy → join
```

The counterexamples are concentrated around `REINFORCE` on `DECISION`. The current Pareto vector compresses `QUESTION`, `BOTTLENECK`, and `DECISION` into the same binary `active_role_band`, while the channel policy treats `DECISION` specially as immediate `ENGAGE`.

Example:

```text
REINFORCE(DECISION, importance=HIGH, epistemic=LOW) → ENGAGE
CHALLENGE(QUESTION, importance=HIGH, epistemic=LOW) → WATCH
```

The CHALLENGE vector dominates the REINFORCE vector, so current Pareto pruning can remove the ENGAGE-producing effect and return WATCH.
## 5. Production reachability check

The current dogfood database contains 84 AnalysisRuns. Only three completed current-strategy runs currently contain non-empty research-aligned effect sets; none contains a `DECISION` target. Therefore the synthetic counterexample has **not** been observed in current dogfood production data.

This is a structural warning, not evidence of a field failure.

It is also not safe to dismiss as unreachable: Kernel `DECISION` is a supported target type, its channel policy is explicit, and target importance can be overridden by explicit Kernel state. Formal Gate 0 must therefore test reachable canonical states rather than arbitrary vectors alone.

## 6. Revised Phase 10E consequence

Human-Gold state-sufficiency testing should not begin until the deterministic policy algebra is coherent.

The next order is:

```text
Gate 0a: prove / falsify Pareto-channel isotonicity on reachable canonical states
Gate 0b: if violated, compare the smallest policy-preserving repairs
Gate A: strategy-explicit production replay parity
Gate B: minimal Human-Gold state-sufficiency probe
```

Candidate repairs are not preregistered as winners. The simplest possibilities are to make the dominance vector reflect existing decision-relevant role distinctions, or to move Pareto to a post-channel causal/provenance role. No new semantic variable is justified by this review.