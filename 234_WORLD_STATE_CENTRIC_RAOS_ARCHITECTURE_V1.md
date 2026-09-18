# RAOS World-State-Centric Architecture V1

Status: **FROZEN THEORY / IMPLEMENTATION ACTIVE**  
Date: 2026-09-18

## 1. Core positioning

RAOS does not fundamentally judge articles.

> **RAOS observes the world through Sources, builds a revisable representation of world state, and decides which world-state changes deserve human attention.**

Canonical positioning:

```text
RSS / Reader           → Source-centric
ordinary recommender   → Content-centric
RAOS                   → World-state-centric → Attention
```

A Source is evidence left by observation.  
A World Event / material Claim Change is the object RAOS attempts to understand.  
Attention is the result RAOS exposes to the human.
## 2. Top-level planes

The serial data path is:

```text
Acquisition
→ Semantic Perception
→ World Representation
→ Cognition & Decision
→ Attention & Responsibility
→ Delivery
```

Two planes cut across or control the path:

```text
Agent / Control Plane
Phase 13 Trust / Integrity Plane
```

Phase 13 is not a serial stage. It governs identity, authority, attestation, integrity and authorized mutation across authority-bearing transitions.
## 3. Layer model

### L0 — Observation / Acquisition

External world signals become immutable Source / Snapshot evidence.

Responsibilities include:
- acquisition and polling;
- source identity/versioning;
- raw/presentation preservation;
- append-only correction semantics.

Inbox remains Source-oriented because its job is to preserve what RAOS observed.

### L1 — Semantic Perception

```text
Sensor → Semantic Evidence Auditor
```

The Sensor proposes semantic observations/claims/inferences.  
The Auditor asks whether those semantics are actually supported by the Source.
### L2 — World Representation

This layer answers:

> How many real-world things are represented here, and how are the observations related?

Canonical primitives remain intentionally small:

```text
Source
Event
Claim
SourceEdge
EventSource
```

The layer represents:
- Event / Claim hypotheses;
- provenance;
- same-event membership;
- independence / secondary reporting;
- contradiction;
- evidence maturity;
- collective-attention evidence.
A real-world event is ontologically unique, but a RAOS Event is a revisable epistemic hypothesis.

```text
World Event
= ontological reality

RAOS Event
= revisable representation of that reality
```

Therefore:

```text
CANDIDATE Event ≠ CONFIRMED Event
```

RAOS must support later merge/split/correction without destructive rewriting of historical evidence.

### L3 — Cognition & Decision

Canonical decision input is a frozen Representation Snapshot rather than an isolated Source:

```math
R_t = Assemble({AuditedSourceEvidence_i})
```

```math
Decision_t = F(R_t, K_t)
```

not:

```math
Decision_i = F(Source_i, K_t)
```

The Representation Snapshot keeps the Source evidence that justifies the representation.

Decision then branches:

```text
Representation Snapshot R_t
        │
        ├── Cognitive Effect exists
        │     → Grounding / Effect Existence / OPEN_NEW
        │     → Multi-Delta / Pareto
        │
        └── No Cognitive Effect
              → D / S / P
              → no-Delta AWARE gate
```

World Representation therefore serves both cognitive-change and no-Delta branches. D/S/P remains a no-Delta decision mechanism, not the universal representation layer.

### L4 — Attention & Responsibility

The long-term attention subject is:

```text
World Event / material Claim Change
```

not every Source independently.

Canonical distinction:

```math
AttentionDecision(Event or ClaimChange)
```

versus:

```math
PresentationPolicy(Event, Sources)
```

The first asks whether the world-state change deserves consciousness.  
The second selects how to present it and which Source(s) best represent it.

Long-term compression target:

```text
N Sources
→ 1 Event / Claim Change
→ 1 current Attention object
→ 1 representative reading path
```

This is attention compression rather than source filtering.

WATCH remains delegated future-attention responsibility. High P alone must never mechanically imply WATCH.

### L5 — Delivery

Delivery transports an already-authorized Attention/Responsibility state through Today, email, notifications, etc.

Event-level representation should eventually prevent repeated notifications for multiple Sources covering the same world event.

## 4. User-facing projections

Coverage and Related are views over the underlying representation, not separate truths.

```text
World Event
   ↑
covered by
Source A / B / C
```

```text
Coverage(E)
= Sources and relations that cover the same Event

Related(E)
= useful nearby Event / Claim context, not the same Event
```

