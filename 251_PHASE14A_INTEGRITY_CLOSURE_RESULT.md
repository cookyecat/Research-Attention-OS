# Phase 14A — Integrity Closure Result

Status: **CLOSED / BOUNDED REVIEW COMPLETE / DOGFOOD PATCHED**  
Date: 2026-09-19

## 1. Scope and stop condition

Phase 14A performed one bounded inventory of authority-bearing canonical mutation paths.

Reviewed classes:

- Event / EventSource materialized topology;
- SourceEdge decision-relevant manual mutation;
- AttentionPlan / WATCH;
- Kernel mutation;
- Delivery mutation;
- Agent-originated canonical writes.

Append-only observation/evidence persistence was explicitly excluded from blanket blocking.

## 2. Critical distinction

Phase13 gates **authority-bearing canonical side effects**, not every database write.

Observation/evidence paths such as Source, Snapshot, ParserRun, parser CITES, Claim, Observation and forensic AnalysisRun artifacts may remain persistable when their contract allows it.

They must not silently mutate decision-bearing topology or action state.

## 3. Findings and repairs

### Agent / WATCH

Direct Agent and ordinary WATCH mutation paths previously lacked an explicit Phase13 side-effect gate.

`require_side_effects_authorized()` now gates direct WATCH create/cancel, active-acquisition activation and trigger firing.

### Forensic Event topology contamination

REPLAY/FORENSIC cognition previously called `attach_or_create_event()` before Attention authority was checked.

This could create Event/EventSource rows that later appear in graph_digest even though the run had no side-effect authority.

`extract_source()` now accepts `materialize_event_topology`; `run_pipeline()` sets it from Phase13 side-effect authority.

REPLAY/FORENSIC may still persist Claims, Observations, Inferences, EvidenceLinks, AnalysisRun and EventEvidenceFrame evidence, but new Claim/Observation rows are not bound to materialized Events and Event/EventSource counts do not change.

### Direct Kernel mutation

Direct Kernel seed/node/patch mutation endpoints now require Phase13 side-effect authority.

### Direct Delivery mutation

Delivery acknowledge/dismiss and realtime WebSocket delivery-state mutation now require Phase13 side-effect authority. The delivery worker already had its own authority check.

### Manual SourceEdge mutation

`POST /sources/source-edges` can manufacture decision-relevant representation relations and now requires Phase13 side-effect authority.

Parser-extracted CITES remains Epistemic observation/provenance and is not blocked.

## 4. What was deliberately not gated

Phase 14A did not gate ordinary Source/Snapshot acquisition, parser CITES extraction, Claim/Observation evidence, or forensic AnalysisRun persistence.

Doing so would violate `Observe broadly` and conflate evidence persistence with decision authority.

## 5. Validation

Focused Phase13 / Agent / Representation Snapshot regression after the final repairs:

`30 passed`.

Representative negative tests prove that REPLAY cannot create WATCH state, Agent WATCH state, Event/EventSource topology, Kernel nodes, manual SourceEdges, or Delivery acknowledgements.

## 6. Stop condition

Phase 14A is closed.

Do not continue scanning arbitrary persistence code for hypothetical authority problems. Reopen only when a new authority-bearing mutator is introduced or dogfood exposes a concrete bypass.

## 7. Final validation

Final backend regression after restoring the unchanged public extraction diagnostics contract:

`900 passed / 63 skipped / 1 known Case-K failure`.

The only failure remains the historical PREEMPT expected vs PRIORITY actual residual.

After restart, runtime doctor reports CANONICAL / ATTESTED / READY with no mismatches. Read-only Agent capabilities, Delivery listing, and Representation belief surfaces remain healthy.
