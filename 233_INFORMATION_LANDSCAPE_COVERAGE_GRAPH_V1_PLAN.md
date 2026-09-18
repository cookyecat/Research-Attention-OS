# RAOS Information Landscape / Coverage Graph V1 — Research Plan and First Slice

Status: **ADOPTED / V1A IMPLEMENTED**  
Date: 2026-09-18

## 1. Product doctrine

RAOS now adopts the following long-term distinction:

```text
Inbox basic unit      = Source / original information object
Attention basic unit  → World Event / material Claim Change
P basic unit          → Event-level collective attention
```

A Source is preserved because a publisher actually emitted it. An Event is RAOS's representation of what happened in the world. Several Sources may cover one Event without becoming several events.

Canonical flow:

```text
Acquisition
→ Source preservation
→ SourceGraph
→ Same-event / provenance / independence
→ Event-level world representation
→ Collective Attention evidence
→ D / S / P
→ Attention compression
```

## 2. Two distinct user-facing relations

### Coverage / Same story

Coverage means multiple Sources concern the same world event.

It exists to answer:

- What is this article actually reporting on?
- Where else was the same event covered?
- Which source appears official/original?
- Which reports are independent?
- Which are derived, reposted, or secondary?

Coverage may eventually contribute evidence to event-level P, but only after relation quality is audited.

### Related reading

Related means useful conceptual or topical proximity without identity of event.

It exists only for voluntary deeper reading. It must not increase event-level P and must not become an endless recommendation feed.

Permanent UX rule:

> **Coverage is world context. Related reading is optional exploration.**

Related reading is folded by default.

## 3. Why this matters for attention

If one event is reported by seven places:

```text
vivo official announcement
├─ 量子位
├─ 机器之心
├─ 新智元
├─ vivo website
├─ WeChat version
├─ Weibo discussion
└─ Bilibili discussion
```

Inbox may preserve all seven Sources.

RAOS must not conclude that seven world events occurred or demand seven units of human attention.

Long-term Attention should compress this into one event-level state plus an auditable coverage graph.

## 4. Authority boundary

Existing Event/EventSource rows are not automatically trusted same-event truth.

Current dogfood data contains historical Event rows with status `CANDIDATE`. Some multi-source candidate clusters are too weak to expose as confirmed Coverage.

V1 authority gate:

```text
same EventSource cluster alone
→ candidate evidence only

CONFIRMED Event
or
high-confidence provenance SourceEdge
→ user-visible Coverage
```

High-confidence provenance relationships currently include:

- REPOSTS
- DERIVED_FROM
- REPORTS_ON

with confidence >= 0.85.

A candidate Event can remain visible to internal tooling while `coverage_authorized=false`.

## 5. V1A — Landscape surface

Implemented first slice:

```text
GET /sources/{source_id}/landscape
```

It exposes:

- authorized Event context;
- Coverage Sources;
- SourceGraph relationship/provenance;
- current independence report;
- Related Sources;
- explicit P authorization state.

Current P state is deliberately:

```text
p_input_status = NOT_YET_AUTHORIZED
```

Therefore Coverage V1A cannot silently change P or Attention.

Reader UX:

- Coverage is visible when authorized evidence exists.
- Each source is navigable.
- Graph independence summary is shown as an audit hint.
- Related reading is collapsed by default.
- No “you may also like” recommendation framing is used.

## 6. V1B — Same-event candidate generation

Next stage runs in shadow mode only.

Candidate generation should optimize recall using cheap signals such as:

- publication time proximity;
- shared named entities;
- title/event lexical overlap;
- canonical links and explicit references;
- publisher metadata;
- normalized product/model/company names;
- embedding similarity where available.

Candidate generation must never itself merge Events.

## 7. V1C — Same-event adjudication

Candidates pass a higher-precision adjudication layer that decides among concepts such as:

```text
SAME_EVENT
DERIVED_FROM
REPOST
INDEPENDENT_REPORT
RELATED_DIFFERENT_EVENT
UNRELATED
UNCERTAIN
```

Adjudication must preserve evidence/provenance and confidence.

Only sufficiently supported SAME_EVENT facts may confirm/merge Event representation.

Target before automatic authority: high precision over recall. False grouping is more damaging than missing a relationship because false grouping can corrupt P and attention compression.

## 8. V1D — Coverage as P evidence

Only after dogfood relation precision is established may Coverage enter P.

Event-level collective attention should be estimated from evidence families rather than one platform metric:

```text
P(E,t) = Estimator(
    AudienceAttention,
    EditorialCoverage,
    SearchInterest,
    CrossPlatformSpread,
    Velocity,
    ...
)
```

EditorialCoverage must count independent coverage rather than raw Source count.

Reposts, mirrors, alternate transports, and duplicated article versions must not multiply P.

## 9. V1E — Event-level Attention

Only after Event clustering and P evidence are stable should the Attention surface move from Source-level repetition toward Event / Claim Change.

Inbox remains Source-oriented.

This preserves the product distinction:

> Inbox answers “what did RAOS observe?”  
> Attention answers “what happened in the world that deserves consciousness?”

## 10. Historical backfill

Do not bulk-backfill WeChat or other publishers before Same-event relation quality is established.

Preferred sequence:

```text
live observation
→ Coverage Graph dogfood
→ precision audit
→ limited recent-window backfill
→ calibration
→ wider history only if useful
```

## 11. Positive Core dogfood case

Source:

```text
量子位
“被英伟达点名的杭州团队，补上了AI for Science的「最后一公里」”
```

Observed decision:

```text
D = IN
S = NOT_MATERIAL
P = UNKNOWN
→ DROP
```

User feedback: judgment is highly accurate.

Interpretation: the source is inside a monitored research/AI area, but a single company's product announcement does not by itself constitute material disturbance to an important shared reference system. No evidence established structural change to accepted knowledge, standards, or industry-wide practice.

This is a **positive Core example**, not a tuning failure.

Permanent lesson:

> Surface relevance, prestigious-name association, and product usefulness must not be allowed to masquerade as material consequence.

Do not tune Core against this case without contrary real evidence.


## 12. V1B first shadow result — 2026-09-18

V1B shadow candidate retrieval is now implemented:

```text
GET /sources/{source_id}/same-event-candidates
mode = SHADOW_CANDIDATE_RETRIEVAL
authority = NONE
mutates_graph = false
```

The retriever currently uses cheap title-structure and time-proximity signals only. It is intentionally a recall mechanism, not a truth estimator.

Real dogfood example:

Primary:

```text
Ars Technica
Google announces new experimental "CC" AI agent for families
```

Top shadow candidates included:

```text
#1 Google and UN system launch new global data platform
#2 CC is an AI agent for families and groups
```

The #2 item is the plausible same-event Google publisher source; #1 is a false positive caused by broad Google/AI/title similarity and temporal proximity.

Research conclusion:

> **Candidate ranking quality is not same-event truth.**

Do not attempt to solve this by treating a lexical-score threshold as authority. V1C must adjudicate event identity using event semantics, named entities, action/predicate, temporal compatibility, provenance, and source summaries. Dense retrieval may improve recall but does not replace adjudication.
