# RAOS Representation Auditor V0.1 — Architecture Review 1 Result

Status: **REVIEWED / PREREGISTRATION AMENDED / READY FOR C2 IMPLEMENTATION**  
Date: 2026-09-19

## 1. Verdict

The core Representation Auditor design remains sound. Review 1 did not change the frozen world-state-centric theory; it tightened implementation boundaries that could otherwise reintroduce article-centric clustering, duplicate truth stores, scalar relation collapse, or future local/cloud migration debt.

Reviewed preregistration: `237_REPRESENTATION_AUDITOR_V01_PREREGISTRATION.md`.

## 2. Amendments

1. **Orthogonality clarified** — semantically/causally irreducible, not statistically independent.
2. **Judgment scopes separated** — SourcePair/FramePair, SourceEvent, and EventPair are different objects.
3. **Source role decomposed** — `officiality`, `reporting_role`, and `originality` are separate dimensions; OFFICIAL, PRIMARY_REPORT and ORIGINAL are not mutually exclusive.
4. **Source → 0..N EventEvidenceFrames** — whole-article same-event clustering is no longer the semantic target.
5. **SAME_EVENT normalized** — pairwise SAME_EVENT remains audit evidence; canonical fact is shared authorized Event membership, not a second Source↔Source truth edge.
6. **Event lifecycle compatibility** — `SUPERSEDED` is a lifecycle semantic until E3; current `CANDIDATE/CONFIRMED/MERGED/ARCHIVED` enum is not changed during shadow work.
7. **EventEvidenceFrame persisted immutably** — Source/Snapshot provenance, contract identity and digest are retained for replay.
8. **Global consistency validator added** — rejects lineage cycles, incompatible frame memberships, provenance direction violations and partial/non-idempotent transitions.
9. **Raw retrieval candidates excluded from graph identity by default** — candidate-set/audit digests are separate from `graph_digest`.
10. **Local-first constraints moved into persistence only** — workspace ownership, global UUID identity, append-only syncability and authority epoch must not become semantic relation features.

## 3. Persistence target

```text
EventEvidenceFrame
RepresentationAuditRun
EventRevision
EventLineage
EventMembershipAssertion
```

Current `Event / EventSource / SourceEdge` remain materialized projections during migration.

## 4. Canonical fact mapping

```text
CITES / REPOSTS / DERIVED_FROM
→ SourceEdge

same-event identity
→ EventMembershipAssertion + Event hypothesis

officiality / reporting role / originality
→ Event membership contextual fields

Event description correction
→ EventRevision

Event merge / split / supersession
→ EventLineage
```

## 5. Readiness

Review 1 finds no architecture blocker to beginning **C2 — Representation audit substrate**.

C2 remains shadow/infrastructure-only:

```text
no new SAME_EVENT authority
no Event auto-merge
no decision_representation_digest change
no Coverage→P change
```

Next sequence remains:

```text
C2 audit substrate
→ D1 EventEvidenceFrame
→ D2 unified candidate retrieval
→ D3 shadow Representation Auditor
→ D4 calibration
→ E1 deterministic authority preregistration
```

## 6. Final review invariants

```text
Candidate ≠ Audited ≠ Authorized
CONFIRMED Event ≠ Objective Reality
Orthogonal dimensions are irreducible, not necessarily statistically independent
One Source may contain multiple EventEvidenceFrames
SAME_EVENT judgment is evidence; shared Event membership is the canonical fact
False Merge cost ≫ Missed Merge cost
Raw retrieval candidate ≠ World Representation fact
History is immutable; representation is revisable
Persistence ownership metadata never becomes world-relation semantics
```
