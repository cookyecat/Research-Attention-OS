# Phase 12 — Architecture Review after Phase 11

Status: **ARCHITECTURE REVIEW / ACCEPTED DIRECTION**
Date: 2026-09-15
Reviewed against: Cognitive Transition Model v2.1, Attention Policy Input Clarification, current canonical architecture, Phase 11 Agent/Delivery closure.

## 1. Executive verdict

The original Phase 12 idea was directionally useful but too broad for the current RAOS architecture. The redesigned Phase 12 must be an **optional residual calibration and multi-actor control layer**, not a new personalization core.

RAOS already personalizes substantially through explicit `K_t`, the D profile, and runtime-conditioned canonical Attention. Phase 12 must first prove that a stable user-specific residual remains after those core mechanisms are correct.

```text
Core correct + no stable personal residual
→ identity calibration is the right result

Core correct + repeated stable personal residual
→ smallest bounded calibration may be justified
```

## 2. Runtime clarification

`R_t` belongs to the frozen Cognitive Transition Model v2.1 architecture but is semantically separate from `Delta_t`.

```math
\Delta_t = F_\theta(E_t,K_t,L_t)
```

```math
A_t = \pi(\Delta_t,K_t,R_t)
```

`AnalysisRun` freezes cognitive judgment. Runtime-only change creates another `AttentionPlan` without changing the frozen AnalysisRun / Delta. `RuntimeContext` is explicitly excluded from AnalysisRun identity.

Therefore Phase 12 must never learn deadline, cognitive capacity, available attention, interruptibility, or active task as durable personalization parameters. Wrong runtime values are runtime-capture/core-policy issues.

## 3. Phase 12 is not first-order personalization

Pre-Phase-12 user specificity already exists:

| State | Owner | Meaning |
|---|---|---|
| `K_t` | Core | evolving committed cognition |
| D profile | Core | standing attention jurisdiction |
| `R_t` | Core | transient runtime condition |
| WATCH | Core | delegated future-attention responsibility |
| Delivery | Phase 11 execution | delivery of authorized attention |
| Agent provenance | Phase 11 interface | delegation/invocation context |

Phase 12 may only own a proven stable residual `Theta_u`, delivery preferences `Lambda_u`, and multi-actor delegation/arbitration configuration.

## 4. Core-first mathematical contract

The canonical core remains independently executable:

```math
A_t^{core}=\pi_{core}(\Delta_t,D_t,S_t,P_t,R_t)
```

Phase 12 starts at identity:

```math
A_t^{user}=A_t^{core}
```

Only after a fresh residual-necessity study may an optional calibration be introduced:

```math
A_t^{user}=C_u(A_t^{core},T_t;\Theta_u)
```

`T_t` is frozen policy provenance, not raw-source reinterpretation. `C_u` may not alter Delta, D/S/P, Runtime truth, Decision Cause, WATCH semantics, or Kernel authorization.

## 5. Residual attribution is the firewall

A user disagreement with RAOS is not automatically personalization evidence. Attribute first:

```text
PERCEPTION_ERROR
COGNITION_ERROR
AWARENESS_ERROR
RUNTIME_CAPTURE_ERROR
CORE_POLICY_ERROR
USER_POLICY_RESIDUAL
DELIVERY_PREFERENCE
ACTOR_CONTEXT_ERROR
```

Only `USER_POLICY_RESIDUAL` may train/calibrate `Theta_u`.

This is the Phase-12 analogue of the existing rule:

```text
BadSensor != ChangePhysics
```

Here:

```text
CoreBug != PersonalPreference
```

## 6. Historical Human Gold decision

The 2026-09-05 30-case questionnaire remains useful only for hypothesis discovery. It predates mature D/S/P, later cognitive-path reconciliation, Phase 11 WATCH/Delivery/Agent infrastructure, and the current core/runtime boundary.

Do not fit Phase 12 to it.

Its useful discoveries — future optionality, generative potential, interruption cost and active-work overlap — should be treated as candidate explanations to test afresh, not as current labels.

## 7. Feedback asset review

The existing `AttentionFeedback` design has one strong property worth retaining:

```text
system prediction + append-only user correction
without rewriting historical AttentionPlan
```

But its old public contract can mix cognitive adjudication (`update`, target, delta content) with disposition correction. Phase 12 must distinguish these causal classes before learning.

Current dogfood database audit on 2026-09-15 found:

```text
AttentionFeedback rows = 0
```

Therefore the schema/contract can be cleaned up without reinterpreting historical real-user feedback records.

## 8. Revised research sequence

```text
12A  Boundary & Feedback Attribution
12B  Residual Necessity Test
12C  Bounded Calibration, only if justified
12D  Multi-Actor Attention Arbitration
12E  Multi-user / Product Scale
```

The ordering is intentional. Phase 12 does not assume personalization is needed; it earns the right to personalize.

## 9. Architecture stop conditions

Stop or redirect Phase 12 if:

- residuals disappear after fixing core/runtime/sensor errors;
- the proposed calibration needs to reinterpret Delta or D/S/P;
- a factor appears universal across users and therefore belongs in the shared core;
- passive UI behavior is the only evidence for a claimed preference;
- multi-agent support requires independent Agent attention authorities.

## 10. Final positioning

Phase 1–10 remains the RAOS cognitive/attention core. Phase 11 connects that core to the external world, delivery and Agents. Phase 12 is a **non-essential but potentially valuable control/calibration layer** around a functioning system.

The strongest concise definition is:

> **Phase 12 calibrates residual human attention economics only after the canonical RAOS core has already explained the world, cognition and runtime correctly.**
