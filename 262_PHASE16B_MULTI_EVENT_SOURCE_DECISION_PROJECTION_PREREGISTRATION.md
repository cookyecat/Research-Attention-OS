# Phase 16B — Multi-Event Source Decision Projection Preregistration

Status: **PREREGISTERED / FRAME-CONDITIONED COGNITION PROBE FIRST / NO PRODUCTION MULTI-EVENT ATTENTION YET**  
Date: 2026-09-20

## 1. Problem

Phase16 made current Attention decision identity Event-centric, but current primary analysis still resolves one decision Event per Source.

Representation already permits:

```text
1 Source -> 0..N EventEvidenceFrames
```

Dogfood census:

```text
353 Sources with frames
67 Sources with >1 frame
max 8 frames / Source
```

Sample multi-frame Sources contain genuinely distinct event_key/event_summary pairs.

Therefore `1 Source -> 1 source-local decision Event` is a transitional approximation, not the final ontology.

## 2. Core hypothesis

Existing research-aligned cognition can be reused per EventEvidenceFrame if and only if the frame preserves the audited semantic units and evidence supports originally admitted by the Sensor/Auditor.

Desired composition:

```text
Source
→ Sensor/Auditor
→ 0..N EventEvidenceFrames
→ frame-scoped audited semantic units
→ existing ResearchAligned cognition kernel
→ per-frame decision result
```

No new cognition model is introduced.

## 3. Evidence-binding requirement

`event_summary` alone is insufficient.

Frame-conditioned cognition must retain:

- semantic unit id;
- statement;
- epistemic status;
- confidence;
- support pointers/excerpts;
- Source provenance.

Otherwise Support Binding / Grounding would be weakened relative to the frozen Phase10 contract.

## 4. Engineering change allowed in 16B-A

Persist the already-computed per-Event admitted audited semantic units inside EventEvidenceFrame payload.

This changes frame evidence completeness, not Sensor/Auditor judgment semantics.

Version the EventEvidenceFrame contract.

## 5. Thin adapter

Add a strict in-memory adapter:

```text
EventEvidenceFrame
→ frame-scoped ExtractionResult
```

The adapter must:

- never re-extract Source prose;
- never invent semantic units;
- preserve semantic_unit_id and semantic_supports;
- preserve Event key/title/summary and Source provenance;
- fail closed if audited semantic units are absent.

## 6. Controlled experiment

Use one Source containing two audited Event frames with intentionally different relevance to the current Kernel.

Compare:

```text
whole-Source cognition
frame A cognition
frame B cognition
```

Measure:

- canonical semantic unit ids;
- kernel matches;
- authorized cognitive effects;
- resulting Attention disposition;
- decision-candidate identity that would be required.

## 7. Success criterion

Phase16B advances only if:

1. frame adapter preserves the frozen support-binding semantics;
2. two frames from one Source can produce independently inspectable cognition;
3. no frame decision requires mutation of Source text/history;
4. no production AttentionPlan is created by the probe.

## 8. Stop conditions

Do not switch production to 0..N Event Attention if:

- frame support evidence is incomplete;
- frame-scoped cognition changes semantics relative to Phase10;
- current persistence cannot distinguish frame-local Event identity without a new hidden merge;
- no controlled case demonstrates a meaningful difference from whole-Source cognition.

## 9. Non-goals

- no cross-Source SAME_EVENT commitment;
- no EventLineage authority;
- no topology merge;
- no new EventDecision table;
- no probability calibration;
- no Phase15D resurfacing test yet.