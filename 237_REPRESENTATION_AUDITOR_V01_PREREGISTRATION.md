# RAOS Representation Auditor V0.1 — Preregistration

Status: **PREREGISTERED / REVIEW 1 AMENDED / D3-D4 SHADOW READY / PROBABILISTIC BELIEF VIEW V0.1 ACTIVE / E1 TOPOLOGY-COMMITMENT SHADOW READY / E1.1 CLOSED / E2 TOPOLOGY WRITES NOT AUTHORIZED**  
Date: 2026-09-19

## 1. Purpose

Representation Auditor V0.1 unifies the unfinished halves of the original implementation stages:

```text
C. Provenance/reference extraction and relation auditing
D. Shadow same-event candidate retrieval + semantic adjudication
```

into one representation-authority path.

The goal is not to build a better article classifier. The goal is to let RAOS make auditable, revisable judgments about relationships among Sources, Claims and Event hypotheses while preserving the frozen world-state-centric architecture.

This phase must not change Multi-Delta, Pareto, D/S/P, Attention policy, or Event-level P authority.

V0.1 is deliberately **Event-first**. Existing Claim/Observation semantic auditing remains unchanged; broader Claim-to-Claim / Claim-to-Event representation authority is deferred until the Event relation substrate is calibrated. This prevents the first implementation from widening scope faster than its authority model.

---

## 2. Frozen epistemic semantics

A database `Event` is not objective reality.

```text
World Event
= ontological reality

RAOS Event
= revisable epistemic hypothesis about that reality
```

Therefore:

```text
CANDIDATE Event ≠ CONFIRMED Event
CONFIRMED Event ≠ objectively proven world truth
```

For V0.1:

```text
CANDIDATE
= materialized Event hypothesis that has not been topology-committed as the current operational projection

CONFIRMED
= Event hypothesis currently topology-committed for operational use in the materialized RAOS Event graph

SUPERSEDED
= historically valid RAOS hypothesis replaced by a later correction / merge / split topology
```

A probabilistic epistemic hypothesis may be admitted into canonical World Representation through grounded RepresentationAuditRun history without changing Event.status. Therefore epistemic admission and Event topology commitment are separate concepts.

Reality may be unique while RAOS initially holds multiple hypotheses for the same event, or one hypothesis that later proves to contain multiple events.

Historical evidence and historical Representation Snapshots must never be destructively rewritten to make the past look as if RAOS always knew the current hypothesis.

Permanent invariant:

> **Reality is unique; RAOS representation is revisable.**

---

## 3. Orthogonality principle

Representation relations are not one scalar axis and must not be forced into a single mutually-exclusive class.

```text
SAME_EVENT
DERIVED_FROM
INDEPENDENT_REPORT
OFFICIAL
RELATED
```

cannot be linearly substituted for one another.

For example, two Sources may simultaneously be:

```text
SAME_EVENT
+
DERIVED_FROM
```

or:

```text
SAME_EVENT
+
INDEPENDENT_REPORT
```

or:

```text
CITES
+
RELATED_DIFFERENT_EVENT
```

The Auditor therefore emits orthogonal judgments, but the **scope of each judgment must also be explicit**. Pairwise Source/Frame relations, Source-to-Event membership/role, and Event-to-Event lineage are not the same kind of object.

```text
SourcePair / FramePair Judgment
├─ event_identity
│  ├─ SAME_EVENT
│  ├─ DIFFERENT_EVENT
│  └─ UNCERTAIN
│
├─ provenance_dependency
│  ├─ REPOST
│  ├─ DERIVED_FROM
│  ├─ INDEPENDENT
│  └─ UNKNOWN
│
└─ relation_context
   ├─ RELATED
   ├─ UNRELATED
   └─ UNCERTAIN

SourceEvent Judgment
├─ membership
│  ├─ REPORTS_EVENT
│  ├─ DOES_NOT_REPORT_EVENT
│  └─ UNCERTAIN
│
├─ officiality
│  ├─ OFFICIAL_FOR_REPRESENTED_ACTOR
│  ├─ THIRD_PARTY
│  └─ UNKNOWN
│
├─ reporting_role
│  ├─ PRIMARY_REPORT
│  ├─ SECONDARY_REPORT
│  ├─ COMMENTARY
│  └─ UNKNOWN
│
└─ originality
   ├─ ORIGINAL_CANDIDATE
   ├─ NON_ORIGINAL
   └─ UNKNOWN

EventPair Judgment
└─ topology_relation
   ├─ MERGE_CANDIDATE
   ├─ DISTINCT
   ├─ OVERLAP_UNRESOLVED
   └─ UNCERTAIN
```

