# Phase 17 — Recursive Event State Filter Primitive Result V0.1

Status: **PRIMITIVES IMPLEMENTED / PRODUCTION REPRESENTATION SNAPSHOT ENABLED / ATTENTION POLICY UNCHANGED**  
Date: 2026-09-21

References:

- `267_PHASE17_EVENT_STATE_MODEL_REVIEW_AND_JEV_BENCHMARK.md`
- `268_PHASE17_JEV_LONGITUDINAL_BENCHMARK_IDENTITY_RESULT.md`
- `269_PHASE17_EVENT_SOURCED_RECURSIVE_STATE_FILTER_THEORY.md`

## 1. Theory frozen

Phase17 adopts mature external principles rather than inventing a bespoke dynamic-state theory:

```text
Event Sourcing
+
Recursive State Estimation
+
Evidence Accumulation
+
Hysteretic Attention
```

Canonical dynamic laws:

\[
S_{t+1}=U(S_t,e_{t+1})
\]

\[
D_{t+1}=F(S_{t+1},K_t,C_t)
\]

\[
A_{t+1}=\mathcal H(A_t,D_{t+1},C_t)
\]

Conservation principle:

```text
History append-only.
Current State revisable.
```

## 2. EventState contract

Implemented:

```text
event-state-v0.1
```

with:

```text
EventState
├─ WorldState
└─ EvidenceState
```

WorldState reuses the small current Event projection:

```text
title
event_type
actors
action
object
occurred_at
time_context
location
summary
current_state
status
```

EvidenceState contains structural support state:

```text
member_source_count
independent_source_count
secondary_report_count
relational_digest
arrival_momentum        # optional / not production-selected
momentum_model          # optional / not production-selected
momentum_updated_at
last_evidence_key
```

No algorithm-specific Event fields were added.

In particular, the Event schema does not gain fixed columns for:

```text
correction
supersession
contradiction
enrichment
```

Those remain possible internal semantics of a candidate update operator.

## 3. EventRevision as Event-Sourcing log

No new table was introduced.

Existing `EventRevision` now carries:

```text
revision_payload.event_state
  contract = event-state-v0.1
  world_state
  evidence_state
  state_digest
```

This gives each future Event CREATE/UPDATE revision a structured materialized state snapshot while preserving immutable revision history.

Production Attention/Decision behavior is unchanged by this wiring.

## 4. Revision-chain integrity repair

While testing structured EventState snapshots, Phase17 exposed a hidden Event-Sourcing correctness risk.

Historical `_latest_revision()` selected the latest revision using:

```text
created_at DESC
+ UUID ordering
```

SQLite timestamps can share the same second. UUID order is not chronology.

Therefore rapid Event updates could theoretically select the wrong head or create a revision fork.

Repair:

```text
revision head
=
the unique EventRevision that is not referenced as parent_revision_id
```

If multiple heads exist:

```text
fail closed
```

A rapid three-update regression verifies one root, one head, one linear parent chain.

## 5. Recursive filter primitives

Implemented in:

```text
backend/app/services/event_state.py
```

Primitive contracts:

```text
event-state-v0.1
recursive-event-state-filter-v0.1
hysteretic-attention-controller-v0.1
```

### Leaky accumulator

\[
M_{t+1}=\rho^{\Delta t}M_t+I_{t+1}
\]

The primitive is generic.

It does not define `innovation` as Source count and does not freeze a production \(\rho\).

### Recursive reducer

```text
previous EventState
+
EventStateDelta
-> next EventState
```

Immediate replay of the same evidence key is idempotent.

Global exactly-once semantics remain the responsibility of append-only history/revision identity.

### Hysteresis controller

A generic multi-level Schmitt-trigger primitive is implemented for:

```text
DROP
AWARE
WATCH
ENGAGE
```

with distinct enter and exit thresholds.

The mapping from cognition/decision output to a normalized signal is intentionally not frozen yet.

## 6. Jev benchmark corrected semantics

The benchmark is now explicitly four-layered.

### Observed World Trace

