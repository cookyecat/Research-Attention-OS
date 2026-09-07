# Research Attention OS — Semantic Evidence Frame v0.1

Status: **CANDIDATE SENSOR INTERFACE — ACTIVE CALIBRATION**  
Date: 2026-09-07  
Parent: `33_SEMANTIC_EVIDENCE_EXTRACTION_FRONT_END.md`  
Mathematical registry: `35_RAOS_MATHEMATICAL_LANGUAGE_REGISTRY.md`

> Purpose: define the smallest provenance-preserving semantic evidence object that can sit between raw information and the frozen D/S/P estimators without pre-answering D, S, P, or Attention Action.

---

## 1. Position in the system

Theoretical event semantics:

$$
Sem^*(E)
$$

are not directly observable.

The Sensor Front-End receives raw information $I$ and produces:

$$
\boxed{
\widehat{Sem}(E)=ExtractSemanticEvidence(I)
}
$$

The downstream path is:

$$
\boxed{
I
\rightarrow
SemanticEvidenceFrame
\rightarrow
(\hat D,\hat S,\hat P)
\rightarrow
\hat A
}
$$

The frame is a **sensor reading**, not a policy decision.

---

## 2. Non-negotiable boundary

The frame MUST NOT contain:

```text
D / standing_radar_fit
S / material_consequence
P / collective_attention_salience
AWARE / DROP / WATCH / ENGAGE
user_interest judgment
importance score
editorial-worthiness score
predicted cognitive change
```

Those belong downstream.

Invariant:

$$
\boxed{Evidence\neq StateEstimate\neq PolicyAction}
$$

---

## 3. Minimal v0.1 structure

```text
SemanticEvidenceFrame
├── event
├── sources[]
├── evidence[]
├── substantive_actors_objects[]
├── actions_changes[]
├── affected_systems_populations[]
├── temporal_context
└── uncertainties[]
```

The interface deliberately avoids a giant domain/event ontology.

---

## 4. Event

Required:

```text
event_id
as_of
summary
```

### summary

A short factual description of the underlying event.

Requirements:

```text
- describe what happened, not whether it matters
- do not include D/S/P labels
- do not encode user preference
- do not call the event viral/important unless that statement itself is source-supported evidence
- distinguish current event from historical background
```

Good:

> A national regulator announced a mandatory time-of-use residential electricity pricing regime that will replace the current flat tariff next year.

Bad:

> A highly important energy event that the user should know about.

---

## 5. Sources

Each source has a stable `source_id` plus basic provenance metadata.

Candidate fields:

```text
source_id
source_type
published_at
locator
```

`locator` may be a URL, document identifier, file pointer, message id, or other reproducible source location.

The interface does not assume all sources are web pages.

---

## 6. Evidence records

Every extracted semantic statement must ultimately trace to evidence.

Candidate fields:

```text
evidence_id
source_id
support_pointer
support_excerpt
 epistemic_status
confidence
```

### support_pointer

Preferred reproducible location inside a source:

```text
paragraph 12
page 4
section Results
message timestamp
JSON field path
```

### support_excerpt

Optional short excerpt for audit/debugging. Prefer a pointer over copying large source spans.

### epistemic_status

Small epistemic vocabulary:

```text
SOURCE_CLAIM
DIRECT_OBSERVATION
EXTRACTOR_INFERENCE
```

The extractor may use inference, but it must label it as inference rather than silently presenting it as source fact.

### confidence

Use coarse confidence only:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Do not fabricate numeric precision.

---

## 7. Substantive actors / objects

Each record represents an entity genuinely participating in what happens in the event.

Candidate fields:

```text
name
role
substantive_basis
support_ids[]
```

Examples:

```text
OpenAI
role: releaser
substantive_basis: released the model described in the event

National electricity regulator
role: regulator
substantive_basis: issued the binding settlement rule
```

Invariant:

$$
\boxed{Mention\neq SubstantiveActorObject}
$$

A company named only in historical background should not automatically become a substantive actor.

---

## 8. Actions / changes

Each record states what happened or changed.

Candidate fields:

```text
description
temporal_status
support_ids[]
```

`description` remains natural-language evidence, for example:

```text
mandatory settlement rule changed
benchmark success rate increased in independent reproduction
logo changed but product behavior did not
access requirement removed
industry standard became binding
```