The EventPair judgment is a proposal about RAOS hypotheses, not a statement that two ontological world objects have been directly observed.

No dimension may be inferred merely because another dimension has a value.

Here **orthogonal** means semantically / causally irreducible, not statistically independent. Two dimensions may be highly correlated in observed data while still answering different world-model questions. Statistical correlation must never justify collapsing them into one scalar or using one dimension as a linear substitute for another.

This is both an Occam constraint and an authority-safety constraint: keep only irreducible explanatory dimensions and do not collapse causally distinct properties into one score.

---

## 4. Candidate ≠ Audited ≠ Admitted ≠ Committed

The Representation pipeline has four distinct epistemic/operational stages:

```text
Candidate
→ Audited Judgment
→ Admitted Epistemic Hypothesis
→ Topology Commitment
```

They must remain technically distinct.

### Candidate

High-recall hypothesis produced by cheap retrieval or graph evidence.

```text
authority = NONE
mutates materialized topology = FALSE
```

### Audited Judgment

A structured semantic judgment over an immutable evidence bundle. It may still be uncertain and must preserve supporting/conflicting evidence.

### Admitted Epistemic Hypothesis

A grounded, provenance-preserving judgment produced under valid execution identity may enter canonical epistemic World Representation with explicit uncertainty.

Admission means:

```text
RAOS may represent and revise this belief
```

not:

```text
the hypothesis is certified true
```

Probabilistic belief may therefore exist before any Event merge, duplicate suppression, or independence collapse.

### Topology Commitment

A separate decision step may change the current materialized operational graph when downstream asymmetric risk justifies it.

Examples include:

```text
merge Event hypotheses
replace Event membership
collapse independent evidence
suppress duplicate Sources
```

Only this layer may perform such topology-changing side effects, and it remains subject to Phase13 execution authority plus a versioned commitment policy.

---

## 5. EventEvidenceFrame

Representation Auditor must not consume only titles or embedding similarity.

Semantic Perception should project each Source into **zero or more** evidence-grounded event frames. One article may describe multiple distinct events; forcing one Source into one frame would silently turn Event representation back into article clustering.

```text
Source
→ EventEvidenceFrame 0
→ EventEvidenceFrame 1
→ ...
→ EventEvidenceFrame N
```

Each frame is an immutable, versioned evidence artifact:

```text
EventEvidenceFrame
├─ frame_id
├─ source_id / source_snapshot_id
├─ semantic_input_digest / frame_contract_version
├─ actors / organizations
├─ action / transition
├─ object / target
├─ product / system / version
├─ time anchors
├─ location anchors
├─ quantitative anchors
├─ explicit identifiers
├─ source Claim / Observation ids
├─ attribution spans
└─ uncertainty
```

This object is not an Event. It is Source-grounded evidence about **one event mention / event proposition** the Source appears to describe.

Every field must retain provenance to Source / Snapshot / Claim / Observation evidence. EventEvidenceFrames are append-only; a later better frame does not rewrite the frame used by an earlier RepresentationAuditRun.

Candidate generation may use Source-level retrieval as a cheap prefilter, but semantic adjudication should ultimately compare frame-to-frame or frame-to-Event-hypothesis evidence rather than treating whole articles as indivisible event units.

---

## 6. RepresentationEvidenceBundle

The Auditor operates on a structured evidence bundle, not a similarity score:

```text
RepresentationEvidenceBundle
├─ Source A metadata + audited semantic evidence
├─ Source B metadata + audited semantic evidence
├─ EventEvidenceFrame A/B
├─ explicit provenance
│  ├─ CITES
│  ├─ DOI / canonical URL
│  └─ publisher attribution
├─ textual evidence
│  ├─ explicit attribution
│  ├─ quoted material
│  └─ substantial reuse
├─ temporal evidence
├─ identity/entity evidence
├─ existing graph facts
└─ contradictions / missing evidence
```

The input bundle itself is immutable and digestible so the judgment can be replayed.

---

