# Phase 11 — External Attention Infrastructure

Status: **CLOSED — 11A–11E COMPLETE 2026-09-15**
Date: 2026-09-15
Depends on: Phase 1–10 cognition / attention baselines, Acquisition Plane v0.1, frozen D/S/P semantics.

> Phase 11 turns RAOS from a system that can judge attention into infrastructure that can continuously observe a larger world, assume delegated future-attention responsibility, and interrupt the human only when warranted.

## 1. North-star question

Can RAOS continuously watch a world larger than a human can personally monitor, assume responsibility for deciding when that world deserves the human back, and expose the same canonical attention authority to external agents?

```text
User / Agent
    ↓
WATCH / observation intent
    ↓
Query Expansion
    ↓
Broad Acquisition Adapters
    ↓
Event clustering + attention evidence
    ↓
P Evidence / P Estimator
    ↓
Canonical RAOS Cognition
    ↓
DROP / AWARE / WATCH / ENGAGE
    ↓
Delivery Plane
    ↓
Human only when warranted
```
## 2. Phase decomposition

### Phase 11A — Acquisition Expansion
Add pragmatic external adapters while preserving the existing `Source → Observation → Information Object → Snapshot` ontology. Initial targets: Hacker News, Bilibili, Sogou/web search. Research dimensions: coverage, freshness, reliability, cost, duplicate rate, source-failure isolation.

### Phase 11B — Query Expansion / Active Acquisition
Expand WATCH / observation intents into retrieval queries to improve world-observation recall under bounded acquisition cost. Query expansion may change where RAOS looks; it may not decide D/S/P or Attention.

### Phase 11C — P Evidence Sensor & Estimator
Collect real event-level attention evidence (engagement, rank, velocity, breadth, persistence, independent uptake) and map it to frozen `P(E,t)` semantics. Raw popularity is evidence, never Attention authority. Magnitude-free platform normalization is a primary engineering candidate; estimator architecture remains empirical.

### Phase 11D — Delivery Plane
Map already-authorized Attention dispositions to delivery behavior. `DROP → silence`; `AWARE → passive/digest`; `WATCH → delegated monitoring, no immediate interruption`; `ENGAGE → Today / realtime delivery when warranted`.

### Phase 11E — RAOS Agent Interface / Skill
Expose one canonical RAOS authority through stable API/CLI/MCP/Skill surfaces such as `today`, `attention`, `analyze`, `watch`, `watch-status`, `why`, and `observe`. External agents must never create a second cognition path.

### Phase 12 — Personalization / Scale
The previously planned Phase 11 (`Questionnaire prior + trajectory residuals + multi-user/product validation`) is intentionally moved to Phase 12, after the external attention loop is operational.
## 3. Phase 11 invariants

1. Acquisition observes; it does not decide Attention.
2. Query Expansion improves observation recall; it does not define relevance or importance.
3. Raw popularity is evidence for P; it is never Attention authority.
4. P is event-level, not Source-level.
5. Missing / unavailable evidence is not zero evidence.
6. Delivery executes Attention decisions; it does not create them.
7. WATCH is delegated future-attention responsibility, not a bookmark label.
8. Agent interfaces reuse canonical RAOS semantics; there is one cognition authority.
9. DROP observations remain preserved; filtered does not mean nonexistent.
10. Peripheral machinery may be borrowed aggressively; semantic authority remains RAOS.

## 4. Research questions

- **RQ11.1:** Can broad adapters materially increase external-world coverage without contaminating cognition authority?
- **RQ11.2:** Can Query Expansion improve recall at fixed acquisition budget while controlling semantic drift?
- **RQ11.3:** Can observable cross-platform signals support a defensible estimate of frozen `P(E,t)`?
- **RQ11.4:** Can Attention-aware delivery reduce human interruptions while keeping critical misses very low?
- **RQ11.5:** Can external agents use RAOS without creating a second cognition / authority path?

## 5. Execution order

```text
11A → 11B → 11C → 11D → 11E → 12
```

Do not advance merely because code exists. Each subphase requires its own preregistered contract, dogfood evidence, residual attribution, and explicit close/continue decision.

## Phase 11A-H — Acquisition Hardening Backlog

Deferred without reopening 11A core. Implement after/alongside Phase 11C when platform signal coverage needs it.

- `X_SEARCH`: Top + Latest lanes with raw engagement + query provenance.
- `WEIBO_HOT`: hot rank / heat / first-seen / rank-delta as public-attention evidence.
- shared `PublicTransportPolicy`: browser UA, anonymous visitor state, referer/language, jitter, backoff, Retry-After, host/platform concurrency.
- platform-aware rate limiting / acquisition budget.
- account/entity resolution: human/entity name → platform identities / creator SourceDefinitions.
- freshness normalization by platform / source class.
- acquisition-only source priority for scheduling; MUST NOT influence D/S/P/Attention authority.

Invariant: copy acquisition transport/signal machinery aggressively; do not copy Hotspot semantics into RAOS truth or cognition authority.

## 6. Closure

All five subphases closed on 2026-09-15. RAOS now has broad acquisition, WATCH-driven query expansion, real public-attention evidence for event-level P, durable sparse delivery, and a stable external Agent API/CLI/Skill that preserves one canonical cognition authority.

The Acquisition Hardening backlog above remains intentional infrastructure follow-up and does not reopen Phase 11 semantics. Phase 12 — Personalization / Scale — is next.
