# Phase 11C — P Evidence Sensor & Estimator Preregistration

Status: **PREREGISTERED / IMPLEMENTATION ACTIVE**
Date: 2026-09-15
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`
Depends on: 11A/11B closed results `200` / `202`
Semantic baseline: `22_COLLECTIVE_ATTENTION_SALIENCE.md`
Estimator baseline: `23_COLLECTIVE_ATTENTION_ESTIMATOR_MODELING.md`
Evidence interface: `24_COLLECTIVE_ATTENTION_EVIDENCE_INTERFACE.md`

## 1. Question

Can RAOS turn measurable public-platform telemetry acquired by 11A/11B into reproducible event-level current-attention evidence for the already-frozen P estimator, without redefining P as raw popularity?

Frozen estimand remains:

```math
P(E,t)=LatentSalience(R_E(\le t))
```

No Phase 11C implementation may redefine that variable around available APIs.
## 2. Sensor storage contract

Raw engagement/rank telemetry is a sensor observation, not P.

Use compact interval samples per `(SourceDefinition, ExternalInformationItem, platform)`:

```text
same metric state on next poll → extend last_observed_at
changed metric state           → append a new sample row
```

This preserves change velocity and persistence without storing one row per polling tick.

A sample stores raw metrics, platform, first/last observation time, content-age context, quality/contamination labels, and provenance hash. Existing `AcquisitionObservation` remains the durable fact that a source observed an item; it is not mutated into a time-series record.
## 3. Magnitude-free normalization

For measurable metric `m` on platform `p`, do not compare raw counts across platforms. Candidate engineering observation:

```math
q_{p,m}=F_{p,m\mid age,context}(x_{p,m})
```

where `F` is an empirical recent reference distribution and `q` is a percentile-like magnitude-free observation.

Initial v0.1 conditions use platform + metric + coarse content-age bucket. Creator-size/domain conditioning may be added only when measurable support exists. A percentile is emitted only when reference support reaches a frozen minimum; insufficient support remains `UNKNOWN`, never a fake zero.

Magnitude-free normalization is measurement machinery, not the semantic definition of P.
## 4. Event-level evidence packet

P remains event-level:

```text
item/platform signal samples
→ Source
→ Event cluster
→ event-level P Evidence Packet
→ existing collective-attention-estimator-v1
```

Item-level telemetry may be recorded before an Event link exists. Event projection happens only when the item/source is linked to an Event. Cross-source/platform spread is itself evidence but is not a mandatory gate.

The existing joint semantic estimator remains the v1 decision mechanism. Anchors may be used for calibration/diagnostics; Pareto remains experimental and is not introduced as a mandatory P gate in Phase 11C.
## 5. Initial signal families

Phase 11C v0.1 consumes only already-publicly-observable telemetry:

- Hacker News: points, comments;
- Bilibili: views, likes, favorites, comments, danmaku;
- X public: likes, reposts, replies, quotes;
- Weibo public: likes, reposts, comments.

Missing metrics remain missing. Views are weaker evidence than active engagement and are never promoted directly into P.

## 6. Close criteria

11C closes when: (1) signal time-series capture is idempotent and compact under repeated polling; (2) changed signals create new history segments; (3) magnitude-free normalization returns UNKNOWN under insufficient support and reproducible percentiles under sufficient support; (4) at least one real Event can be projected into a provenance-preserving P Evidence Packet; and (5) the existing P estimator consumes that packet without any raw-popularity shortcut or new Attention authority path.