## 7. Embedding policy

The current Qwen3-Embedding-0.6B deployment is a **candidate-retrieval sensor**, not a Representation authority mechanism.

Allowed uses:

```text
semantic nearest-neighbor retrieval
candidate expansion
hard-negative discovery
recall-oriented clustering hints
```

Forbidden uses:

```text
embedding_score > threshold
→ SAME_EVENT

embedding_score > threshold
→ DERIVED_FROM

embedding_score > threshold
→ CONFIRMED Event
```

Embedding quality is evaluated on RAOS-specific candidate-retrieval metrics, not accepted from generic benchmark scores.

Required calibration metrics:

```text
same-event Recall@K
hard-negative Recall@K
candidate-set size
latency / source
memory footprint
cross-language recall
failure slices by event type
```

The primary objective is high recall at bounded candidate cost. False merge authority is handled downstream and must never be delegated to the embedding model.

A larger embedding/reranker model may be introduced only if RAOS-specific retrieval calibration shows material value.

---

## 8. Retrieval and authority have opposite optimization targets

Candidate retrieval:

> optimize recall; tolerate false positives.

Representation authority:

> optimize precision; tolerate missed merges.

Permanent risk asymmetry:

```text
False Merge cost ≫ Missed Merge cost
```

A missed merge primarily reduces compression and may temporarily duplicate Attention.

A false merge can corrupt:

```text
Coverage
independence
P
Claim context
Event history
Attention
```

Therefore SAME_EVENT authority is precision-first.

---

## 9. Relation-specific proof standards

No universal `confidence > threshold` rule is allowed.

### CITES

```text
literal explicit reference
→ authorized CITES
```

Already implemented in Explicit Reference Provenance V0.1.

### DERIVED_FROM

Requires positive dependency evidence such as:

```text
explicit attribution/reference
+
compatible publication order
+
substantial semantic/textual dependency
```

### SAME_EVENT

Requires:

```text
event semantic identity
+
key actors/action/object compatibility
+
time compatibility
+
no hard contradiction
+
strong anchor OR multi-axis corroboration
```

Semantic similarity + temporal proximity alone remain candidate evidence.

### INDEPENDENT_REPORT

Must never be inferred from absence of DERIVED_FROM evidence.

```text
no dependency found
≠ independent
```

Default:

```text
INDEPENDENCE_UNKNOWN
```

Positive independence evidence is required before EditorialCoverage/P may count the Source as independent.

### OFFICIAL / ORIGINAL

OFFICIAL is an attributable source-role judgment about the actor represented by the publisher/account.

ORIGINAL_SOURCE is stronger and requires explicit provenance/temporal/identity support. An official Source is not automatically the first Source.

---

## 10. Deterministic Topology Commitment Gate

The semantic Auditor may:

```text
reason
classify
cite evidence
surface conflicts
estimate uncertainty
```

and grounded judgments may be admitted into probabilistic epistemic World Representation.

The Auditor may not independently commit topology.

Topology commitment is assigned by a deterministic, versioned decision policy:

```text
Admitted Epistemic Hypothesis
+
frozen evidence predicates
+
relation-specific commitment policy
+
Phase13 execution authority
→ COMMIT / KEEP_SEPARATE / DEFER / REJECT
```

The existing E1 shadow outputs (`WOULD_AUTHORIZE / CANDIDATE_ONLY / REJECTED / UNRESOLVED`) are retained for compatibility, but their semantics are now interpreted as **commitment simulation**, not truth certification.

Forbidden:

```text
LLM confidence > 0.9
→ merge Event topology
```

The **Topology Commitment Gate** must be replayable deterministically from frozen inputs. A future calibrated epistemic probability may enter an expected-loss decision rule, but the current response-spectrum probability proxy is explicitly not calibrated enough to authorize merge/suppression.

Phase13 answers whether the runtime may perform the side effect; it does not certify the world hypothesis as true.

---

## 11. Event revision model

Current `Event` should evolve into a stable hypothesis identity plus immutable revisions:

```text
Event
= hypothesis identity

EventRevision
= immutable description of that hypothesis at time t
```

An EventRevision may update:

```text
title
summary
event_type
occurred_at
location
semantic frame
evidence maturity
```

without pretending that historical revisions never existed.

Correction within the same hypothesis:

```text
Event E / Revision R3
→ Event E / Revision R4
```

