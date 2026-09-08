# Phase 8C.2 — Production Sensor Bridge Preregistration

Status: **PREREGISTERED / ACTIVE**  
Date: 2026-09-09  
Baseline SHA: `08eb763e99a80ea568198c23be813560507ec0c6`

## 1. Research question

Can the validated Phase 7A semantic path enter the real production analysis pipeline without changing downstream cognition or Attention Policy semantics?

Controlled comparison:

```text
A — legacy production extraction
Raw Source -> provider.extract_information/reason_evidence -> ExtractionResult

B — candidate semantic path
Raw Source -> Semantic Sensor v0.2.6 -> Auditor v0.1.1
           -> audited semantic bridge -> ExtractionResult

A and B -> same production persistence / Locate / Delta / Attention downstream
```

The experiment tests the representation boundary, not a new policy.
## 2. Frozen semantics and controls

The following are frozen for this experiment:

- `Delta`, `D`, `S`, `P`, and Attention Policy definitions;
- production Locate / Impact / Scheduler behavior;
- Kernel fixtures and runtime context within each paired case;
- Sensor v0.2.6 and Auditor v0.1.1 prompts/semantics;
- Auditor `SUFFICIENT` as the only admission criterion.

No Sensor prompt tuning is allowed from Phase 8C.2 outcomes.

The production default remains legacy until the A/B and regression gates pass.

## 3. Bridge composition contract

No new semantic schema will be invented.

```text
event_frames
-> Phase 6A event audit edges
-> SUFFICIENT-only audited event projection

non_event_units
-> Phase 6B epistemic-unit audit/admission

both
-> existing ExtractionResult representation
```
Event safety invariant:

> Sensor `event.summary` remains diagnostic-only. An event may enter downstream only when its audited projection is `ROUTABLE`, and only Auditor-admitted subobjects may be represented.

Epistemic typing must be conservative: the bridge must never upgrade source claims or extractor inferences into direct observations.

## 4. Production seam

`backend/app` must not import `eval/live` candidate modules.

Production will expose only a narrow injectable extraction-bridge interface. The v0.2.6 composition remains in `eval/live` and is passed into production `run_pipeline()` for the experiment.

The bridge execution fingerprint must enter the `AnalysisRun` execution digest. Otherwise A and B could collide in analysis caching and invalidate the A/B.

Default `run_pipeline()` behavior with no bridge must remain legacy-compatible.

## 5. Preregistered cases

Primary heterogeneous development cases:

```text
RS05  non-event performance/profiling causal relation
RS15  non-event collective-intelligence relation
RS11  event + non-event release/news source
RS12  event + non-event interview/robotics source
```
RS05/RS15 are causal decision-bearing probes inherited from Phase 7A. RS11/RS12 are regression controls that also exercise event-frame transport.

These are development cases, not fresh holdout evidence.

## 6. Measurements

For each arm record at minimum:

- exact git SHA and execution fingerprint;
- extracted claim / observation / inference counts;
- Sensor event/non-event counts and Auditor admissions for B;
- event routing/blocking diagnostics for B;
- production Kernel matches;
- primary Delta operation and target;
- final Attention disposition and expected output;
- bridge/pipeline failures separately from semantic disagreements.

Main comparison is downstream decision fidelity and causal direction, not raw unit count or Auditor admission rate.

## 7. Exit / failure criteria

Phase 8C.2 may close with the Sensor path selected as the next production candidate only if:

1. production legacy behavior is unchanged when no bridge is supplied;
2. candidate and legacy traverse the same downstream implementation;
3. A/B runs have distinct, auditable identities;
4. event frames cannot disappear silently at the bridge;
5. RS05/RS15 preserve or improve the established decision-bearing relation rather than regress it;
6. RS11/RS12 do not show a stable new downstream regression attributable to the bridge;
7. relevant regression tests pass on the exact measurement SHA.
A mixed or negative result is still informative. It should block default-path promotion and be attributed to the earliest failing layer rather than repaired by changing downstream policy.

## 8. Research discipline

```text
Perception first.
Representation second.
Decision last.
```

If A and B disagree, inspect the represented external world before judging the Attention action.

Canonical reminder:

> **A semantic label is not a substitute for the relation it summarizes.**

And for this integration specifically:

> **A production bridge is correct only if it transports validated semantics without silently changing what the downstream system is allowed to know.**
