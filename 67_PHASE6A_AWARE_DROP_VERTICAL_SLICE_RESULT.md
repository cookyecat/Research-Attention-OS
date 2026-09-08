# Phase 6A — Raw Source → AWARE/DROP Vertical Slice Result

Status: **PHASE 6A COMPLETE / WORKING END-TO-END BASELINE / DEVELOPMENT-ONLY**
Date: 2026-09-08

This archive records the first executable RAOS vertical slice from real raw sources through:

```text
Raw Source
→ Semantic Sensor v0.2.3
→ Semantic Evidence Auditor v0.1.1
→ Audited Semantic Representation
→ D v4 / S v1 / P v1
→ production Scheduler / Attention Policy
→ AWARE / DROP
```

No Human Gold is attached to this round. It is not fresh validation evidence.

## Canonical implementation / measurement SHAs

Phase 6A full-channel implementation commit:

```text
7cbbe2688f67405bb6e64aeee78978a40560abf5
```
Canonical semantic-only artifact:

```text
eval/live/results/phase6a_aware_drop_vertical_slice_v0_1/
phase6a_aware_drop_vertical_slice_v0_1_20260908T003637Z.json
measurement_git_head = 7cbbe2688f67405bb6e64aeee78978a40560abf5
```

Canonical context-envelope artifact:

```text
eval/live/results/phase6a_aware_drop_vertical_slice_v0_1_1/
phase6a_aware_drop_vertical_slice_v0_1_1_20260908T003719Z.json
measurement_git_head = 7cbbe2688f67405bb6e64aeee78978a40560abf5
```

Focused stability probe implementation / measurement:

```text
runner commit = dd71f13eafaeed5652c36e5cf05633c7adef64d6
artifact = eval/live/results/phase6a_context_envelope_stability_v0_1/
           phase6a_context_envelope_stability_v0_1_20260908T004033Z.json
```

## Component policy

```text
Sensor       DeepSeek Pro / bounded v0.2.3
Auditor      DeepSeek Flash / v0.1.1
D            DeepSeek Pro / profile v4
S            DeepSeek Flash / v1
P            DeepSeek Flash / v1
Policy       production Scheduler
```
## 1. Raw-source routing result

The Sensor produced:

```text
RS11 → 2 Event Frames
RS12 → 5 Event Frames
RS15 → 1 Event Frame
RS05 → 0 Event Frames
```

This is the desired architectural split:

```text
news / release / industry events → attention-world event path
technical tutorial              → cognitive / Delta path
```

RS05 was not forced into the no-Delta event gate.

## 2. Auditor result

Across 8 Event Frames:

```text
36 provenance edges
32 scorable
17 SUFFICIENT
15 INSUFFICIENT
4 no-cited-evidence
8 / 8 events remained ROUTABLE
```

The Auditor rejected many actor/system scope expansions while retaining at least one supported action/change per event.

This is a useful regulator behavior, not an Auditor accuracy score.
## 3. First full Attention Policy run

Semantic-only audited representation (`v0.1`) achieved:

```text
8 / 8 events scorable
8 / 8 gate_wiring_matches = true
production Scheduler executed for every event
```

Canonical outcome:

```text
AWARE 0
DROP  8
```

This exposed a system-level interface residual: locally valid Auditor filtering had removed context needed by downstream D/S.

Observed examples:

```text
RS12-E1: robotics competition context thinned → D OUT
RS12-E2: autonomous robot task context thinned → D OUT
RS11-E1: evidence needed to judge market/technical consequence omitted → S NOT_MATERIAL
```

Key lesson:

> **Local correctness does not imply system correctness.**
## 4. Controlled interface repair — audited context envelope

The repair does **not** restore rejected semantic objects and does **not** retrieve new evidence.
It preserves only source excerpts already attached to Auditor edges whose verdict is `SUFFICIENT`.

Working interface:

```text
Audited Semantic Representation
=
admitted semantic objects
+
their already-admitted evidence context
```

Invariant:

> **Context preservation != semantic repair.**

After this change (`v0.1.1`):

```text
8 / 8 events scorable
8 / 8 gate_wiring_matches = true
AWARE 2
DROP  6
```

Material component changes included:

```text
RS11-E1: S NOT_MATERIAL → MATERIAL; final DROP → AWARE
RS11-E2: D OUT → IN in the canonical paired run; final DROP → AWARE
RS12-E1: D OUT → IN; final remains DROP because S=NOT_MATERIAL
RS12-E2: D OUT → IN; final remains DROP because S=NOT_MATERIAL
```
## 5. Focused stability result

RS11-E1 / RS11-E2 were repeated 3 times per representation condition.

RS11-E1:

```text
SEMANTIC_ONLY
D = IN          3/3
S = MATERIAL    2/3
S = NOT_MATERIAL 1/3

SEMANTIC_PLUS_ADMITTED_EVIDENCE
D = IN          3/3
S = MATERIAL    3/3
```

RS11-E2:

```text
SEMANTIC_ONLY
D = IN       3/3
S = MATERIAL 3/3

SEMANTIC_PLUS_ADMITTED_EVIDENCE
D = IN       3/3
S = MATERIAL 3/3
```

Thus the context envelope is not justified by a single lucky flip. On RS11-E1 it improved downstream consequence-judgment stability, while RS12-E1/E2 independently showed repeatable restoration of robotics-domain context across the exploratory and canonical full runs.
## 6. Remaining known residual

RS12-E5 remains:

```text
D = OUT
S = NOT_MATERIAL
P = SALIENT
Final = DROP
```

The admitted action evidence states only that cumulative deliveries are near 10,000 units. It does not itself identify OmniHand or robotics. The Sensor created actor/product attribution using context not present in that cited evidence, and the Auditor correctly rejected those objects.

Therefore:

```text
RS12-E5 root cause
= upstream Sensor provenance insufficiency
!= Auditor context-envelope failure
```

The final action is currently masked by `S=NOT_MATERIAL`, so this residual is recorded but not optimized now.

## 7. Phase 6A decision

```text
Raw Source → Sensor                         PASS
Sensor event/non-event routing              PASS
Sensor → Auditor                            PASS
Auditor local evidence gate                 WORKING BASELINE
Audited representation context envelope     ACCEPTED WORKING INTERFACE
D/S/P end-to-end execution                  PASS
Controlled P wiring                         PASS
Frozen no-Delta gate                        PASS
Production Scheduler / Attention Policy     PASS
AWARE / DROP vertical slice                 COMPLETE
```

Phase 6A is **CLOSED FOR CURRENT DEVELOPMENT PURPOSES**.

Next frontier:

```text
Phase 6B — Audited Semantics + Cognitive Kernel → Delta → Attention Policy
```