Topology change is not a revision.

The existing scalar `Event.confidence` may remain during migration as a diagnostic/materialized summary, but it must not be treated as representation authority. Authority comes from versioned evidence + audit + policy, not from a single confidence number.

---

## 12. Non-destructive merge / split / supersession

### Merge

If RAOS later concludes two historical Event hypotheses represent one event:

```text
Event A ─┐
         ├─ MERGED_INTO → Event C
Event B ─┘
```

A and B become historical/SUPERSEDED hypotheses. They are never deleted or rewritten away.

### Split

If one Event hypothesis later proves to contain two events:

```text
         ┌─ SPLIT_INTO → Event B
Event A ─┤
         └─ SPLIT_INTO → Event C
```

A remains the historical hypothesis visible to historical AnalysisRuns and Representation Snapshots.

### Correction

Changes to the description of the same hypothesis use EventRevision.

### Topology change

Changes to event identity use EventLineage.

### EventStatus compatibility

`SUPERSEDED` in this document is a **lifecycle semantic**, not yet a newly authorized database enum. The current code still exposes `CANDIDATE / CONFIRMED / MERGED / ARCHIVED`. During C2/D shadow work, do not mutate this enum merely to match the preregistration.

At E3, EventLineage should become the canonical explanation of why an Event is no longer current. The long-term materialized status can then converge toward:

```text
CANDIDATE
CONFIRMED
SUPERSEDED
ARCHIVED
```

with `MERGED_INTO / SPLIT_INTO / SUPERSEDED_BY` represented as lineage relations rather than overloading status with topology.

---

## 13. Proposed persistence substrate

Add five append-oriented objects while retaining current Event/EventSource/SourceEdge as current materialized projections.

### EventEvidenceFrame

Persist the immutable Source-grounded frame generated in D1 so later candidate retrieval/audit can be replayed without re-running perception against mutable code/model state.

Minimum identity/provenance:

```text
id
workspace_id
source_id / source_snapshot_id
frame_contract_version
semantic_input_digest
frame_payload
frame_digest
created_at
```

A Source may own zero or more frames.

### RepresentationAuditRun

Immutable record of one auditor judgment:

```text
id
identity_key
workspace_id
origin_device_id
authority_epoch
audit_type
subject_type / subject_id
object_type / object_id
input_evidence_digest
input_frame_ids / evidence_bundle_refs
auditor_contract_version
provider / model
judgments
supporting_evidence
conflicting_evidence
uncertainty
proposed_transition
authority_policy_version
authority_result
authorized_by
execution_context_digest
created_at
```

`workspace_id / origin_device_id / authority_epoch` are persistence/authority provenance. They must never become semantic inputs to relation classification.

### EventRevision

Immutable version of one Event hypothesis.

```text
id
workspace_id
event_id
parent_revision_id
revision_payload
revision_digest
audit_run_id
authority_epoch
created_at
```

A revision changes the description/evidence maturity of the same Event hypothesis. It does not merge/split Event identity.

### EventLineage

Append-only Event-hypothesis topology:

```text
id
workspace_id
predecessor_event_id
successor_event_id
relationship = MERGED_INTO / SPLIT_INTO / SUPERSEDED_BY
audit_run_id
authority_epoch
created_at
```

Lineage must be acyclic. Resolving a historical Event to current hypotheses may yield one current successor after merge or multiple current successors after split.

### EventMembershipAssertion

Append-only membership authority:

```text
id
workspace_id
event_id
source_id
frame_ids
action = ASSERT / RETRACT
membership
contextual_role_fields
audit_run_id
authority_policy_version
authority_epoch
authority_status
supersedes_assertion_id
created_at
```

A retraction supersedes an earlier assertion; it does not delete it.

Current `EventSource` remains a materialized current projection during migration.

### 13.1 Canonical fact normalization — no duplicate truth

A judgment dimension does not automatically imply a new edge/table fact of the same name. The authoritative fact layer must stay normalized.

```text
CITES / REPOSTS / DERIVED_FROM
→ SourceEdge provenance facts

SAME_EVENT
→ NOT an authoritative Source↔Source SAME_EVENT edge
→ authorized EventMembershipAssertion(s) to the same Event hypothesis
→ current EventSource materialization

officiality / reporting_role / originality
→ EventMembershipAssertion contextual role fields / current EventSource projection

Event merge / split / supersession
→ EventLineage

Event description correction
→ EventRevision

RELATED / DISCUSSES / EXTENDS
→ contextual graph relation where useful, never a substitute for Event identity
```

