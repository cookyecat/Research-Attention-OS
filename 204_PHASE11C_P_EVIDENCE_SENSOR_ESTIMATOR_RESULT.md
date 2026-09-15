# Phase 11C — P Evidence Sensor & Estimator Result

Status: **CLOSED / 11D NEXT**
Date: 2026-09-15
Preregistration: `203_PHASE11C_P_EVIDENCE_SENSOR_ESTIMATOR_PREREGISTRATION.md`
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`
Estimator baseline: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`
Evidence interface: `24_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE.md`

## 1. Result

Phase 11C closes successfully without changing the frozen meaning of `P(E,t)`.

```text
public platform telemetry
→ compact Attention Signal Ledger
→ magnitude-free platform/context normalization
→ Event-level P Evidence Packet
→ existing collective-attention-estimator-v1
→ SALIENT / NOT_SALIENT
```

Raw popularity remains evidence only. No signal value, percentile, platform, or popularity shortcut acquired D/S/P or Attention authority.
## 2. Signal ledger

New durable model: `AttentionSignalSample` (`attention_signal_samples`).

The storage rule is state-segment compression rather than one row per poll:

```text
same platform + metrics + content-age bucket
→ extend last_observed_at

changed metrics OR changed content-age bucket
→ append a new state segment
```

This preserves velocity/persistence history while bounding growth by signal-state changes rather than polling frequency.

A composite `(platform, external_item_id, first_observed_at)` index supports latest-state reference lookup. At much larger scale, a rebuildable current-state projection/materialized view is preferred over flattening the historical truth ledger.

Migration `0010_attention_signal_samples` was validated on a copied 0009 SQLite database and creates the table plus expected indexes successfully. The live dogfood DB was already auto-created from ORM metadata; after schema verification it was safely stamped to 0010.
## 3. Magnitude-free normalization

`attention-signal-magnitude-free-v0.1` estimates a platform/context-relative percentile instead of comparing raw counts across platforms.

Current v0.1 conditioning:

- platform;
- metric;
- coarse content-age bucket;
- latest state per external item only.

Important corrections made during implementation:

1. historical state segments from one item do not receive repeated weight in the cross-sectional reference distribution;
2. content-age bucket changes create a new segment even when raw metrics are unchanged;
3. reference scans are bounded and indexed;
4. support below the frozen minimum returns `INSUFFICIENT_SUPPORT` / percentile `null`, never zero.

Creator-size/domain conditioning remains a future measured-data refinement, not an invented prior.
## 4. Live dogfood

Live polling on the real dogfood DB produced public signal samples from three existing source families:

```text
HACKER_NEWS  5
BILIBILI     5
WEIBO        5
```

For the HN/Bilibili set, an immediate second poll kept the ledger at 10 rows and extended the unchanged state intervals instead of appending 10 duplicate rows.

Four existing real HN-linked Events could be projected directly into schema-valid P Evidence Packets. Their current HN evidence was low (1–3 points, 0 comments), normalization support was honestly `UNKNOWN`, and the frozen estimator returned `NOT_SALIENT` for all four without transport/schema failure.

Example behavior:

```text
raw HN points/comments
+ UNKNOWN percentile support
+ short persistence history
→ joint semantic P estimator
→ NOT_SALIENT
```

No new P formula or raw-popularity threshold was introduced.
## 5. Residuals

Phase 11C closes at the preregistered interface boundary, with several explicit residuals:

- current real dogfood Events with measurable telemetry are mostly single-platform; cross-platform packet behavior is regression-tested but not yet common in live data;
- historical Event clustering still contains shallow one-Source/one-Event cases; P remains defined over the underlying Event and must not be redefined around that upstream limitation;
- X has no currently enabled public source in dogfood; Weibo/HN/Bilibili are the current live signal families;
- real normalization support is still sparse, so production packets often emit `UNKNOWN` percentiles; this is correct missingness behavior;
- million-scale ledgers should add a rebuildable current-state projection/materialized view while retaining append-only historical truth;
- the Phase 11A-H backlog (`X_SEARCH`, `WEIBO_HOT`, shared public transport, platform rate limiting, entity/account resolution, freshness normalization, acquisition scheduling priority) will expand P sensor coverage later.

A tooling invariant was also recovered: the configured SQLite URL is relative. Research scripts that need the production dogfood DB must run from `backend/` (or use an absolute DB URL) so they do not silently connect to another `./raos.db`.

## 6. Validation

Focused Phase 11A–11C + P/No-Delta regression:

```text
42 passed
1 existing Starlette/httpx deprecation warning
```

Phase 11C-specific regression after final normalization/history hardening:

```text
9 passed
```

The warning predates this phase and is unrelated to the implementation.
## 7. Close decision

All preregistered close criteria are satisfied. Phase 11C is **CLOSED**.

The key result is not that RAOS now has a perfect P measurement. It is that measurable public attention signals now enter the correct evidence boundary with history, provenance, scale-aware normalization, and honest missingness while the frozen P semantics remain unchanged.

Next:

```text
Phase 11D — Delivery Plane
Attention decision → delivery policy → human interruption only when warranted
```
