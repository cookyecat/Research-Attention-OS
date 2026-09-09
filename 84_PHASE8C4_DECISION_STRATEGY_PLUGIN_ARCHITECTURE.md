# Phase 8C.4 — Decision Strategy Plug-in Architecture

Status: IMPLEMENTATION / BEHAVIOR-PRESERVING BASELINE
Date: 2026-09-10

## Objective

Create an explicit, versioned decision-strategy seam so RAOS can compare one-Delta, multi-Delta, Pareto/partial-order, and later calibration policies without rewriting production control flow.

This change is architectural only. The production default remains the existing one-Delta policy.

## Frozen default

```text
strategy_id = one-delta
version     = one-delta-v1
```

The default strategy preserves the current pipeline:

```text
CognitiveImpactAssessment.effects[]
  -> NormalizeFrozenTransition
  -> select_primary_effect(argmax(change_magnitude * target_importance))
  -> legacy Attention Policy
  -> runtime overlays
```
## Strategy contract

A decision strategy now owns three explicit responsibilities:

```text
route(...)
visible_prediction(...)
execution_snapshot()
```

`run_pipeline(..., decision_strategy=...)` can inject a strategy. If omitted, `one-delta-v1` is used.

Every new AnalysisRun records:

```text
execution_snapshot.decision_strategy
attention_plan.score_debug.decision_strategy
```

The strategy fingerprint participates in the AnalysisRun execution digest, so different strategy versions cannot collide in cache.

Historical runs without this field resolve to the legacy one-Delta strategy. Stored version mismatches fail closed rather than silently reinterpret history.

## Research use

The seam is intentionally lighter than a dynamic plug-in ecosystem. It is a versioned Strategy/Dependency-Injection boundary, not Python entry-point loading.

Next candidate chips can be implemented behind the same contract, for example:

```text
one-delta-v1       — frozen production baseline
multi-delta-v1     — multiple cognitive effects, per-channel policy
pareto-delta-v1    — partial-order / Pareto frontier candidate
ordinal-margin-v1  — future calibration strategy
```
## Calibration finding carried forward

`change_magnitude` is still a raw LLM estimate clamped to `[0,1]`; production grounding does not recalibrate it.

Production does improve the other axes:

```text
target_importance  -> explicit Kernel value > node-type prior > LLM estimate > neutral
epistemic_strength -> deterministic caps from evidence/source conditions
invalid targets     -> discarded during grounding
```

Therefore full production grounding can reduce target/epistemic errors, but it cannot remove change-magnitude jitter by itself.

The next research step should use the new strategy seam to compare the frozen one-Delta baseline against a partial-order/Pareto candidate without changing Sensor/Auditor or the production default.

## Validation

Focused contract / identity / replay suite:

```text
83 passed, 1 warning
```

Broader regression including Phase 6B, raw-source vertical slice, 8C.2 bridge, analysis-run identity, WATCH/continuous arrival, Attention Policy contract, and acceptance cases:

```text
108 passed, 1 deselected, 1 warning
```
