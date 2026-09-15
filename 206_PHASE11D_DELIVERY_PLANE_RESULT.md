# Phase 11D — Delivery Plane Result

Status: **CLOSED**
Date: 2026-09-15
Preregistration: `205_PHASE11D_DELIVERY_PLANE_PREREGISTRATION.md`
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`

## 1. Result

Phase 11D closes with a durable, channel-independent Delivery Plane downstream of canonical Attention.

```text
AttentionPlan
→ exactly one DeliveryEnvelope
→ delivery policy
→ durable outbox
→ in-app realtime / passive digest / configured external transport
→ acknowledgement or dismissal
```

The Delivery Plane does not create, reinterpret, promote, or downgrade Attention. The source `AttentionPlan` remains immutable decision authority.

## 2. Frozen delivery mapping

```text
DROP   → SUPPRESSED     → no human delivery
AWARE  → PASSIVE        → IN_APP_DIGEST
WATCH  → HELD_BY_WATCH  → no immediate delivery
ENGAGE → INTERRUPT      → IN_APP_REALTIME
```

Already-authorized `PRIORITY/PREEMPT` urgency may add configured Email/Push execution channels to ENGAGE only. Missing external transport configuration is represented as `UNAVAILABLE`; it never changes the Attention disposition.

## 3. Durable outbox implementation

`DeliveryEnvelope` is keyed uniquely by `attention_plan_id`; enqueue is idempotent. Every newly persisted production AttentionPlan now enqueues its delivery envelope inside the same database transaction, while all network execution remains asynchronous/out-of-band.

The envelope preserves:

- source Attention disposition and urgency;
- candidate identity and source payload;
- delivery class and selected channels;
- per-channel execution status / attempts / errors;
- delivery / acknowledgement timestamps;
- human acknowledgement or dismissal;
- delivery policy version.

Migration `0011_delivery_plane` was validated from a real `0010_attention_signal_samples` database copy and applied successfully to dogfood.

## 4. Realtime and external transports

Phase 11D v0.1 implements:

- `GET /deliveries` passive/interrupt retrieval;
- `GET /deliveries/metrics` execution metrics;
- `WS /deliveries/ws` durable ENGAGE realtime delivery;
- acknowledgement and dismissal endpoints;
- SMTP Email transport behind explicit configuration;
- generic Push webhook transport behind explicit configuration;
- independent `delivery_worker` for external channel execution.

Network transport failures cannot roll back or mutate cognition/Attention decisions.

## 5. Real dogfood

A real historical `ENGAGE / PRIORITY` AttentionPlan (`latency paper`) was selected without bulk historical backfill. One research envelope was created:

```text
ENGAGE / PRIORITY
→ INTERRUPT
→ IN_APP_REALTIME + EMAIL + PUSH
```

Email and Push were unconfigured and correctly remained `UNAVAILABLE`. A real localhost WebSocket client received the envelope; `IN_APP_REALTIME` transitioned `PENDING → SENT`, envelope state became `DELIVERED`, and `human_interruptions` became `1`. The same envelope was then acknowledged through the production API and moved to `ACKNOWLEDGED` while preserving the sent-channel audit trail.

The frontend now includes a global `DeliveryListener`. It only renders envelopes already classified as `INTERRUPT / ENGAGE`, offers `Open in RAOS`, `Acknowledge`, and `Dismiss`, and contains no Attention logic.

## 6. Regression / residuals

Focused backend regression:

```text
102 passed
+ 2 WATCH responsibility tests passed
```

Frontend `typecheck`, production `next build`, and dogfood restart passed. Existing Starlette/httpx deprecation warning remains unrelated.

Residuals intentionally remain outside 11D v0.1: multi-device delivery leases / duplicate-client suppression, provider-specific APNs/FCM/enterprise messaging, quiet-hour/user-channel preferences, and downstream critical-miss/false-interrupt measurement. Those require personalization/outcome evidence and must not be inferred from transport success.

## 7. Close decision

**CLOSED.** Delivery now operationalizes `Interrupt sparsely` without introducing a second cognition authority. Phase 11E Agent Interface / Skill is next.
