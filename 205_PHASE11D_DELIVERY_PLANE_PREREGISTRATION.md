# Phase 11D — Delivery Plane Preregistration

Status: **PREREGISTERED / IMPLEMENTATION ACTIVE**
Date: 2026-09-15
Parent plan: `198_PHASE11_EXTERNAL_ATTENTION_INFRASTRUCTURE_PLAN.md`
Depends on: Phase 11C closed result `204_PHASE11C_P_EVIDENCE_SENSOR_ESTIMATOR_RESULT.md`

## 1. Question

Can RAOS execute an already-authorized Attention disposition through durable delivery policy so that human interruption is sparse, auditable, and channel-independent?

Frozen authority boundary:

```text
Canonical Cognition / Attention
→ DROP / AWARE / WATCH / ENGAGE
→ Delivery Plane
→ channel execution
```

```text
Delivery executes Attention.
Delivery never creates, upgrades, downgrades, or reinterprets Attention.
```
## 2. Frozen v0.1 delivery mapping

| Attention disposition | Delivery class | Default channel behavior |
|---|---|---|
| `DROP` | `SUPPRESSED` | no human-visible delivery |
| `AWARE` | `PASSIVE` | durable in-app digest only |
| `WATCH` | `HELD_BY_WATCH` | no immediate delivery; WATCH retains future responsibility |
| `ENGAGE` | `INTERRUPT` | durable in-app realtime delivery |

For `ENGAGE`, already-authorized urgency may affect execution channel only:

```text
NORMAL      → IN_APP_REALTIME
PRIORITY    → IN_APP_REALTIME + configured external channels
PREEMPT     → IN_APP_REALTIME + configured external channels
```

An unconfigured Email/Push transport is unavailable, not a failed Attention decision.

`AWARE` must never be promoted to realtime merely because an email/push channel exists. `WATCH` must never notify merely because time passed.
## 3. Durable outbox contract

Every persisted `AttentionPlan` owns at most one `DeliveryEnvelope`.

The envelope stores the source Attention decision, delivery class, selected channels, channel status, audit payload, timestamps, and optional human acknowledgement/dismissal. Enqueue is idempotent by `attention_plan_id`.

The outbox is the delivery truth layer. WebSocket/Email/Push are replaceable transports over the same envelope; transport failure must not mutate the underlying AttentionPlan.

Expected states:

```text
SUPPRESSED
PASSIVE
HELD
PENDING
DELIVERED
ACKNOWLEDGED
DISMISSED
FAILED
```

Historical delivery records remain auditable even when a serving UI is rebuilt.
## 4. Transport scope

Phase 11D v0.1 implements:

- WebSocket-backed in-app realtime delivery for `ENGAGE`;
- passive durable in-app digest retrieval for `AWARE`;
- SMTP Email transport behind explicit configuration;
- generic push-webhook transport behind explicit configuration;
- acknowledgement / dismissal and delivery metrics.

No external message is sent during dogfood unless the corresponding transport is configured. Tests use fake transports.

WATCH promotion path remains canonical:

```text
WATCH recheck
→ new AttentionPlan
→ AWARE / ENGAGE if warranted
→ new DeliveryEnvelope
```

Delivery itself never fires or promotes a WATCH.
## 5. Measurement

Phase 11D records at minimum:

- delivery envelopes by Attention disposition / delivery class;
- realtime human interruptions;
- passive surfaces;
- held WATCH responsibilities;
- suppressed DROP deliveries;
- acknowledgement / dismissal;
- per-channel success/failure/unavailability.

Initial product metric:

```text
human interruption count = delivered INTERRUPT envelopes
```

This is an execution metric, not a proxy for Attention quality. Critical-miss and false-interrupt quality require downstream human/outcome feedback and are not inferred from transport events alone.

## 6. Close criteria

11D closes when the four-disposition mapping is regression-locked, every new production AttentionPlan idempotently receives a durable envelope, WebSocket realtime delivery works on a real `ENGAGE` dogfood envelope, AWARE/WATCH/DROP remain non-interrupting, Email/Push transports are fail-closed behind configuration, delivery acknowledgement/metrics work, and no second Attention-authority path is introduced.
