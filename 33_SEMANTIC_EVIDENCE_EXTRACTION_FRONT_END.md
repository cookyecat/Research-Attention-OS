# Semantic Evidence Extraction / Sensor Front-End

Status: **ACTIVE MODELING — NEXT PRODUCT FRONTIER**  
Date: 2026-09-07

> Purpose: define the engineering layer that transforms raw real-world information into the semantic evidence consumed by the already-frozen D/S/P variables, without redefining those variables around extraction limitations.

---

## 1. Why this layer now exists

The Phase II-B questionnaire / controlled validation work has mostly tested downstream policy under relatively clean semantic inputs.

Conceptually:

```text
clean event semantics / clean P evidence
        ↓
D-hat / S-hat / P-hat
        ↓
frozen no-Delta AWARE gate
```

Real RAOS input is different:

```text
article
post
paper
transcript
feed item
multi-source event cluster
```

The system must first determine what actually happened, which actors/objects are substantive, what changed, which shared systems may be affected, the scope of the event, and what attention evidence is genuinely observed.

Therefore the next engineering problem is upstream of the frozen policy:

```text
Raw information
    ↓
Semantic Evidence Extraction
    ↓
Estimator-ready evidence
    ↓
D-hat / S-hat / P-hat
    ↓
frozen AWARE gate
```

This is analogous to the Collective Attention design:

```text
theoretical state
    ↓
noisy sensors
    ↓
state estimator
```

A poor sensor is not a reason to rewrite the state definition.

---

## 2. Theoretical / engineering split

Let the real underlying event semantics be:

```text
Sem*(E)
```

RAOS never observes `Sem*(E)` directly. From raw source material `I`, it produces an engineering estimate:

```text
SemHat(E) = ExtractSemanticEvidence(I)
```

Downstream variables remain defined over the event / world, not over the extraction algorithm:

```text
D(E,u)
S(E)
P(E,t)
```

Engineering path:

```text
I
 ↓
SemHat(E)
 ↓
D-hat = D_estimator(SemHat(E), StandingRadar_u)
S-hat = S_estimator(SemHat(E))
P-hat = P_estimator(P_EvidencePacket(SemHat(E), observations_t, history))
 ↓
A-hat = FrozenPolicy(D-hat, S-hat, P-hat)
```

Never redefine D/S/P merely because `SemHat(E)` is imperfect.

---

## 3. Error decomposition

The integrated first-run result motivates explicit attribution across four layers:

```text
1. Extraction / sensing error
2. D/S/P estimator application error
3. Unknown / missingness propagation error
4. Policy composition / scheduler wiring error
```

A wrong final action must not be treated as one opaque policy error.

Examples:

```text
Article says a rule changes national pricing
        ↓
Extractor misses the rule / scope
        ↓
S-hat = NOT_MATERIAL
```

This is an extraction failure, not an S semantic failure.

Likewise:

```text
Extractor correctly identifies OpenAI as the substantive actor
        ↓
D estimator still invents an extra significance condition
        ↓
D-hat = OUT
```

This is a D clause-application failure, not extraction.

---

## 4. Minimal semantic evidence contract

Do **not** build a giant event ontology.

The extractor should emit a small evidence-oriented representation that preserves factual support and uncertainty.

Candidate `SemanticEvidenceFrame`:

```text
EventIdentity
EventSummary
SubstantiveActorsObjects
ActionsAndChanges
AffectedSystemsOrPopulations
ScopeEvidence
TemporalContext
SourceSupport
UncertaintyAndMissingness
```

### 4.1 EventIdentity

```text
event_id / cluster_id
as_of
source_ids
```

### 4.2 EventSummary

A concise factual description of what happened.

Requirements:

```text
- no D/S/P label
- no AWARE/DROP recommendation
- no user-interest judgment
- separate event fact from source opinion/promotion
```

### 4.3 SubstantiveActorsObjects

Entities that are actually doing, receiving, changing, regulating, releasing, studying, operating, or otherwise participating in the event.

This supports D actor/entity/affiliation clauses.

Important:

```text
Mention != SubstantiveActorObject
```

### 4.4 ActionsAndChanges

Evidence of what changed, for example:

```text
rule changed
price changed
capability changed
cost frontier changed
access condition changed
governance/control changed
standard changed
product behavior changed
only branding/appearance changed
```

Keep these as evidence statements, not a fixed categorical ontology.

### 4.5 AffectedSystemsOrPopulations

Who / what is affected and at what reference scope, based only on supported source evidence.

Examples:

```text
one internal team
one company
city commuters
an industry
national market participants
broad technical field
national households
```

This is evidence for S reference-system reasoning, not an S label.

### 4.6 ScopeEvidence

Natural-language evidence for scale / jurisdiction / reach:

```text
organizational
local/geographic
field/industry
national
international
broad public
unknown
```

A coarse hint is acceptable; false precision is not.

### 4.7 TemporalContext

```text
event time
announcement vs effective date
current / historical / proposed
measurement as-of time
```

This prevents stale facts from being interpreted as current state.

### 4.8 SourceSupport

Every extracted semantic claim should retain provenance:

```text
source_id
quoted / paraphrased support span or pointer
claim / observation status
confidence / ambiguity
```

The extractor must not silently merge unsupported inference into event facts.

### 4.9 UncertaintyAndMissingness

The extractor may say:

```text
unknown
conflicting_sources
uncertain_scope
uncertain_actor_role
insufficient_support
```

Never convert missingness to zero / absence.

---

## 5. P remains partly a separate sensor problem

P cannot be derived from the article semantics alone.

Semantic extraction can help infer:

```text
Objective Attention Constituency prior
```

but current collective attention still requires time-indexed observable evidence:

```text
search
independent discussion
professional follow-up
media / institution uptake
engagement quality
cross-platform spread
history
```

So the front-end has two related sensor paths:

```text
Raw content
   ↓
Semantic Evidence Frame
   ↓
constituency prior

External attention sources
   ↓
Attention observations
   ↓
P Evidence Packet
```

Do not let article popularity metadata substitute for the theoretical P state.

---

## 6. Evaluation strategy

The next evaluation should isolate the new layer rather than immediately reporting one end-to-end score.

### Layer E1 — semantic extraction fidelity

Give the extractor raw articles/posts/papers and compare the extracted evidence frame with Human evidence annotation.

Measure fields separately:

```text
event identity / summary fidelity
substantive actor-object recall
change/action fidelity
affected-system / scope fidelity
temporal fidelity
unsupported-inference rate
missingness honesty
```

Do not score with one opaque scalar.

### Layer E2 — downstream invariance

For the same real source, compare:

```text
Human clean semantic evidence -> D/S/P
versus
LLM extracted semantic evidence -> D/S/P
```

This directly measures how much error the extraction layer introduces.

### Layer E3 — end-to-end policy

Only after E1/E2 are understood:

```text
raw source
  ↓
extract
  ↓
D/S/P
  ↓
frozen gate
  ↓
AWARE / DROP
```

Report causal attribution for every final error.

---

## 7. Data design

Stop producing more questionnaire cases where all semantic facts are already cleanly given merely to inflate confidence.

Next useful data should be **real or realistic raw information objects** with ambiguity and irrelevant detail intact.

Preferred first corpus:

```text
12–20 diverse real articles/posts/papers
```

covering:

```text
monitored and unmonitored domains
small vs systemic impact
prominent actor but trivial event
subtle material rule/cost changes
marketing language vs actual change
multi-actor / multi-domain events
uncertain or conflicting scope
current vs historical facts
```

For P, attach separately collected / frozen attention evidence when available; otherwise evaluate D/S extraction first.

---

## 8. Relationship to the current D residuals

Before using raw-source end-to-end results as evidence about extraction quality, known D clause-application residuals must be treated separately.

Current integrated run exposed repeated D false negatives under already-clean semantic inputs:

```text
IA5 / IA6 — scope guard applied too strongly / independent market-structure clause missed
IA9       — monitored OpenAI actor given an extra significance/topic requirement
```

Therefore:

```text
D semantics                 remain frozen
D implementation            reopen
raw semantic extraction     new active frontier
```

Do not blame future raw-source extraction for errors already reproducible with clean semantics.

---

## 9. Current system model

```text
                         THEORETICAL LAYER

Real event E ---------------------------------------------+
   |                                                       |
   |                                                       v
   |                          D(E,u) / S(E) / P(E,t) / Attention Policy
   |
   v
                         SENSOR / ENGINEERING LAYER

Raw sources
   ↓
Event clustering / semantic extraction
   ↓
Semantic Evidence Frame
   +--------------------------+
   |                          |
   v                          v
D/S estimators          constituency prior
                              +
                       attention observations
                              ↓
                         P Evidence Packet
                              ↓
                         P estimator
   +--------------------------+
   ↓
frozen policy gate
   ↓
AWARE / DROP
```

---

## 10. Current pointer

```text
P semantic / estimator             CLOSED / accepted for controlled use
S semantic / estimator             CLOSED / accepted for controlled use
D semantic                         CLOSED
D implementation                   REOPEN — known clause-application residuals
Integrated first attribution       COMPLETE
Partial UNKNOWN determinacy        v1.1 implementation in progress

★ Semantic Evidence Extraction / Sensor Front-End modeling NOW
```

The next central question is:

> **Can RAOS recover sufficiently faithful semantic evidence from raw real-world information so that the already-frozen cognitive/attention variables continue to behave correctly?**
