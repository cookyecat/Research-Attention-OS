# Phase 17 — Event State Model Review + Jev Longitudinal Benchmark V0.1

Status: **BENCHMARK FIXTURE RETAINED / STATE DESIGN REFINED BY 269 + 271**  
Date: 2026-09-21

## 1. Why this review exists

Phase16C made both world representation identity and current Attention identity Event-centric.

The next question is not "how many historical claims can an Event hold?" It is:

> What is the smallest orthogonal Event representation that is sufficient for repeated world-state updates and Event-level decision recomputation?

This review deliberately separates the Event data model from any particular update algorithm.

## 2. Minimal Event representation

For RAOS V1.x, model one committed Event hypothesis as:

```text
Event_t
= Identity
+ Current EventState
+ History refs
```

Current EventDecision is NOT part of the Event representation:

```math
D_t = F(S_t, K_t, C_t)
```

and Attention is a later policy projection:

```math
A_t = G(D_t, D_{t-1}, C_t)
```

This preserves:

```text
Evidence / History
!=
Current EventState
!=
EventDecision
!=
Attention
```

## 3. Event Identity Descriptor

The identity descriptor answers:

> What real-world episode/story is this Event hypothesis about?

Minimal V1 fields:

```text
actors / subjects
main action / episode
object / target
time context
optional location
optional event type
```

Important:

- not every field must be observed in the first Source;
- title and summary are renderings/descriptions, not ontology-defining identity keys;
- Claim count never defines Event count;
- one coarse Event may contain many atomic transitions if they belong to one editorial episode/story.

The stable RAOS Event UUID is the identity of the committed Event hypothesis, not proof of objective world truth.

## 4. Probabilistic Event identity is external to the Event row

Whether candidate A and existing Event B are the same world Event is a relational epistemic hypothesis:

```math
H_{same}(A,B)
```

with conceptual belief:

```math
P(H_{same}(A,B)=1 \mid Evidence)
```

This probability must NOT be stored as a universal `Event.confidence` field.

It belongs to the Representation / Event Resolver relation between two hypotheses.

Therefore:

```text
Event representation
!=
P(Event A is Event B)
```

The Event Resolver may use probabilistic belief, model judgments, or future calibrated estimators, but topology commitment remains a separate decision:

```text
belief about SAME_EVENT
-> commitment policy
-> SAME / DIFFERENT / UNCERTAIN
```

The current `llm-coarse-event-resolver-v1` is an operational resolver, not a calibrated probability estimator.

## 5. Current EventState

Current EventState is the smallest decision-relevant sufficient representation of the Event at time t.

Review conclusion: split it into two orthogonal parts.

### 5.1 WorldState

What RAOS currently believes about the Event itself:

```text
what happened / is happening
current episode progress
current mechanism / properties
current results / consequences
current status
```

Examples:

```text
model announced
launch completed
paper released
rollout paused
benchmark independently reproduced
```

### 5.2 EvidenceState

What RAOS currently knows about the support structure for that WorldState:

```text
which sources support it
source independence / provenance dependence
first-party vs secondary evidence
breadth of corroboration
conflict / uncertainty structure
evidence maturity / technical depth
```

EvidenceState is NOT just "number of Sources".

Two reposts may add almost no independent evidence.

One high-quality first-party technical presentation may materially change EvidenceState even if WorldState barely changes.

Thus:

```text
EventState_t
= WorldState_t + EvidenceState_t
```

## 6. Event History

History is append-only audit memory:

```text
all accepted Sources
all audited semantic evidence
EventEvidenceFrames
EventRevisions
membership assertions
representation judgments
historical Event decisions
```

History is preserved so RAOS can explain and audit how it reached the current state.

But by default:

```text
EventHistory_t != EventState_t
```

and cognition should not assume:

```text
Decision_t = F(all historical evidence)
```

The current EventState is the sufficient current representation; history is available for audit, deep verification, and state reconstruction.

## 7. Update operator U is algorithm, not Event ontology

The abstract evolution law is:

```math
S_{t+1} = U(S_t, e_{t+1})
```

where `e_{t+1}` is newly admitted audited evidence.

Terms such as:

```text
corroboration
enrichment
correction
supersession
contradiction
```

may be useful internal relations for one implementation of U.

They are NOT required fields of the Event data model.

Different algorithms may implement U differently while sharing the same Event representation.

Candidate algorithms include:

```text
A. Latest Source baseline
B. Full History Bag baseline
C. Incremental Event State
D. Recency / sliding evidence
E. Explicit transition / supersession logic
C + E. Incremental state with explicit transition semantics
```

The benchmark should choose among algorithms; the ontology should not pre-select one.

## 8. High-level invariants for any update algorithm

These invariants are intentionally algorithm-independent.

### I1. History conservation

Accepted evidence/history is not silently deleted merely because Current EventState changes.

### I2. Current-state sufficiency

For ordinary online decision recomputation, Current EventState should contain the decision-relevant present representation.

The system should not need to replay the entire historical bag on every arrival merely to know the current state.

### I3. Identity / state orthogonality

Evidence that two Sources refer to the same Event is separate from the contents/state of that Event.

