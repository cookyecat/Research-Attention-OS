# Phase 10E — Current-Core Attention Reconciliation Preregistration

Date: 2026-09-15
Status: **PREREGISTERED / NOT YET MEASURED**
Production impact: **none before a measured gate**

## 1. Why this phase exists

Phase 12 personalization review exposed an instrumentation mismatch: the historical `Oracle-Δ` harness still routes frozen Delta through the legacy `one-delta-v1` strategy, while active developer dogfood uses `research-aligned-cognition-v1` with `pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2`.

Therefore the exploratory 30-case replay cannot be interpreted as a measurement of the current active Attention Core.

Phase 10E restores the original scientific purpose of Oracle-Δ under the current architecture: freeze cognition, remove upstream stochasticity, and test only the active Attention decision machinery.

## 2. Frozen active Core under test

The positive cognitive-effect branch under test is exactly:

```text
frozen authorized CognitiveEffect set
→ effect-specific OPEN_NEW admission
→ Magnitude-Free calibration
→ Pareto frontier
→ article-level Attention join
→ Runtime overlay
```

The no-Delta branch remains separate:

```text
Delta = NONE
→ frozen/oracle D/S/P semantics
→ AWARE iff S AND (D OR P)
→ Runtime only where already authorized by the current Core
```

No Phase 12 calibration parameter is present in this phase.

## 3. Research questions

RQ10E.1 — Can a current-core Oracle harness reproduce active production Attention exactly when supplied the same frozen post-cognition inputs?

RQ10E.2 — After upstream cognition is held correct, does the current active Attention Core reproduce fresh Human Gold without needing additional latent variables?

RQ10E.3 — If mismatches remain, are they attributable to an existing Core rule, a missing universal Core variable, Runtime capture, or a truly user-specific residual?

## 4. 10E.1 — Current-Core Oracle Harness

The new harness must not call Extract, Sensor, Auditor, Locate, Relation Mapping, Support Binding, Grounding, or Jurisdiction models.

It consumes a frozen authorized effect set containing exact operation, target/jurisdiction, support provenance, grounding, importance band, epistemic band, and effect-specific jurisdiction anchors, plus frozen Runtime.

It must explicitly route through the active decision strategy snapshot rather than relying on the legacy default of `scheduler.route()`.

## 5. 10E.2 — Production-Parity Replay

Before collecting any new Human Gold, replay a set of completed `research-aligned-cognition-v1` AnalysisRuns from the dogfood database.

For each run, reconstruct the frozen post-cognition effect set and Runtime from stored provenance, then compare Oracle output against the persisted production AttentionPlan.

Primary gate:

```text
exact disposition parity = 100%
exact decision-strategy identity parity = 100%
no upstream model call = 100%
```

Any failure here is an instrumentation defect. Human-Gold interpretation is forbidden until parity is restored.

## 6. 10E.3 — Fresh Core-Completeness Human-Gold Probe

Only after 10E.2 parity passes, collect fresh controlled judgments against current semantics.

The probe is not a personalization questionnaire. It is a Core completeness test. Cases should isolate current decision dimensions and historical candidate omissions while keeping upstream cognition frozen.

High-value probe families:

```text
REINFORCE / CHALLENGE with ordinal importance × epistemic authority
OPEN_NEW with valid jurisdiction but varied generative potential
WATCH-worthy optionality with otherwise matched current-core inputs
multi-effect / Pareto cases
separate Runtime perturbations using already-canonical Runtime fields
Delta=NONE with complete oracle D/S/P inputs
```

The historical 30-case questionnaire may inform case construction but is not current Gold and must not be scored as a confirmatory dataset.

## 7. Attribution firewall

Every fresh mismatch must be classified before any policy change:

```text
INSTRUMENT_ERROR
CURRENT_RULE_ERROR
MISSING_UNIVERSAL_CORE_VARIABLE
RUNTIME_CAPTURE_ERROR
NO_DELTA_DSP_ERROR
USER_SPECIFIC_RESIDUAL
UNRESOLVED
```

`USER_SPECIFIC_RESIDUAL` is not allowed unless all canonical Core inputs are judged correct and the same residual is stable across repeated matched cases.

A candidate such as `GenerativePotential` can return to Core only if fresh matched cases show that current authorized inputs are insufficient to explain systematic Human Gold differences. It must not be introduced merely because it appeared in the historical pilot.

## 8. Exit and handoff

Phase 10E closes when:

```text
10E.1 current-core Oracle harness exists and is versioned;
10E.2 production-parity replay passes the preregistered exact gate;
10E.3 fresh Human-Gold probe is completed and mismatches are causally attributed;
10E.4 any Core amendment, if required, is separately preregistered and revalidated.
```

If fresh evidence finds no stable residual beyond the Core, Phase 12 personalization remains identity/no-op by default.

If a stable universal missing factor is found, it returns to the Core research line first; it must not be absorbed as personalization.

If stable user-specific residuals remain only after Core reconciliation, Phase 12 may resume with bounded calibration.

## 9. Immediate decision

Phase 12A is **PAUSED BY CORE GATE** until Phase 10E completes. No personalization fitting, questionnaire calibration, or scheduler tuning is authorized during this gate.