`temporal_status` uses only a small status vocabulary:

```text
PROPOSED
ANNOUNCED
ENACTED
EFFECTIVE
OBSERVED
HISTORICAL
UNKNOWN
```

This is a temporal-status vocabulary, not an event ontology.

---

## 9. Affected systems / populations

Each record states what is affected and at what supported reference scope.

Candidate fields:

```text
description
reference_scope
support_ids[]
```

Examples:

```text
description: residential electricity customers nationwide
reference_scope: tens of millions of households / national

description: active maintainers of a niche database engine
reference_scope: professional product community / approximately several thousand
```

`reference_scope` is intentionally free natural language.

Do not force all events into a universal hierarchy such as local < city < national < global.

---

## 10. Temporal context

Candidate fields:

```text
event_time
effective_time
as_of
notes
```

The distinction matters because:

```text
announced != effective
historical != current
proposal != enacted rule
```

The frame must not convert future or proposed state into current fact.

---

## 11. Uncertainty / missingness

Candidate fields:

```text
field
kind
note
support_ids[]
```

Allowed `kind`:

```text
UNKNOWN
CONFLICTING_SOURCES
UNCERTAIN_SCOPE
UNCERTAIN_ACTOR_ROLE
INSUFFICIENT_SUPPORT
```

Core invariant:

$$
\boxed{Missing\neq Absent}
$$

If the article does not state the affected population size, emit unknown rather than inventing one.

---

## 12. Provenance integrity rules

v0.1 should enforce:

1. every `evidence.source_id` must exist in `sources`;
2. every semantic object (`actor`, `change`, `affected system`) must cite at least one existing `evidence_id`;
3. unsupported semantic objects are invalid;
4. unknown/missing fields remain explicit rather than converted to empty-negative facts;
5. extra undeclared top-level fields are rejected;
6. D/S/P/A labels are rejected by schema boundary rather than merely discouraged by prompt.

---

## 13. Why this is intentionally small

The front-end is not trying to answer:

```text
What exact domain ontology class is this?
What is the universal event type?
What is the event's global importance score?
```

It is trying to recover enough supported semantic evidence that downstream variables can ask their own questions.

For D, the useful evidence is mainly:

```text
substantive actors / objects
what they did
relations / affiliations if source-supported
```

For S:

```text
what changed
which shared systems/populations are affected
scope / rule / capability / cost / control evidence
```

For P constituency prior:

```text
what the event is
who is naturally affected / addressed
```

Current P attention observations remain a separate time-indexed sensor path.

---

## 14. Evaluation plan

Do not jump directly to AWARE/DROP accuracy.

### E1 — frame fidelity

Compare Human frame vs LLM frame field-by-field:

```text
event-summary fidelity
substantive actor/object precision and recall
action/change fidelity
affected-system/population fidelity
temporal-status accuracy
unsupported-inference rate
missingness honesty
provenance completeness
```

No single weighted master score is required initially.

### E2 — downstream invariance

For the same source:

```text
Human SemanticEvidenceFrame
        ↓
D/S/P

versus

LLM SemanticEvidenceFrame
        ↓
D/S/P
```

Measure whether extraction changes downstream state estimates.

A particularly useful quantity is:

$$
\boxed{
DownstreamInvariance
=
Pr\left[
DSP(\widehat{Sem}_{LLM})
=
DSP(\widehat{Sem}_{Human})
\right]
}
$$

This is an evaluation quantity, not a new RAOS physical variable.

### E3 — end-to-end

Only after E1/E2 attribution is understood:

```text
raw source
  ↓
extract
  ↓
D/S/P
  ↓
policy
  ↓
AWARE / DROP
```

---

## 15. v0.1 research decision

```text
Interface purpose               sensor boundary
Ontology ambition               minimal / evidence-oriented
D/S/P labels in frame           FORBIDDEN
Source provenance               REQUIRED
Semantic-object support         REQUIRED
Missingness                     explicit
Exact numeric confidence        rejected
Current status                  CANDIDATE v0.1
Next step                       implement schema + validate on development raw sources
```

Do not freeze v1 until the interface has represented a small development corpus of real/raw sources without requiring D/S/P leakage or a large ontology.
