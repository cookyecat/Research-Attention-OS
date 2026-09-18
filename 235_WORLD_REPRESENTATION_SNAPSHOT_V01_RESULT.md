# RAOS World Representation Snapshot V0.1 — Result

Status: **DOGFOOD READY**  
Date: 2026-09-18

## 1. Scope

This result implements the first executable slice of the frozen world-state-centric architecture in `234_WORLD_STATE_CENTRIC_RAOS_ARCHITECTURE_V1.md`.

The goal of V0.1 is not to change Multi-Delta, Pareto, D/S/P, or Attention mathematics. It changes how the decision input is frozen, identified and audited.

Canonical transition:

```text
Source + explicit extras
→ FrozenRepresentationSnapshot R_t
→ current Core mathematics
```

## 2. Representation Snapshot

New service:

```text
backend/app/services/representation_snapshot.py
```

Versions:

```text
world-representation-v0.1
decision-representation-v0.1
```

The snapshot records:
- primary/member Source ids;
- Event hypotheses visible at freeze time;
- SourceGraph facts;
- frozen relational/independence context;
- collective-attention evidence packets;
- graph digest;
- decision-representation digest.

## 3. Dual digest semantics

```text
graph_digest
= full representation facts for audit/reconstruction/UI

decision_representation_digest
= only facts currently authorized to change cognition/attention
```

V0.1 decision-relevant facts are deliberately narrow:
- current REPOSTS / DERIVED_FROM / REPORTS_ON relational facts;
- derived independence / duplicate state;
- collective-attention evidence packets already consumed by no-Delta D/S/P.

Candidate Events, Related-reading edges and other presentation/context enrichment affect `graph_digest` only.

This establishes an important cost/correctness invariant:

> **UI/world-graph enrichment must not spend cognition budget unless it changes an authorized decision input.**

It also closes a prior identity gap: collective-attention evidence packets could affect D/S/P while living outside the old Source `input_hash`. They now participate in `decision_representation_digest`.

## 4. Consistency firewall

Pipeline freezes `R_t` before cognition and rechecks the decision digest before impact/decision.

```text
R0 → extraction / locate
representation changes to R1

if decision_digest(R0) != decision_digest(R1)
→ FAIL CLOSED
```

Presentation-only graph changes do not abort the run.

The previous historical test semantics that allowed a decision-relevant SourceGraph mutation mid-run to finish against an older frozen relational context was intentionally replaced by this fail-closed rule.

This mirrors the existing Kernel consistency principle and prevents hybrid world-state decisions.

## 5. Analysis identity and provenance

Analysis identity now accepts `decision_representation_digest` while retaining `relational_digest` as a compatibility input for historical callers.

Execution snapshot records Representation schema/decision versions. Both authoritative and quarantined analysis payloads include the frozen Representation Snapshot.

Analysis provenance records:
- representation graph digest;
- decision representation digest;
- representation schema version;
- representation decision version.

## 6. Regression

Focused representation + Phase13:

```text
17 passed
```

Expanded identity / D-S-P / provenance / Phase13:

```text
102 passed
```

Full backend:

```text
848 passed
63 skipped
1 failed
```

The only failure remains the pre-existing Case-K urgency residual: expected PREEMPT, actual PRIORITY.

## 7. Canonical live smoke

Live source:

```text
量子位
“被英伟达点名的杭州团队，补上了AI for Science的「最后一公里」”
```

Old run: disposition DROP, no Representation Snapshot.

New canonical run:

```text
purpose      CANONICAL
attestation  ATTESTED
authority    true

representation_schema  world-representation-v0.1
decision_version       decision-representation-v0.1
Event hypotheses       1
graph edges             0
```

Decision remained:

```text
D = IN
S = NOT_MATERIAL
P = UNKNOWN
→ DROP
```

Therefore the Representation migration preserved the previously validated Core judgment while adding stronger identity and audit semantics.

## 8. Next stage

Proceed to strongest-evidence Representation relations first:

```text
explicit outbound references
→ reference candidates
→ official/original source resolution
→ Representation Auditor
→ authoritative provenance facts
```

Do not infer same-event authority from lexical similarity alone.
