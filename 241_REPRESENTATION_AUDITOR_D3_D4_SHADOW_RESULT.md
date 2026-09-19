# RAOS Representation Auditor D3/D4 — Shadow Calibration Result

Status: **SHADOW READY / E AUTHORITY NOT ENABLED**  
Date: 2026-09-19

## 1. Scope

This closes the first research loop for:

```text
D1 — audited 0..N EventEvidenceFrames
D2 — Source retrieval → FramePair candidate expansion
D3 — shadow FramePair Representation Auditor
D4 — seed calibration + real-flow shadow probe
```

No authoritative Event membership, merge, split, SourceEdge promotion, Coverage→P authorization, or Attention behavior is changed.

## 2. D1 correction: reuse the existing audited event projection

The production research-aligned extraction bridge already emits 0..N audited event projections with:

```text
actor_objects
actions_changes
affected_systems_populations
uncertainties
support ids
audit status
```

Therefore EventEvidenceFrame V0.2 reuses those projections instead of inventing a second event extractor.

Legacy extraction retains a single fallback frame only for compatibility and remains explicitly marked UNAUDITED_LEGACY.

Historical immutable AnalysisRuns were append-only backfilled without re-running cognition:

```text
547 completed AnalysisRuns
494 research-aligned bridge runs
299 runs with audited events
426 audited EventEvidenceFrames
298 Sources represented
55 multi-frame AnalysisRuns
```

## 3. D2: no representative-frame collapse

Source-level retrieval remains high-recall and non-authoritative.

A candidate Source pair is expanded into all latest Frame↔Frame pairs:

```text
Source A with m frames
×
Source B with n frames
→ m × n FramePair candidates
```

Intra-Source frame pairs are also exposed because one article can contain multiple distinct event propositions.

Source retrieval rank and frame similarity remain separate observable retrieval signals.

Permanent semantics:

```text
authority = NONE
mutates_graph = false
```

## 4. D3 FramePair Auditor

Current orthogonal dimensions:

```text
event_identity
  SAME_EVENT | DIFFERENT_EVENT | UNCERTAIN

provenance_dependency
  REPOST | DERIVED_FROM | INDEPENDENT | UNKNOWN

relation_context
  RELATED | UNRELATED | UNCERTAIN
```

These dimensions are semantically irreducible.

The immutable RepresentationEvidenceBundle is a computation object, not a persistence entity. RepresentationAuditRun remains the one persisted audit history object.

## 5. Code-level constitution

The following are enforced outside the model prompt:

```text
unknown evidence id
→ FAIL CLOSED

decisive judgment without support_ids
→ FAIL CLOSED

similarity-only SAME_EVENT
→ FAIL CLOSED

DIFFERENT_EVENT without both frames
→ FAIL CLOSED

INDEPENDENT without positive independence evidence
→ FAIL CLOSED

same canonical URL
→ Source identity/versioning case
→ provenance_dependency defaults UNKNOWN
```

This prevents fluent but ungrounded model output from becoming a persisted audit judgment.

## 6. Phase13 execution integrity validation

Two attempted direct shell runs were correctly blocked:

```text
UNATTESTED_NO_IDENTITY
ATTESTED but missing llm_api_key capability
```

Only the same canonical research-dogfood-v1 runtime identity/capabilities used by the backend were allowed to execute real shadow audits.

## 7. Auditor contract evolution

Real dogfood produced useful contract failures:

```text
v0.1: model omitted evidence ids
v0.2: schema repair still failed
v0.3: natural support_ids / conflict_ids contract adopted
v0.4: Source identity/versioning boundary fixed
v0.5: RELATED tightened from broad topic similarity to concrete world relation
```

The contract was tightened rather than weakening evidence requirements.

## 8. RELATED boundary

V0.5 requires a concrete relation such as:

```text
same concrete actor/object/product/system/ongoing episode
explicit cross-reference
direct causal / response / follow-up / update relation
```

Broad domain overlap is insufficient:

```text
both are AI
both involve agents
both are technology news
≠ RELATED
```

## 9. Seed calibration corpus

The seed architecture-regression corpus now contains 9 real cases.

Result:

```text
representation-auditor-frame-pair-v0.5
9 cases
9 pass
0 fail
```

It includes:

```text
same-event same-resource
same-event cross-source
related different-event
same-actor/product-family hard negative
unrelated retrieval false positive
same-source multi-event
same-source framework vs case-study
same-domain unrelated hard negatives
```

This is a regression seed, not a comprehensive benchmark.

## 10. Unlabeled real-flow probe

A second 12-pair probe was sampled from the actual D2 FramePair candidate stream.

V0.5:

```text
selected = 12
constitution-valid = 12
fail = 0

event_identity:
  DIFFERENT_EVENT = 10
  SAME_EVENT = 2

provenance_dependency:
  UNKNOWN = 12

relation_context:
  RELATED = 8
  UNRELATED = 4
```

V0.4 had classified all 12 as RELATED. The four V0.5 UNRELATED pairs are the cases with only broad AI/agent thematic overlap, which is the intended correction.

## 11. Validation and rollout

Focused D3/D4 path:

```text
21 passed
```

Full backend regression after D3/D4:

```text
868 passed
63 skipped
1 known failure
```

The only failure remains the pre-existing Case-K urgency residual:

```text
expected PREEMPT
actual PRIORITY
```

Runtime restart/live smoke:

```text
overall = READY
purpose = CANONICAL
attestation = ATTESTED
mismatches = []

same-event-frame-candidates:
  authority = NONE
  mutates_graph = false
  frame-pair digest present

representation-audits:
  live persisted v0.5 audits visible
  authority_result = SHADOW_ONLY
```

## 12. Research conclusion

D3/D4 are now **SHADOW READY**.

This does not justify E-stage authority.

The next research gate is a deterministic, replayable E1 Authority Gate in simulation mode:

```text
Frozen RepresentationAuditRun
+
Frozen deterministic evidence predicates
+
Versioned relation-specific policy
+
Phase13 execution identity
→ WOULD_AUTHORIZE / CANDIDATE_ONLY / REJECTED / UNRESOLVED
```

No representation mutation is permitted during E1 shadow simulation.
