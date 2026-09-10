# Phase 8C.13 — Decision-Causal Core Chip Preregistration

**Status:** PREREGISTERED / NOT YET MEASURED  
**Production impact:** none; deterministic research measurement only  
**Frozen decision stack:** Anchored OPEN_NEW + Magnitude-Free + Pareto

## Purpose

Topology similarity is descriptive. Phase 8C.13 measures which cognitive relations actually carry the Article Attention decision under the frozen policy.

For a realized legal relation set `T` and decision policy `pi`, define first-order necessity:

`Necessary(r) := pi(T - {r}) != pi(T)`

The original load-bearing-wall definition is this necessary core. However Pareto permits redundant supports, so singleton deletion alone can miss relations that each independently sustain the same decision. Therefore v0.1 also measures first-order sufficiency:

`Sufficient(r) := pi({r}) == pi(T)`

Classification:

- necessary + sufficient: singular load-bearing relation;
- not necessary + sufficient: redundant load-bearing support;
- necessary + not sufficient: interaction-dependent relation;
- neither: peripheral for the measured Article disposition.

This is a first-order causal profile only. No Shapley value, power-set search or multi-relation minimal-cut enumeration is permitted in v0.1.

## Decision projection

Core membership is defined against **Article Attention disposition** (`DROP/AWARE/WATCH/ENGAGE`) under the frozen strategy. Changes only to prose/reason fields do not count as decision changes in v0.1.

## Unit of ablation

The ablation unit is a decision relation `(operation, target)`, not an individual duplicate effect. All effects sharing the same relation key are removed/isolated together. OPEN_NEW is `(OPEN_NEW, null)` at this decision-topology layer.

## Validation

1. Synthetic contract tests: unique necessary relation, redundant sufficient relations, peripheral relation, empty set, magnitude invariance.
2. Canonical measurement: RS05, RS15, RS11, RS12 using exact historical audited worlds + exact historical modal Locate fixtures.
3. Relation Mapping is sampled; all causal ablations inside each sample are deterministic and make no additional LLM calls.

Report relation occurrence frequency separately from necessity/sufficiency frequency. A high-frequency relation is not automatically causal.

## Measurement-definition amendment discovered by negative control

The first exploratory replay revealed that `alone == baseline == DROP` cannot constitute causal sufficiency. Canonical v0.1 therefore requires `pi({r}) == pi(T)` **and** `pi(T) != pi(empty)`. The pre-fix artifact is invalid for inference; the corrected rerun is the canonical result recorded in `106_PHASE8C13_DECISION_CAUSAL_CORE_RESULT.md`.
