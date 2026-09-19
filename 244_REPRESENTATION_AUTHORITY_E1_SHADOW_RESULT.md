# RAOS Topology Commitment Gate E1 — Shadow Simulation Result (historical file name retained)

Status: **SHADOW READY / ZERO REPRESENTATION MUTATION / E2 NOT AUTHORIZED**  
Date: 2026-09-19

## 1. Scope completed

Implemented the first deterministic Representation Authority Gate as shadow simulation only.

```text
Frozen RepresentationAuditRun
+
Frozen deterministic evidence predicates
+
Versioned policy
→ WOULD_AUTHORIZE / CANDIDATE_ONLY / REJECTED / UNRESOLVED
```

No LLM call occurs inside the gate.

No Event/EventSource/EventMembershipAssertion/EventLineage/SourceEdge mutation occurs.

## 2. Directional provenance correction

Implementation exposed a structural omission in D3: `DERIVED_FROM` and `REPOST` are directional, but the original audit schema stored only the relation label.

The Auditor contract now requires:

```text
A_FROM_B
B_FROM_A
NOT_APPLICABLE
UNKNOWN
```

for provenance direction.

A directional provenance relation can never become WOULD_AUTHORIZE without an explicit direction.

## 3. Frozen authority predicate snapshot

Each new audit freezes a compact predicate snapshot in the existing `RepresentationAuditRun.evidence_bundle_refs`.

No new persistence entity was introduced.

Current predicate families:

```text
Source identity
Frame semantic authority
Exact event-semantic fingerprint
Explicit graph facts + authority eligibility
Origin Phase13 execution identity
```

The snapshot has its own digest. Missing/tampered/unsupported predicate snapshots fail closed.

Historical pre-E1 audits are not rewritten.

## 4. Deterministic policy

Current policy:

```text
representation-authority-shadow-v0.2
```

Key SAME_EVENT rule:

```text
Auditor SAME_EVENT
+ FRAME_A & FRAME_B support
+ no cited conflict
+ both frames SEMANTIC_AUDITED
+ origin CANONICAL / ATTESTED
+ same ExternalInformationItem
+ same canonical URL
+ exact audited event-semantic fingerprint
→ WOULD_AUTHORIZE
```

All weaker cross-publication SAME_EVENT cases remain CANDIDATE_ONLY.

DIFFERENT_EVENT currently has no authoritative negative-pair projection and remains CANDIDATE_ONLY.

RELATED / UNRELATED remain semantic/navigation judgments only.

INDEPENDENT remains unavailable without positive independence evidence.

## 5. Real seed simulation

D4 seed corpus under:

```text
representation-auditor-frame-pair-v0.7
```

remains:

```text
9 / 9 pass
```

E1 result over the same nine real cases:

```text
event_identity:
  CANDIDATE_ONLY = 9

provenance_dependency:
  UNRESOLVED = 9

relation_context:
  CANDIDATE_ONLY = 9

WOULD_AUTHORIZE = 0
```

Zero authority yield is an acceptable and expected result.

## 6. Real-flow probe

The 12-pair D2/D3 real-flow probe remains stable after the SourceGraph authority correction:

```text
12 selected
12 valid
0 failed

event_identity:
  DIFFERENT_EVENT = 10
  SAME_EVENT = 2

provenance:
  UNKNOWN = 12

relation_context:
  RELATED = 8
  UNRELATED = 4
```

## 7. Positive-anchor coverage study

Dogfood currently contains:

```text
24 multi-version ExternalInformationItems
12 multi-version pairs with audited Frames
20 cross-version FramePairs scanned
```

Under the initial exact predicate:

```text
same ExternalInformationItem
+ same canonical URL
+ exact audited event semantic fingerprint
```

the number of real strong-anchor pairs is:

```text
0
```

Inspection shows why: later Source versions often expose fuller text and the audited semantic projection can change granularity, split one prior frame into multiple frames, or rephrase actors/actions.

This is evidence that exact semantic fingerprint equality is a useful strong predicate but not a general same-event primitive.

The policy is intentionally not relaxed to fuzzy similarity.

## 8. Content-identity authority leak discovered during E1

The provenance study exposed 142 historical `REPOSTS / METADATA` edges.

137 were generated from metadata-only Bilibili placeholder/teaser content sharing the same content hash.

These edges are now quarantined from current authority without destructive deletion.

See:

```text
243_CONTENT_IDENTITY_AUTHORITY_QUARANTINE_RESULT.md
```

Impact:

```text
REPOSTS total        142
authority eligible     5
quarantined          137

Sources with outgoing decision-relevant secondary facts:
old 48
new 4

Sources whose relational facts change:
44
```

## 9. Contract versions after the authority fix

```text
EventEvidenceFrame:
  event-evidence-frame-v0.2

RepresentationEvidenceBundle:
  representation-evidence-bundle-v0.3

Representation Auditor:
  representation-auditor-frame-pair-v0.7

Authority predicates:
  representation-authority-predicates-v0.2

E1 shadow policy:
  representation-authority-shadow-v0.2
```

## 10. Validation

Focused Representation / SourceGraph / WATCH / Landscape / E1 suite:

```text
72 passed
```

Final full backend regression including the read-only authority-simulation API:

```text
882 passed
63 skipped
1 known Case-K failure
```

The known residual remains:

```text
expected PREEMPT
actual PRIORITY
```

## 11. Live dogfood validation

Runtime after restart:

```text
overall = READY
purpose = CANONICAL
attestation = ATTESTED
mismatches = []
```

Live v0.7 audits expose E1 reason codes through the read-only Representation audit API. The metadata-only Bilibili quarantine smoke returns zero Coverage peers and one independent Source, confirming the historical false REPOST no longer affects current authority.

## 12. Current research boundary

E1 is **SHADOW READY** as a deterministic simulator.

E2 is **not authorized**.

The absence of real WOULD_AUTHORIZE examples is itself a useful result: current deterministic evidence does not yet justify high-precision Event identity authority across normal independent publications.

## 13. Next research gate

Do not loosen the gate with embedding or generic similarity thresholds.

E1.1 was subsequently executed as a bounded corroboration study and closed without changing authority policy. See `245_REPRESENTATION_AUTHORITY_E11_CORROBORATION_RESULT.md`.

The reopening condition is now evidence-contract based rather than benchmark-size based.

Do not continue calibrating larger ad hoc SAME_EVENT corpora under the current EventEvidenceFrame contract. Reopen only if Semantic Perception independently gains a source-grounded, audited identity anchor that is useful to world representation beyond this authority experiment — for example an audited temporal anchor or stable external object identifier.

Only after such evidence exists and survives bounded positive/hard-negative calibration should E2 write EventMembershipAssertion.
