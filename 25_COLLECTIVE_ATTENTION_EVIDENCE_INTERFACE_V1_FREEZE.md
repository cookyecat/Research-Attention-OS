# Collective Attention Salience (P) — Evidence Packet v1 Freeze

Status: **EVIDENCE INTERFACE v1 — FROZEN**  
Date: 2026-09-07  
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`  
Estimator modeling baseline: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`

## 1. Frozen source

Evidence Packet v1 is the interface defined in:

`24_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE.md`

at source commit:

```text
651d64762b3f980745484f9fa13a187e0efb6f6e
```

with content blob SHA:

```text
dc790341d50ecbd8a88987647280793d844b5ebb
```

The earlier document may retain its historical `CANDIDATE v0.2` header; this freeze declaration establishes that exact content as **Evidence Packet v1** for the first P estimator lifecycle.

## 2. Frozen top-level contract

```text
Event
ConstituencyPrior
CollectionContext
CurrentAttentionEvidence
RecentAttentionHistory
```

Canonical flow:

```text
world / platforms / communities
        ↓
noisy and incomplete observations
        ↓
Evidence Packet v1
        ↓
P estimator
        ↓
SALIENT / NOT_SALIENT
```

Core invariant:

$$
\boxed{Observation\neq P}
$$

The packet is a sensor boundary, not a second classifier.

## 3. Frozen interface principles

1. `event.as_of` is required because `P=P(E,t)`.
2. The Objective Attention Constituency is chosen from event semantics, not optimized after observing attention.
3. Constituency scale may be coarse; false numeric precision is not required.
4. `reference_size_hint` is optional and must be grounded when supplied.
5. Current attention observations carry source, time window, observation time, evidence quality, independence grouping, and contamination information.
6. Recent history carries observations rather than treating previous model labels as truth.
7. Missing evidence is unknown, not zero.
8. `collection_context` records which channels were checked and which were unavailable.
9. D, S, user interest, event importance, sentiment, stance, downstream AttentionAction, and any pre-computed P label are excluded from the packet.
10. Controlled scored evaluation uses a frozen packet; the estimator does not browse for additional live evidence during the first-run measurement.

## 4. Representational evidence

Before freeze, the interface was checked against development cases PC1–PC24.

```text
PC1-PC24 representable             24/24
P-label leakage required           0/24
D/S fields required                0/24
Exact hidden platform telemetry    0/24
```

This is representational calibration evidence only. PC1–PC24 must not be reused as fresh holdout evidence.

## 5. Change policy

Evidence Packet v1 is now frozen for the first P estimator lifecycle.

Do not change it merely because a model performs poorly.

A future interface revision requires an attributable interface limitation, such as:

- a real observation needed by P cannot be represented;
- missingness/provenance cannot be expressed correctly;
- the schema permits semantic leakage that compromises measurement;
- real-world dogfooding exposes repeated sensor-boundary ambiguity.

Estimator prompt errors, model reasoning errors, or lack of external telemetry are **not** by themselves reasons to redefine the frozen interface.

## 6. Next step

```text
P semantics                FROZEN
Evidence Packet v1         FROZEN
        ↓
Implement P estimator v1
        ↓
Regression / dry-run only
        ↓
Freeze estimator + prompt/profile provenance
        ↓
Author fresh P holdout
```