Pairwise `SAME_EVENT` may exist inside a RepresentationAuditRun as evidence/judgment, but the canonical representation of same-event identity is shared authorized membership in an Event hypothesis. This prevents RAOS from maintaining two competing truth stores for the same world relation.

### 13.2 Local-first / future-tenancy persistence constraints

These are storage constraints, not research semantics.

All newly introduced persistent Representation objects should be designed so a later local-first/private-beta deployment does not require semantic migration:

```text
workspace-scoped ownership
UUID/global identity suitable for cross-device sync
append-only immutable audit/history records
materialized projections are rebuildable
no database-local autoincrement ordering as semantic identity
authority-bearing records carry authority_epoch + execution identity
```

For the current single-user dogfood, `workspace_id` may resolve to one implicit singleton workspace. The field exists to preserve the ownership boundary; workspace/user identity must never influence SAME_EVENT, DERIVED_FROM, OFFICIAL, independence, or other semantic judgments.

---

## 14. Unified pipeline

```text
Source / Snapshot
  ↓
Audited Semantic Evidence
  ↓
0..N EventEvidenceFrames
  ↓
Candidate Retrieval
  ├─ Source-level cheap prefilter
  ├─ title/time/entity/reference/graph
  └─ embedding retrieval
  ↓
Frame↔Frame / Frame↔Event candidate set
  ↓
RepresentationEvidenceBundle
  ↓
Representation Auditor
  ├─ SourcePair / FramePair judgments
  │    ├─ event_identity
  │    ├─ provenance_dependency
  │    └─ relation_context
  ├─ SourceEvent judgments
  │    ├─ membership
  │    ├─ officiality
  │    ├─ reporting_role
  │    └─ originality
  ├─ EventPair topology judgments
  ├─ supporting evidence
  ├─ conflicting evidence
  └─ uncertainty
  ↓
Deterministic Representation Authority Gate
  ↓
Representation Transition Planner
  ↓
Global Representation Consistency Validator
  ↓
Phase 13 Authority Gate
  ↓
Atomic authorized transition commit
  ↓
Normalized authorized facts
  ├─ SourceEdge provenance
  ├─ EventMembershipAssertion
  ├─ EventRevision
  └─ EventLineage
  ↓
Current World Representation projection
  ↓
Frozen Representation Snapshot R_t
```

### 14.1 Global Representation consistency

Pairwise judgments are not committed independently. Before any authority-bearing transition is persisted, a deterministic validator must check graph-level invariants.

Minimum V0.1 invariants:

```text
EventLineage is acyclic
one EventEvidenceFrame cannot be an authoritative current member of two mutually distinct Event hypotheses
one Source may still report multiple Events through different EventEvidenceFrames
provenance direction is preserved; A DERIVED_FROM B is not symmetric
role/officiality/originality never manufactures SAME_EVENT membership
candidate/shadow facts never satisfy authority predicates
merge/split never deletes historical Event/Revision/Membership evidence
```

The authoritative transition must be atomic: the frozen audit record, assertion/revision/lineage records, and current materialized projection either commit together or not at all. Retries must be idempotent through a stable audit/transition identity key.

---

## 15. Digest policy during rollout

### Shadow phase

Raw retrieval candidates are **audit/search intermediates**, not World Representation facts. They receive their own candidate-set / evidence-bundle digests and do not enter `graph_digest` by default.

Likewise, a shadow RepresentationAuditRun is preserved for inspection/calibration but does not automatically become a graph fact merely because it exists.

The following may enter `graph_digest` when deliberately persisted as part of the epistemic representation:

```text
EventEvidenceFrames referenced by persisted hypotheses/audits
persisted CANDIDATE Event hypotheses
explicit SourceGraph facts such as CITES
other intentionally materialized non-decision representation facts
```

None of the above may affect `decision_representation_digest` until separately authorized for Decision use.

Rule:

```text
retrieval result ≠ representation fact
shadow judgment ≠ representation fact
authorized or explicitly materialized epistemic fact → graph representation
```

### Authority phase

Only after E-stage preregistration and calibration may a new version:

```text
decision-representation-v0.2
```

admit explicitly authorized representation facts such as:

```text
authorized Event membership
authorized provenance dependency
authorized independence
authorized officiality / reporting role / originality
```

Rule:

```text
Candidate relation
↛ Decision digest

Audited but unauthorized relation
↛ Decision digest

Authorized representation fact
→ Decision digest
```

---

## 16. Event promotion

```text
CANDIDATE → CONFIRMED
```

is an authority-bearing representation transition.

It must require:

```text
EventPromotionProposal
→ Representation Authority Gate
→ Phase 13
→ authorized transition
```

It must never be implemented as:

```text
confidence > scalar threshold
→ CONFIRMED
```

CONFIRMED means epistemically authorized for current RAOS use, not ontologically proven.

---

## 17. Implementation sequence

### C2 — Representation audit substrate

Implement append-only audit/history tables and current-projection adapters with workspace-scoped UUID identity, replayable digests and authority provenance. No current authority change.

### D1 — EventEvidenceFrame

Generate zero-or-more Source-grounded structured event frames from audited semantic evidence; persist them immutably with Source/Snapshot provenance.

### D2 — Unified candidate generation

Extend current Source-level shadow retriever with entity/time/reference/graph/embedding signals, then refine to Frame↔Frame / Frame↔Event candidate retrieval. Authority remains NONE.

### D3 — Representation Auditor shadow

Emit orthogonal judgments and evidence traces. No authoritative graph mutation.

### D4 — Dogfood calibration corpus

Build difficult positive/negative cases:

```text
same title / different event
different title / same event
same event / repost
same event / independent report
explicit citation / different event
official source / not original
follow-up event / related but not same
correction / merge / split cases
```

### E1 — Deterministic Authority Gate V0.1

Freeze relation-specific proof predicates and authority results.

### E2 — Conservative authorization

Authorize strongest relations first. CITES is already live. Next candidates: explicit REPOSTS / DERIVED_FROM / OFFICIAL_FOR_REPRESENTED_ACTOR. Automatic Event membership from SAME_EVENT evidence remains later and stricter.

### E3 — Event lifecycle

Enable CANDIDATE promotion, EventRevision, merge/split lineage and supersession. Early merge/split should remain shadow or human-confirmed until calibrated.

### E4 — Representation Snapshot V0.2

Admit only authorized representation facts into decision identity.

Then continue original plan:

```text
F. Coverage evidence authorization into P
G. Event/Claim-level Attention objects
H. Event-aware PresentationPolicy, Delivery and Agent APIs
```

---

## 18. Exit criteria for V0.1 shadow

Representation Auditor V0.1 shadow is not eligible for E-stage authority until:

1. Candidate retrieval has measured high Recall@K on RAOS-specific event pairs.
2. Auditor dimensions are shown to be independently necessary on calibration cases.
3. Hard-negative false-merge slices are explicitly measured.
4. Every judgment preserves supporting/conflicting evidence.
5. No candidate/shadow judgment changes `decision_representation_digest`.
6. Historical Event/Source evidence remains append-only and replayable.
7. Phase 13 identity is attached to every authority-capable audit path.
8. A merge/split simulation can reconstruct both historical and current Event topology.
9. Raw retrieval candidate churn does not change `graph_digest`; only intentionally materialized epistemic facts do.
10. Canonical SAME_EVENT representation is shared authorized Event membership, not a duplicate authoritative Source↔Source edge.
11. A multi-event Source can produce multiple EventEvidenceFrames and join different Event hypotheses without violating consistency.
12. New Representation persistence is workspace-scoped, globally identifiable, append-oriented and replayable without making workspace/device identity a semantic relation feature.
13. The Global Representation Consistency Validator rejects lineage cycles, incompatible frame memberships and partial/non-idempotent transition commits.

---

## 19. Frozen principles

```text
Candidate ≠ Audited ≠ Authorized

CONFIRMED Event ≠ Objective Reality

False Merge cost ≫ Missed Merge cost

Orthogonal representation dimensions must not be collapsed into one score

Embedding similarity is retrieval evidence, never relation authority

History is immutable; representation is revisable

SAME_EVENT judgment is evidence; shared authorized Event membership is the canonical fact

Deployment ownership metadata constrains persistence, never world-relation semantics
```
