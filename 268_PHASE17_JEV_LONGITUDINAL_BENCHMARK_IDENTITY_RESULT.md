# Phase 17 — Jev Longitudinal Benchmark V0.1 Identity Result

Status: **IDENTITY GATE PASSED / ATTENTION GATE FROZEN, NOT YET CLAIMED**  
Date: 2026-09-21

Reference:
- `267_PHASE17_EVENT_STATE_MODEL_REVIEW_AND_JEV_BENCHMARK.md`
- `eval/live/fixtures/phase17_jev_longitudinal_v0_1.json`

## 1. Fixture

The benchmark fixes one coarse Event:

```text
Jev model launch / emergence and early validation episode
```

and four longitudinal epochs:

```text
t0 weak launch signal                 -> AWARE
t1 broad independent attention        -> WATCH
t2 author mechanism presentation      -> WATCH
t3 strong independent performance     -> ENGAGE
```

The fixture is based on the user's real observed Attention evolution.

It is not a factual benchmark asserting that every technical claim about Jev is objectively true.

## 2. Event identity gate

The configured real Event Processor V1 was run sequentially on the fixed t0..t3 Source descriptions using an in-memory database.

No production Event, AttentionPlan or WATCH was written.

Observed:

```text
t0
expected: first Event creation
observed: DIFFERENT_EVENT / create
PASS

t1
expected: SAME_EVENT
observed: SAME_EVENT
PASS

t2
expected: SAME_EVENT
observed: SAME_EVENT
PASS

t3
expected: SAME_EVENT
observed: SAME_EVENT
PASS
```

Final topology:

```text
4 Sources
-> 1 Event
-> 4 EventSource links
```

Diagnostics:

```text
all_identity_expectations_pass = true
final_event_count              = 1
canonical_event_source_count   = 4
all_four_sources_share_one_event = true
```

Artifact:

```text
eval/live/results/phase17_jev_event_identity_v0_1/
phase17_jev_event_identity_v0.1_20260920T181034Z.json
```

## 3. Interpretation

The result supports the current coarse Event V1 granularity on this longitudinal fixture.

The resolver treated:

- broad discussion after launch;
- an author mechanism presentation;
- later strong independent performance evidence;

as continuation of the same evolving Jev story rather than separate Events.

This is important because the profile-scoped longitudinal Attention benchmark requires one stable Event identity whose state changes over time.

## 4. State-model gate

The fixed fixture represents every epoch using only:

```text
Event Identity
WorldState delta
EvidenceState delta
History / Source evidence
```

No algorithm-specific EventState fields such as:

```text
correction
supersession
enrichment
contradiction
```

are required by the fixture.

Those concepts remain optional internal semantics of a candidate update operator U.

## 5. Profile-scoped Human Gold trajectory gate

Recorded Human Gold for `profile=user-primary-v0.1` (subjective):

```text
AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

This is not a universal normative label; another Kernel/user may legitimately differ.

Status:

```text
FROZEN AS BENCHMARK TARGET
NOT YET CLAIMED AS PASSED
```

Reason:

Phase17 has not yet productionized or selected the final EventState update algorithm.

The benchmark must be used to compare candidate algorithms rather than tuning the fixture to whichever algorithm is currently implemented.

## 6. Next experiment

Ablate at least:

```text
A. Latest Source
B. Full History Bag
C. Incremental Event State
C+E. Incremental Event State + explicit transition/supersession semantics
```

against the same fixed Jev trajectory and the Phase17 invariants.

The leading hypothesis remains C+E, but benchmark results, not ontology design, should decide.