Frozen RAOS-observed trace:

```text
44 deduplicated ExternalInformationItems
2026-09-16 -> 2026-09-20
28 Weibo
15 Bilibili
1 Substack
```

Daily new-item arrivals:

```text
3 -> 8 -> 15 -> 8 -> 10
```

This is an observed acquisition sample, not global population-level popularity ground truth.

### Event Gold

```text
t0,t1,t2,t3 -> SAME coarse Event
```

Real Event Processor V1 passed this gate.

### Human Gold

Profile-scoped and subjective:

```text
profile = user-primary-v0.1

AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

This is not a universal normative Attention label.

### Algorithm Output

Candidate U/F/H implementations must be tested against the same frozen trace/profile without rewriting the fixture.

## 7. First leaky-integrator sensitivity

This experiment deliberately does NOT tune against Human Gold.

Input innovation is only:

```text
raw daily RAOS-observed new-item arrivals
```

and is treated as an observational-momentum baseline, not decision evidence.

Full-history cumulative baseline:

```text
3
11
26
34
44
```

This is monotone by construction.

Leaky momentum:

```text
retention/day = 0.25
3
8.75
17.1875
12.296875
13.074219

retention/day = 0.50
3
9.5
19.75
17.875
18.9375

retention/day = 0.75
3
10.25
22.6875
25.015625
28.761719

retention/day = 0.90
3
10.7
24.63
30.167
37.1503
```

Interpretation:

- full-history count cannot decay;
- leakage can represent burst + residual momentum;
- the retention parameter materially changes memory duration;
- no retention value is selected from this experiment.

Artifact:

```text
eval/live/results/phase17_jev_recursive_filter_primitives_v0_1/
phase17_jev_recursive_filter_primitives_v0.1_20260920T192635Z.json
```

## 8. Tests

Phase17 focused suite after the final primitive/benchmark checks:

```text
24 passed
```

Primitive-specific checks include:

- provenance-dependent evidence counts;
- immediate evidence replay idempotence;
- recursive state update;
- leaky decay;
- hysteresis boundary stability;
- real up/down hysteresis transitions;
- Jev World Trace / Human Gold contract separation;
- rapid EventRevision linear-chain integrity.

Full backend regression after all Phase17 changes:

```text
947 passed
63 skipped
1 failed
```

Only known residual:

```text
Case-K:
expected PREEMPT
actual PRIORITY
```

No new backend regression.

## 9. Canonical runtime rollout

Canonical services were restarted after the full regression.

Observed:

```text
backend      LOADED
acquisition  LOADED
delivery     LOADED
frontend     LOADED

backend port 8000 -> single listener
frontend port 3000 -> single listener

health/ready -> READY
attestation  -> ATTESTED
schema drift -> 0
Alembic      -> 0017 head
```

At the time of validation, no EventRevision had yet been produced after the new acquisition worker start time. Therefore no claim is made yet that a naturally arriving production revision has been observed carrying `event-state-v0.1`.

The code path is live and regression-tested; natural production evidence will be checked on the next real revision rather than starting a second writer or manufacturing a production side effect solely for validation.

## 10. What is intentionally NOT selected yet

Phase17 has not frozen:

- innovation \(I_t\);
- retention/decay \(\rho\);
- decision-signal scalarization;
- hysteresis thresholds;
- a final \(\Phi\) state-delta estimator;
- a final reducer \(R\) for semantic state transitions;
- production EventState-based cognition wiring.

These are benchmark/ablation questions.

## 11. Next gate

The next experiment should compare candidate update algorithms over frozen longitudinal traces.

Minimum comparison:

```text
A. Latest Source
B. Full History Bag
C. Recursive Event State
D. Recursive Event State + explicit state-transition semantics where necessary
```

The benchmark should evaluate:

```text
Event identity correctness
state reconstruction
idempotence
temporal/order robustness
provenance dependence
momentum stability
profile-scoped Human Gold agreement
Attention chatter / hysteresis behavior
```

Production Decision wiring should remain unchanged until this longitudinal gate is informative.
