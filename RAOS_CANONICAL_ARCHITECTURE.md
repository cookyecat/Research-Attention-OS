# RAOS Canonical Architecture — HEAD Contract

Status: **AUTHORITATIVE LIVING DOCUMENT**

This file describes the architecture that the current repository HEAD is intended to execute.
It is not a historical result log. Numbered research documents explain *why* the architecture changed; this file states *what the architecture is now*.

## Maintenance rule

Any commit that changes a RAOS module, responsibility boundary, main data flow, Attention decision path, or research/online semantic contract **must update this file in the same commit**.

If code and this document disagree, the mismatch is an architecture defect to be resolved explicitly; neither side silently wins.

## 1. System objective

RAOS maintains a changing model of the outside information world and allocates scarce human attention relative to a changing cognitive state.

```text
External World W_t
      ↓
Acquisition
      ↓
Observable Information I_t
      ↓
Information / Evidence Representation
      ↓
Cognition relative to K_t
      ↓
Attention / Authorized Action
      ↓
K_{t+1} when explicitly authorized
```
## 2. Canonical HEAD dataflow

```text
Sources / Feeds / APIs / Manual Input
        ↓
──────────────── Acquisition Plane ────────────────
SourceDefinition → Observation → Information Object → Snapshot
        ↓
RAOS Source / Raw Information Boundary
        ↓
──────────── Information / Evidence Plane ─────────
Semantic Sensor → Semantic Evidence Auditor
        ↓
Audited World Representation
        │
        ├──────────────── Cognitive Transition Path ───────────────┐
        │                                                          │
        │  Locate(K_t) → Relation Mapping → Support Binding         │
        │  → Grounding / OPEN_NEW Jurisdiction → Authority          │
        │  → Cardinal-Free Effect Existence → Magnitude-Free        │
        │  → Pareto                                                  │
        │                                                          │
        └──────────────── No-Delta Awareness Path ─────────────────┤
                                                                   │
           Audited Event Projection → D / S / P                    │
           → AWARE iff S AND (D OR P)                               │
                                                                   ↓
──────────────── Attention / Action Plane ────────────────
DROP / AWARE / WATCH / ENGAGE
        ↓
Decision Cause → Public Update / WATCH / authorized KernelPatch
```

The two Attention branches are orthogonal. D/S/P is not a substitute for cognitive effects, and cognitive relevance is not a substitute for situational awareness.
## 3. Attention authority split

### 3.1 Cognitive-effect branch

When one or more legal cognitive effects survive the research-aligned cognition contract, D/S/P has no authority over that decision.

```text
REINFORCE / CHALLENGE / OPEN_NEW
→ Grounding / Authority
→ Magnitude-Free / Pareto
→ cognitive Attention
```

This branch may produce AWARE, WATCH, or ENGAGE according to the selected semantic effect and frozen policy. It may authorize public cognitive update, WATCH responsibility, or KernelPatch only from the exact Decision Cause.

### 3.2 No-Delta branch

When no legal cognitive effect survives:

```text
Δ = NONE
→ evaluate audited event(s)
→ D / S / P
→ DROP or AWARE
```

Frozen semantic gate:

```text
AWARE iff S AND (D OR P)
```

D = Standing Attention Jurisdiction / Standing Radar Fit.
S = Material Consequence to a consequential shared reference system.
P = Collective Attention Salience inside the event's objective constituency.

P must come from external attention evidence. Article wording, topic similarity, fame, and model prior must not manufacture current P.
When direct platform statistics are unavailable, an engineering estimator or explicitly labelled simulation may approximate P for dogfood/counterfactual analysis, but it must remain provenance-distinct from observed attention evidence and must not redefine the frozen P semantics.
UNKNOWN is not False. If missing components prevent the Boolean result from being logically determined, the no-Delta decision is unresolved rather than silently coerced to DROP.
## 4. Current contract versions

```text
Acquisition Plane              acquisition-plane-v0.1
Semantic Sensor                semantic-evidence-extractor-v0.2.6
Semantic Evidence Auditor      semantic-evidence-auditor-v0.1.1
Cognition                      research-aligned-cognition-v1
Relation Mapping               Phase 9A v0.2 frozen contract
Support Binding                Phase 10D.6L.3 frozen contract
Grounding                      Phase 10D.6L.4 frozen contract
OPEN_NEW Jurisdiction          Phase 10D.6L.4J frozen contract
Effect existence               semantic-cardinal-free
Effect calibration             magnitude-free-v0.1
Decision strategy              pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
D                              standing-radar-fit-estimator-v4 / profile-v4
S                              material-consequence-estimator-v1
P                              collective-attention-estimator-v1
No-Delta gate                  aware-iff-s-and-d-or-p-v1
Unknown composition            no-delta-awareness-integration-v1.1 semantics
```

## 5. Core invariants

1. Acquisition observes; it does not judge cognitive relevance or importance.
2. Sensor/Auditor is the shared evidence boundary for both cognition and no-Delta awareness.
3. D/S/P operates on audited event semantics, not arbitrary whole-article topic text.
4. P is a latent collective-attention state estimated from attention evidence, not article prose.
5. D/S/P has authority only when no legal cognitive Decision Cause exists.
6. Attention Policy must not manufacture cognitive change.
7. Decision Cause = Public Update Cause = Authorized Side-Effect Cause.
8. UNKNOWN / unavailable evidence is not negative evidence.
9. Historical snapshots and execution identity are immutable; replay must preserve the frozen contract.
10. Research and active developer dogfood should execute the same validated semantic contract unless an explicit versioned experiment says otherwise.

## 6. Architecture-change checklist

Before merging an architectural change, check this document against:

```text
module inventory
main dataflow
branching / authority boundaries
versioned contracts
execution identity
online wiring
research ↔ dogfood parity
```

A module that exists only in research code but is required by this diagram is an explicit wiring gap, not an implicit future feature.
