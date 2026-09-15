# Phase 12 — Personalized Attention Calibration & Multi-Actor Control

Status: **CLOSED FOR CURRENT SINGLE-USER DOGFOOD — 12A/12B/12D CLOSED; 12C SKIPPED; 12E BOUNDARY CLOSED / TENANTIZATION DEFERRED**
Date: 2026-09-15
Depends on: Phase 1–10 canonical cognitive/attention core; Phase 11 External Attention Infrastructure CLOSED.

> Phase 12 is an optional calibration/control layer around a working canonical RAOS. It must improve how one human spends attention without becoming a second cognitive engine, a second D/S/P system, or a replacement for Runtime.

## 1. Architectural position

RAOS already contains substantial personalization before Phase 12:

```text
K_t       = explicit evolving cognitive state
D profile = standing attention jurisdiction
R_t       = transient runtime state used by the canonical Attention Policy
WATCH     = delegated future-attention responsibility
Delivery  = execution of an authorized Attention decision
```

Therefore Phase 12 is **not** generic user modeling and is **not** where RAOS first becomes personalized.

Its narrower question is:

> After canonical world/cognition/runtime inputs are correct, is there a stable user-specific residual in how scarce human attention should be allocated or executed?

## 2. Core-first / no-op-default contract

Canonical Phase 1–10 decision:

```math
A_t^{core}=\pi_{core}(\Delta_t,D_t,S_t,P_t,R_t)
```

Phase 12 starts with the null hypothesis:

```math
oxed{A_t^{user}=A_t^{core}}
```

Only if fresh evidence demonstrates a stable user-specific residual may an optional calibration layer be introduced:

```math
A_t^{user}=C_u(A_t^{core},T_t;\Theta_u)
```

where `T_t` is a frozen canonical policy trace/provenance object, not raw-source reinterpretation.

`C_u` must default to identity, remain versioned/auditable, and may never alter `Delta`, D, S, P, Runtime truth, Decision Cause, or Kernel authority.

## 3. Runtime ownership — frozen core boundary

`R_t` belongs to the Cognitive Transition Model v2.1 / canonical Attention Policy core:

```math
\Delta_t=F_	heta(E_t,K_t,L_t)
```

```math
A_t^{core}=\pi_{core}(\Delta_t,K_t,R_t)
```

Runtime-only change creates a new `AttentionPlan` over the same frozen `AnalysisRun`; it does not create a new `Delta`.

Therefore Phase 12 must **not** learn or redefine:

- current task;
- deadline;
- available attention minutes;
- cognitive capacity;
- interruptibility;
- active-work overlap when represented as canonical runtime/context evidence.

A wrong runtime value is a runtime-capture error, not a personalization residual.

## 4. Residual-attribution firewall

Before any user correction becomes calibration evidence, classify its causal layer:

```text
PERCEPTION_ERROR          Sensor/Auditor representation wrong
COGNITION_ERROR           Delta / target / operation wrong
AWARENESS_ERROR           D/S/P estimation or no-Delta composition wrong
RUNTIME_CAPTURE_ERROR     R_t was wrong or stale
CORE_POLICY_ERROR         shared Attention Policy is missing/wrong universally
USER_POLICY_RESIDUAL      canonical inputs are right; this user's stable allocation differs
DELIVERY_PREFERENCE       channel/timing/execution preference only
ACTOR_CONTEXT_ERROR       Agent/task provenance or delegation context wrong
```

Only `USER_POLICY_RESIDUAL` may update `Theta_u`.

A repeated residual shared across users is evidence to reopen the core policy in a separate research phase; it must not be hidden inside personalization.

## 5. What may actually be personalized

Candidate Phase-12-owned state is intentionally small:

```text
Theta_u   stable residual attention-allocation calibration, if proven necessary
Lambda_u  delivery/channel/quiet-hour preferences
Actor policy
          delegation permissions, budgets and provenance for external Agents
```

The following remain core-owned, even though some are user-specific state:

```text
K_t       Cognitive Kernel
D profile Standing Attention Jurisdiction
R_t       Runtime Context
Delta     Cognitive Transition
S / P     world/event variables
WATCH     responsibility semantics
```

This distinction is crucial: **user-specific does not automatically mean Phase-12-owned.**

