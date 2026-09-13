# RAOS Acquisition Plane v0.1 — Top-Level Design

Date: 2026-09-13
Status: FROZEN FOR V0.1 IMPLEMENTATION

## 1. Purpose

RAOS needs a persistent way to observe the external information world without requiring manual copy/paste. Acquisition is the subsystem that makes external information observable to RAOS.

Its responsibility is:

```text
External World
    ↓
Acquisition Plane
    ↓
Raw Information Boundary
    ↓
Information Plane / Sensor / Auditor / Cognition
```

Acquisition answers:

> What became observable?

RAOS cognition answers:

> What does it mean to me now?

These responsibilities must remain separate.

## 2. Top-level objects

Acquisition v0.1 has four semantic objects.

### Source

A persistent observation point chosen by the user or system operator: a feed, website, account, API, publication, repository, or other information origin.

A Source defines **where RAOS looks**, not what RAOS should care about.

### Observation

A record that a Source made an external information object observable to RAOS.

Conceptually:

```text
Observation = (Source, Information Object, Time)
```

Observation is distinct from the information object itself.

### Information Object

An externally existing information object such as an article, post, paper, release, announcement, or video.

The same Information Object may be observed through multiple Sources.

### Snapshot

A captured state of an Information Object at a point in time. Snapshots preserve the boundary between an external object's identity and its observable content state.

## 3. Core invariants

1. **Acquisition observes; it does not judge.**
2. **Source selection defines observation scope, not cognitive relevance.**
3. **Observation and Information Object are distinct.**
4. **Information Object identity and observable content state are distinct.**
5. **Acquisition ends at the Raw Information Boundary; cognition begins downstream.**

Therefore Acquisition must not decide DROP/AWARE/WATCH/ENGAGE, Kernel relevance, relation type, truth, importance, or cognitive update.

## 4. RAOS system position

```text
W_t  External world
 ↓ Acquisition
I_t  Observable information
 ↓ Information Plane / Sensor / Auditor
 ↓ Cognition conditioned on K_t
Decision_t
 ↓ authorized update
K_{t+1}
```

Acquisition extends RAOS to the left; it does not redefine the Information Plane or Cognitive Plane.

## 5. v0.1 implementation scope

The first implementation only needs to prove the semantic chain:

```text
Source
→ Observation
→ Information Object
→ Snapshot
→ existing RAOS Source ingestion
→ existing RAOS analysis pipeline
```

RSS is the first concrete transport because it provides a simple, stable way to exercise the architecture. Existing URL ingestion remains authoritative for article retrieval and normalization.

Other transports such as X, APIs, newsletters, browser automation, RSSHub, or authenticated sources are intentionally deferred. They should become additional adapters without changing the four-object model above.

## 6. v0.1 success condition

A configured Source can be polled automatically; newly observed external information becomes a persistent Information Object and Snapshot, is delivered into the existing RAOS Source boundary, and can proceed through the already-deployed research-aligned cognition pipeline without manual copy/paste.

The architecture is considered sufficient for v0.1 once this chain works in real dogfood. Further acquisition semantics should be driven by observed residuals rather than anticipated corner cases.
