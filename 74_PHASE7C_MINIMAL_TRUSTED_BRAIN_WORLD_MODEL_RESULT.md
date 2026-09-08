# Phase 7C — Minimal Trusted Brain World Model Result

Status: **CLOSED / SUFFICIENT FOR PHASE 7**
Date: 2026-09-08
Measurement SHA: `7575263f55d7face2088509d9b6dafdecbefc262`

## 1. Question

Phase 7C did not attempt to build a complete model of the user's mind.
It asked a narrower systems question:

> **Which claims about the user's current state are allowed to influence cognition and attention decisions, and why?**

The minimum Brain World Model therefore starts as an auditable authority boundary, not as a richer user-simulation model.

## 2. Minimal representation

`BrainStateFact` records:

```text
key / value / source / authority / observed_at / valid_until / provenance / confidence
```
Authority levels:

```text
AUTHORITATIVE
DERIVED
ADVISORY
```

Sources currently distinguish:

```text
USER_EXPLICIT_RUNTIME
SYSTEM_COMMITTED
KERNEL_COMMITTED
MODEL_INFERENCE
UNKNOWN
```

Current snapshot also anchors:

```text
committed Kernel snapshot hash
ACTIVE WATCH obligations
optional standing-radar anchor
```

Core rule:

> **State Value != State Authority.**
## 3. Production integration

Production `RuntimeContext` can now carry an explicit trusted `threatens_active_work` signal.
The pipeline constructs a `BrainWorldSnapshot` at decision time and records it in `AttentionPlan.score_debug`.

The Impact model receives only the trusted projection of that state. A model-generated guess cannot self-authorize PREEMPT.

Rescheduling captures a new Brain snapshot instead of copying the original decision-time state.
This preserves:

```text
Brain state = state at decision time t
not a permanent user profile
```

A database migration (`0007_runtime_threat_authority`) adds the trusted runtime field.
Migration upgrade/downgrade/upgrade was exercised on a temporary SQLite database.

## 4. Controlled authority probe

Four preregistered development cases used the same material cognitive effect and varied only Brain-state authority/freshness.
```text
A. model guess only
   -> trusted_threat=False -> ENGAGE / NORMAL

B. current task + model guess
   -> trusted_threat=False -> ENGAGE / NORMAL

C. explicit authoritative threat=True
   -> trusted_threat=True -> ENGAGE / PREEMPT

D. expired authoritative threat=True
   -> trusted_threat=False -> ENGAGE / NORMAL
```

Result: **4/4 matched the preregistered authority behavior.**

Relevant exact-SHA regression: **131 passed**.

This validates a second rule:

> **Confidence != Authority.**

A 0.95-confidence model inference still cannot upgrade itself into authoritative user state.
## 5. Decision

Phase 7C is sufficient for the current program objective.
It is **not** a claim that Brain World Model estimation is solved.

Known open problems belong to later live operation:

```text
how to infer active task / intent without overclaiming
how to estimate interruptibility and cognitive capacity
how to represent uncertainty over user state
how derived relations become trusted, if ever
how long state remains fresh
how longitudinal Kernel change interacts with transient runtime state
```

Do not expand the Brain World Model into a large user digital twin before Phase 8.

Next: **Phase 8 — Narrow Continuous Attention Loop.**