## 6. Phase decomposition

```text
12A  Personalization Boundary & Feedback Attribution
12B  Residual Necessity Test
12C  Bounded Attention Calibration       [conditional on 12B]
12D  Multi-Actor Attention Arbitration
12E  Multi-user & Product Scale
```

### 12A — Personalization Boundary & Feedback Attribution
Separate cognition correction, awareness/sensor error, runtime correction, core-policy error, true user-policy residual, delivery preference, and Agent context. Preserve every historical decision and correction.

### 12B — Residual Necessity Test — CLOSED
Current deterministic audit found zero personalization-eligible residual rows and the Phase-10E proxy operating-regime probe had zero mismatches. `Theta_u = identity`; no non-identity calibration is currently justified.

### 12C — Bounded Attention Calibration — SKIPPED
12B did not demonstrate a repeatable causally clean personal residual. No calibration model is introduced. Reopen only if the flywheel later produces repeated eligible `USER_POLICY_RESIDUAL` evidence.

### 12D — Multi-Actor Attention Arbitration — CLOSED
Many Agents now share canonical WATCH responsibilities through `WatchDelegation` provenance. Exact normalized agent delegations reuse one canonical Watch, actor-local cancellation preserves remaining responsibility, and the last delegation releases only an agent-only Watch. No actor priority, quota or fairness weight was added because no material contention has been observed.

### 12E — Multi-user & Product Scale Boundary — CLOSED / TENANTIZATION DEFERRED
The state-ownership boundary is frozen as shared external-world state versus private Brain/Attention/authenticated-observation state. The runtime now declares `SINGLE_USER_DOGFOOD` and `multi_user_isolation=false`. No schema-wide tenantization is justified before an actual second-user or external deployment requirement exists.

## 7. Feedback semantics

Passive product behavior is not Human Gold:

```text
Open / click        != ENGAGE
No open             != DROP
Dismiss             != low value
Acknowledge         != correct policy
Long dwell          != importance
Agent request       != human urgency
```

Existing append-only `AttentionFeedback` is a valuable historical asset because it preserves system prediction and user correction without rewriting `AttentionPlan`. Phase 12 must refine its **attribution**, not discard this immutability principle.

A correction to `update / target / delta_content` is cognitive adjudication. A correction to `disposition` with canonical cognition held fixed is a candidate policy residual. These must never be flattened into one training label.

## 8. Historical 30-case questionnaire

The 2026-09-05 elicitation remains useful for hypothesis discovery: future option value, generative potential, interruption cost, and active-work overlap were all surfaced early.

It predates mature D/S/P, later cognitive-path reconciliation, Phase 11 WATCH/Delivery/Agent infrastructure, and today's explicit core/runtime boundaries. It is therefore **development evidence, not current calibration Gold**.

The 2026-09-15 Oracle-Delta run is likewise exploratory instrumentation only. Its no-Delta cases lack current D/S/P evidence, and runtime mismatches cannot be interpreted as personalization residuals without first validating core Runtime capture/policy behavior.

## 9. Research questions

- **RQ12.1:** After K, D/S/P, Delta and Runtime are correct, does a stable user-specific Attention residual still exist?
- **RQ12.2:** Can feedback be causally attributed before entering personalization so core bugs are not absorbed by `Theta_u`?
- **RQ12.3:** If a residual exists, what is the smallest bounded calibration family that improves decisions over the identity baseline?
- **RQ12.4:** Can many Agents safely delegate through one RAOS without multiplying human interruptions or authorities?
- **RQ12.5:** Which state is core-global, user-local, actor-local, runtime-local and delivery-local at product scale?

## 10. Success and stop criteria

Success is not “a personalized model scores higher.” Success means:

```text
canonical core remains intact and auditable
+
proved personal residual, if any
+
smallest necessary calibration
+
fewer unnecessary interruptions
+
no increase in critical misses
```

Stop personalization if fresh evidence is fully explained by core/runtime/sensor errors or by `K_t` / D-profile evolution. In that case `Theta_u = identity` is the correct scientific result.

The north-star remains:

```text
more observed information
→ more automatic cognition
→ fewer unnecessary human interruptions
→ low critical-miss rate
```
