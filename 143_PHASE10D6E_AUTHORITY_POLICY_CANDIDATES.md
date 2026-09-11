# Phase 10D.6E — Authority Policy Candidates

**Status:** PRE-MEASUREMENT FREEZE / NO OUTCOMES SAMPLED
**Date:** 2026-09-11

## Controlled replay

Replay the already persisted Phase 10D.4 semantic realizations. No LLM, acquisition, Sensor, Auditor, Locate, Relation Mapping, or grounding call is allowed. Operation, target, reason, frozen Kernel, frozen Locate, and article-level aggregation remain unchanged. Only the decision-bearing authority bands are replaced.

## Baselines

- `NATIVE_RAW`: historical Phase 10D.4 Magnitude-Free v0.1 using stored LLM `epistemic_strength` and `target_importance`.
- `PRODUCTION_IMPORTANCE`: 10D.5-style production importance rebinding while retaining the stored epistemic value.

## Candidate C1 — Conservative Canonical Authority

**Importance authority**
- explicit Kernel `importance` / `priority` is authoritative;
- otherwise active `QUESTION`, `BOTTLENECK`, or `DECISION` targets are `HIGH`;
- ordinary `BELIEF` / `MODEL` targets without explicit priority are `LOW`;
- `OPEN_NEW` is `HIGH` only when an explicit high-priority jurisdiction anchor exists; otherwise `LOW`.

**Epistemic authority**
- targeted `REINFORCE` / `CHALLENGE` is `SUFFICIENT` only with direct observation or at least two independent support sources; otherwise `WEAK`;
- `OPEN_NEW` may be `SUFFICIENT` when the frozen world contains Auditor-admitted supported units, because the decision claim is only that the source opens a grounded branch, not that every source proposition is externally true.

## Sensitivity C2 — Auditor-trust upper bound

Use the same C1 importance policy, but treat any relation over an Auditor-admitted frozen world as epistemically `SUFFICIENT`. This is an intentional upper bound for detecting uncontrolled `ENGAGE` inflation and is not a promotion candidate by itself.

## Decision rule

C1 is preferred only if it avoids critical false `DROP`, avoids uncontrolled `ENGAGE` inflation, preserves known stable Attention basins, and remains semantically interpretable. C2 is diagnostic only. No candidate may be changed after replay outcomes are observed.
