# Phase 13 — Execution Integrity V1.0 Preregistration

Status: **PREREGISTERED / P0 CONTAINMENT ACTIVE**
Date: **2026-09-16**
Trigger incident: `eval/incidents/20260916_google_language_false_engage/fixture.json`

## 1. Why this phase exists

A real post-reboot dogfood arrival, **Google: AI for everyone in every language**, was surfaced as `ENGAGE`. Forensic replay showed that the decision did not come from the current research-aligned Pareto Core. The live Acquisition worker had restarted under repository compatibility defaults (`rule + legacy + one-delta-v1`) because the local `.env` no longer contained the canonical cognition identity.

The incident proved two independent facts:

1. historical/compatibility cognition is not robust enough to be allowed to silently become canonical production cognition;
2. process liveness is insufficient evidence that RAOS has valid cognitive or Attention authority.

P0 containment is therefore active before implementation: Acquisition remains observable with `--no-analyze`, so new information is persisted while accidental legacy cognition is prevented from creating new canonical Attention side effects.

## 2. Frozen failure mechanism

The incident is frozen before remediation. The acceptance target is **not** an arbitrary final `AWARE` versus `WATCH` label. The forbidden causal chain is:

```text
broad lexical overlap
→ false Kernel localization
→ unrelated "rather than" accepted as target-specific CHALLENGE
→ change_magnitude forced to meaningful
→ one-delta selects false CHALLENGE
→ ENGAGE
→ Delivery + WATCH + KernelPatch proposal
```

The current implementation must preserve historical evidence of this failure; it must not rewrite the old run as if it never happened.

## 3. Execution Integrity V1.0 object model

Phase 13 introduces a deterministic **Execution Context**, not another semantic AI auditor:

```text
ExecutionContext
  purpose
  desired_identity
  resolved_identity
  build_identity
  capability_state
  attestation
```

`RuntimeProfile` defines desired semantic identity. Secrets remain local. Actual loaded provider/strategy/contracts form resolved identity. Build identity records implementation provenance. Capability state records temporary availability separately from static identity.

## 4. Frozen invariants

### I1 — Explicit execution identity
Every authoritative cognitive decision must carry explicit desired and resolved execution identity.

### I2 — Authority by attestation
Canonical Attention authority is derived from execution purpose + deterministic attestation + required capability readiness. It is not a manually writable boolean truth source.

### I3 — Graceful degradation
Failure removes only invalidated capability. Observation may continue while cognition/Attention authority is unavailable. Failure must never silently select a different semantic contract.

### I4 — Recoverability
A genuine post-baseline arrival that could not receive authoritative cognition because of a temporary technical failure must remain recoverable; delayed cognition must preserve original observation time semantics.

## 5. Configuration boundary

Canonical semantic identity becomes version-controlled configuration:

```text
Authority-bearing configuration
  cognition provider family
  cognition contract
  decision strategy
  no-Delta contract
```

Local secrets remain outside Git:

```text
LLM API key
SMTP password
private tokens
```

Operational settings such as ports, poll cadence, and logging do not define cognitive authority.

For V1.0, canonical profile configuration overrides authority-bearing `.env` values rather than allowing `.env` to silently redefine semantic identity. Compatibility/replay behavior remains available only when no canonical runtime profile is selected or when execution purpose explicitly requests it.

## 6. Authority boundary

The critical gate is placed before canonical `AttentionPlan` persistence:

```text
Cognition result / candidate draft
→ Execution Authority Gate
    ├─ not authoritative → preserve AnalysisRun forensic result only
    └─ authoritative     → AttentionPlan → WATCH / Patch / Delivery
```

A quarantined/non-authoritative canonical attempt must not create a canonical `AttentionPlan`, automatic WATCH, KernelPatch proposal, or DeliveryEnvelope.

## 7. Degraded operation

If required model credentials or dependencies are unavailable:

```text
Acquisition       may continue
Snapshot          may persist
canonical cognition/Attention authority stops
arrival remains eligible for reconciliation later
```

This is different from identity mismatch. Dependency availability is dynamic; execution identity is static for a process cohort.

## 8. Runtime operations

Manual and Service installation are orthogonal to semantic identity:

```text
Manual  = user starts RAOS after reboot
Service = OS starts/restarts RAOS automatically
```

Both must run the same versioned runtime profile. Service mode may supervise processes but may not invent or modify cognitive policy.

## 9. V1.0 acceptance gates

1. A committed canonical runtime profile exists and has a stable semantic hash.
2. `/health` exposes desired identity, resolved identity, attestation, capabilities, build identity, and overall state.
3. Missing canonical model credential yields degraded/blocked cognition, never silent legacy fallback.
4. Canonical identity mismatch cannot persist an `AttentionPlan` or its downstream side effects.
5. Compatibility/replay tests remain possible without rewriting frozen legacy behavior.
6. Google incident regression forbids the known false causal chain rather than pinning one arbitrary final disposition.
7. Manual and macOS Service launch paths select the same canonical profile.
8. `raosctl doctor` exposes enough state to diagnose process, profile, capability, and cohort mismatch.

## 10. Non-goals

V1.0 does **not** add a distributed scheduler, Kafka, Kubernetes, a new ML auditor, automatic secret rotation, full Windows/Linux service support, or a second Attention policy. The objective is **Identity + Authority + Recovery**, with minimal new machinery.