Coverage is world context.  
Related reading is optional exploration and remains folded by default.

Do not create a second “Coverage truth” database. Use SourceGraph + Event + Claim as the fact layer.

## 5. Three audit questions

The architecture separates three kinds of audit:

```text
Semantic Evidence Auditor
→ Does this Source actually support this semantic observation/claim?

Representation Auditor
→ Do these Sources / Claims / Events actually have this relationship?

Phase 13 Trust / Integrity
→ Was this authority-bearing judgment produced by an authorized runtime identity?
```

These are complementary rather than duplicate auditing.

Representation relation authority should scale with evidence strength:
- explicit canonical/reference URL, DOI, publisher attribution: strong;
- text reuse + earlier publication + attribution: moderate;
- semantic similarity/time proximity only: candidate evidence, not authority.

## 6. Representation Snapshot

Each decision uses an immutable, auditable Representation Snapshot `R_t`.

Minimum logical contents:

```text
target Event / Claim hypothesis
member Source ids
source roles
authorized provenance facts
independence groups
audited claims / observations / contradictions
evidence maturity
collective-attention evidence
uncertainty / authority status
```

The snapshot is a decision input artifact, not a new competing world ontology.

Historical decisions keep their historical snapshot even when RAOS later revises its Event hypothesis.

## 7. Two digests

Representation must expose two distinct hashes.

```text
graph_digest
= full representation facts useful for audit/UI/reconstruction

decision_representation_digest
= only facts authorized to affect cognition/attention
```

Decision-relevant examples:
- same-event membership;
- provenance;
- independence;
- official/original source status;
- new claims;
- contradiction;
- evidence maturity;
- authorized P evidence.

Presentation-only examples excluded from decision identity:
- Related reading;
- UI ordering;
- decorative annotations;
- presentation metadata.

Only a change to `decision_representation_digest` may invalidate/recompute a canonical decision for representation reasons.

This prevents UI/graph enrichment from repeatedly spending cognition budget.

## 8. Agent / Control Plane

Agents may inspect:

```text
Source
Event
Claim
Representation Snapshot
Attention / Watch
```

External agents may propose candidate relations or delegate future observation/responsibility, but may not unilaterally:
- confirm Event identity;
- mutate authoritative representation;
- assign Attention.

Agent-provided relations enter the same Representation Auditor / authority path as other evidence.

## 9. Phase 13 integration

Authority-bearing representation transitions require Execution Integrity.

Examples:
- confirming same-event membership;
- promoting a CANDIDATE Event;
- persisting authoritative provenance;
- authorizing Coverage as P evidence;
- creating/replacing Event/Claim Attention.

Representation snapshots/digests must be attributable to algorithm/version/runtime identity so historical decisions remain reproducible and auditable.

## 10. Collective Attention

Long-term:

```text
P basic unit = Event-level collective attention
```

```math
P(E,t) = Estimator(
  AudienceAttention,
  EditorialCoverage,
  SearchInterest,
  CrossPlatformSpread,
  Velocity,
  ...
)
```

Raw Source count is not EditorialCoverage. Mirrors, reposts, transport duplicates and derived reports must not inflate independent attention evidence.

## 11. Implementation sequence

The theory is frozen; implementation proceeds incrementally:

```text
A. Representation Snapshot R_t + dual digests
B. Pipeline freezes/records R_t while preserving current Core mathematics
C. Provenance/reference extraction and relation auditing
D. Shadow same-event candidate retrieval + semantic adjudication
E. High-precision authority gate for Event/Claim representation
F. Coverage evidence authorization into P
G. Event/Claim-level Attention objects
H. Event-aware PresentationPolicy, Delivery and Agent APIs
```

No phase may silently make candidate relations authoritative.

## 12. Permanent design principles

1. **Source is evidence; Event / Claim Change is the decision subject.**
2. **Reality is unique; RAOS representation is revisable.**
3. **Preserve Sources even when they compress into one Event.**
4. **Representation precedes both cognitive-effect and no-Delta decision branches.**
5. **Coverage is a projection of the fact graph, not a second truth store.**
6. **Related reading is not collective-attention evidence.**
7. **Attention compression is distinct from source filtering.**
8. **Only decision-relevant representation changes may invalidate cognition identity.**
9. **Representation authority is audited; similarity alone is never truth.**
10. **Phase 13 governs authority across the whole system.**