`P(SAME_EVENT)` cannot substitute for WorldState or EvidenceState.

### I4. Evidence idempotence

Replaying the same admitted evidence must not keep changing EventState or repeatedly escalating Attention.

### I5. Temporal consistency, not accidental arrival-order dependence

If the same evidence set arrives in a different transport/ingestion order, the final state should be stable whenever the evidence itself carries the same semantic/temporal relations.

True temporal updates still matter: a correction after an earlier claim is not semantically equivalent to the reverse chronology.

### I6. Decision separation and bounded attention

EventState is user/cognition-independent world representation.

Decision is computed separately relative to Kernel/context.

Repeated redundant evidence must not make Attention increase without bound merely because history grows.

These six are the V0.1 design invariants.

They do NOT require a specific `correction` or `contradiction` field in EventState.

## 9. Current physical schema review

Current `Event` already has a useful identity skeleton:

```text
actors
action
object
occurred_at
time_context
location
event_type
```

and renderings:

```text
title
summary
```

Current gaps for longitudinal state:

```text
current_state: string
attributes: untyped JSON catch-all
confidence: ambiguous scalar
```

Review conclusion:

- `current_state` is too weak for the long-term dynamic-state contract;
- `attributes` should not become an unbounded hidden ontology;
- `confidence` must never be interpreted as `P(Event A is Event B)`.

Do NOT immediately add algorithm-specific columns.

Before productionizing Phase17, introduce one versioned structured EventState contract containing:

```text
world_state
evidence_state
```

with current string summary retained only as rendering/compatibility if needed.

`EventRevision` can remain the append-only state/history record; no new EventDecision table is required.

## 10. Jev Longitudinal Benchmark V0.1

This fixture is based on the user's real observed attention evolution over several days.

It is a longitudinal Attention benchmark, not a factual benchmark about every technical claim concerning Jev.

The fixed target Event is:

```text
Event:
Jev model launch / emergence and early validation episode
```

Expected identity behavior:

```text
t0, t1, t2, t3
-> SAME coarse Event
```

### t0 — weak launch signal

Observed input:

```text
one brief Weibo Source
simple introduction
little technical depth
little independent evidence
```

State interpretation:

```text
WorldState:
  Jev exists / has launched

EvidenceState:
  one weak secondary signal
  low technical depth
  low corroboration
```

Human Gold for `profile=user-primary-v0.1` (subjective):

```text
AWARE
```

### t1 — broad independent attention

New inputs:

```text
many X discussions / analyses
broader cross-platform discussion
Chinese technical media coverage
```

State interpretation:

```text
WorldState:
  core launch identity mostly unchanged

EvidenceState:
  source breadth increases
  independent discussion increases
  external attention momentum increases
  technical analysis depth increases
```

Human Gold for `profile=user-primary-v0.1` (subjective):

```text
WATCH
```

### t2 — author presentation / mechanism explanation

New input:

```text
author presentation explains the model/mechanism in more depth
```

State interpretation:

```text
WorldState:
  mechanism description becomes richer / less uncertain

EvidenceState:
  first-party evidence increases
  technical depth increases
```

Human Gold for `profile=user-primary-v0.1` (subjective):

```text
WATCH
```

The model is more understandable, but strong external validation is still not established.

### t3 — strong independent performance evidence

New input:

```text
strong independent performance / workflow evidence appears
```

State interpretation:

```text
WorldState:
  practical capability / performance evidence becomes materially stronger

EvidenceState:
  independent validation increases
  practical credibility increases
```

Human Gold for `profile=user-primary-v0.1` (subjective):

```text
ENGAGE
```

Fixed profile-scoped Human Gold trajectory:

```text
AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

## 11. Why this benchmark is valuable

It tests a pattern that article-level classification cannot represent well:

```text
same Event identity
+ changing WorldState / EvidenceState
-> changing EventDecision
-> changing Attention lifecycle
```

It also distinguishes several failure modes:

```text
Latest Source only
-> may forget cumulative evidence

Full History Bag
-> may retain obsolete claims as if still current

Pure Source count
-> mistakes repost volume for independent support

Monotonic accumulation
-> may eventually ENGAGE everything

Static Event summary
-> cannot represent evolving evidence quality
```

## 12. Benchmark gates

### Gate A — Event identity

All four epochs should resolve to the same coarse Event under Event V1.

This can be tested immediately with the current Event Resolver.

### Gate B — State representability

All four epochs must be representable using only:

```text
Identity
WorldState
EvidenceState
History refs
```

without adding algorithm-specific ontology fields.

### Gate C — profile-scoped Attention trajectory

For `profile=user-primary-v0.1`, a candidate update algorithm may be compared against the recorded Human Gold when, under that same fixed Kernel/context, it reproduces:

```text
AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

for the right reasons.

### Gate D — invariants

Replay, order, provenance-dependence and redundant-evidence controls must satisfy I1-I6.

## 13. Phase17 working hypothesis

The leading candidate remains:

```text
Incremental Event State
+
explicit transition/supersession semantics where needed
```

but this is an algorithm hypothesis, not a canonical ontology decision.

Phase17 should ablate algorithms against the same Jev fixture before production wiring.
