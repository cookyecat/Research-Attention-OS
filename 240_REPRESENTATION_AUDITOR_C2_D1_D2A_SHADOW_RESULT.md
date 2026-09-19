# RAOS Representation Auditor V0.1 — C2/D1/D2A Shadow Implementation Result

Status: **DOGFOOD DEPLOYED / SHADOW ONLY / E AUTHORITY NOT ENABLED**  
Date: 2026-09-19

## 1. Scope completed

This implementation executes the first reviewed slices of `237_REPRESENTATION_AUDITOR_V01_PREREGISTRATION.md`:

```text
C2 — Representation audit substrate
D1 — EventEvidenceFrame persistence
D2A — Frame-aware shadow same-event candidate retrieval
```

It deliberately does not implement D3 semantic adjudication or any E-stage authority.

Frozen non-goals remain:

```text
no authoritative SAME_EVENT
no automatic Event merge/split
no decision_representation_digest change
no Coverage → P authorization
no Core mathematics change
```

## 2. Persistence substrate

Five append-oriented objects were added:

```text
EventEvidenceFrame
RepresentationAuditRun
EventRevision
EventLineage
EventMembershipAssertion
```

Current `Event / EventSource / SourceEdge` remain the existing materialized representation.

No Workspace entity, CandidateSet entity, AuthorityHome entity, or additional truth store was introduced.

All new records use UUID identity and carry a lightweight `workspace_id` boundary (`local-default` in current single-user dogfood). Authority-bearing history objects also have fields for authority epoch / execution provenance where applicable.

## 3. D1 EventEvidenceFrame

`backend/app/services/event_evidence_frames.py` persists the event proposition currently exposed by production extraction as an immutable shadow frame.

Current extraction still emits at most one event proposition per analyzed Source, so D1 currently materializes one frame per AnalysisRun/Source. The persistence contract itself supports 0..N frames and does not encode one-Source-one-Event as an invariant.

Frame payload preserves:

```text
Source identity / metadata
event title / summary
persisted Claim evidence
persisted Observation evidence
semantic provenance
structured slots reserved for later event-frame extraction
```

Crucially, frame existence does not imply semantic authority.

Legacy extraction is explicitly marked:

```text
mode = LEGACY_EXTRACTION
authority = UNAUDITED_LEGACY
```

Audited extraction bridge output is marked separately:

```text
mode = AUDITED_BRIDGE
authority = SEMANTIC_AUDITED
```

The digest is therefore named `semantic_input_digest`, not `semantic_audit_digest`.

Frame persistence is idempotent for the same AnalysisRun / Source / contract / frame digest.

## 4. D2A frame-aware shadow retrieval

`same_event_candidates()` remains a high-recall, non-authoritative retriever.

Existing fallback remains:

```text
source title similarity + time proximity
```

When both Sources have EventEvidenceFrames, retrieval additionally consumes frame text:

```text
Source title evidence
+ EventEvidenceFrame event title/summary/claim text
+ time proximity
```

The result exposes:

```text
authority = NONE
mutates_graph = false
candidate_set_digest
retrieval_method
frame_evidence
retrieval feature values
```

Candidate-set churn does not affect `graph_digest` or `decision_representation_digest`.

Frame lookup was implemented as one batched query rather than one query per candidate, avoiding an N+1 retrieval path.

Qwen3-Embedding-0.6B remains architecturally reserved for high-recall candidate generation. This slice does not add a new vector entity or make embedding similarity authoritative.

## 5. Consistency substrate

`backend/app/services/representation_consistency.py` adds the first graph-level invariant check: EventLineage transitions that would create a cycle are rejected.

Broader E-stage global consistency checks remain deferred until authority-bearing transitions exist. No speculative corner-case machinery was added.

## 6. Schema migrations

Added:

```text
0014_representation_auditor_substrate
0015_event_frame_semantic_input_digest
```

`0014` creates the five Representation Auditor tables.

`0015` is an idempotent compatibility migration added after rollout smoke detected a naming drift between an already-applied 0014 live schema and the amended model field name. It renames the old column only when needed and no-ops when `semantic_input_digest` already exists.

This incident validated the rollout discipline: migration was tested against a copy of the real 0013/0014 dogfood database, not only `Base.metadata.create_all()` test databases.

## 7. Validation

Focused Representation / Landscape / candidate tests:

```text
16 passed
```

Pipeline / analysis regression:

```text
44 passed
```

Post-fix targeted regression:

```text
18 passed
```

Pipeline + frame integration:

```text
9 passed
```

Full backend regression after the implementation changes:

```text
860 passed
63 skipped
1 known failure
```

The only full-suite failure remains the pre-existing Case-K urgency residual:

```text
expected PREEMPT
actual PRIORITY
```

No new Representation Auditor regression remains.

## 8. Dogfood rollout

Before migration, the SQLite WAL was checkpointed and a backup was created in `/tmp`.

Dogfood schema is now at:

```text
0015_event_frame_semantic_input_digest
```

`research-dogfood-v1.yaml` minimum schema declaration was updated accordingly.

Runtime after rollout:

```text
backend      RUNNING
acquisition  RUNNING
delivery     RUNNING
frontend     RUNNING
backend_health = ok
frontend_health = ok
overall = READY
purpose = CANONICAL
attestation = ATTESTED
mismatches = []
```

Live same-event candidate API smoke returned:

```text
authority = NONE
mutates_graph = false
candidate_set_digest length = 64
HTTP 200
```

At rollout verification time there were zero EventEvidenceFrames in the dogfood database because no successful new cognition had completed after the schema upgrade. No artificial Source/AnalysisRun was inserted merely to manufacture a frame.

Current reconciler failures observed after rollout are unrelated pre-existing operational debt: two Sources have no `content_text` and are being retried. They are not caused by the Representation Auditor schema/path and are intentionally out of scope for this phase.

## 9. Important rollout bug caught and fixed

The first live smoke caught a real code/schema drift:

```text
live 0014 schema: semantic_audit_digest
amended model:    semantic_input_digest
```

This caused ORM reads and the same-event API to return SQLite `no such column` errors.

The runtime was stopped immediately, `0015` was tested against a live database copy, then applied to dogfood. Repeated doctor + ORM + API smoke passed afterwards.

This is exactly the class of silent/late architecture bug the reviewed design is intended to expose early.

## 10. Current implementation boundary

Implemented:

```text
C2 ✅
D1 ✅ (current extractor projection; 0..N contract preserved)
D2A ✅ (frame-aware lexical/time shadow retrieval)
```

Not yet implemented:

```text
D2B embedding-backed frame retrieval calibration
D3 RepresentationEvidenceBundle + semantic shadow Auditor
D4 dogfood calibration corpus
E1 deterministic relation authority gate
```

## 11. Next gate

The next research implementation should be **D3 shadow Representation Auditor**, preceded only by the minimum evidence-bundle assembly needed to make its inputs replayable.

Do not add new canonical entities unless a new irreducible fact cannot be represented by the existing five-object substrate.

Do not enable E-stage authority until D3/D4 dogfood demonstrates that the orthogonal judgments are observable and calibratable.
