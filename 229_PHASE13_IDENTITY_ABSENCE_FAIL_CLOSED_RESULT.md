# Phase 13 — Identity Absence Fail-Closed / Trust-Root Hardening Result

Status: **IMPLEMENTED / DOGFOOD HARDENED — PHASE 13 REMAINS ACTIVE**  
Date: **2026-09-17**  
Execution Integrity contract: **execution-integrity-v0.2**

## 1. Trigger

During acquisition-correction maintenance, a standalone Python shell called `run_pipeline()` without being launched through `raosctl` and without `RAOS_RUNTIME_PROFILE`. Repository defaults resolved to `rule + legacy + one-delta-v1`.

Phase 13 V1.0 correctly blocked identity *mismatch* when a canonical profile was present, but the no-profile path was interpreted as implicit `COMPATIBILITY`: `desired_identity=None`, `enforced=false`, and therefore Attention side effects were treated as authorized. This exposed a trust-root gap.

The incident was detected before acceptance. The temporary maintenance-generated legacy artifacts were rolled back from a database backup, corrected snapshots were marked deferred, and canonical cognition was later completed through the ATTESTED reconciler. No legacy run remains authoritative for those corrected Sources.

## 2. Root cause

V1.0 had solved:

```text
explicit canonical identity
+ resolved identity mismatch
→ FAILED
→ no canonical Attention authority
```

It had not fully solved:

```text
no desired identity at all
→ implicit compatibility
→ no attestation enforcement
→ side-effect authority accidentally available
```

Therefore the missing invariant was:

> **Identity absence must fail closed, not merely identity mismatch.**

Equivalently:

> **Absence of attestation is not attestation.**

## 3. V0.2 trust-root semantics

The default execution purpose is now `UNSPECIFIED`, not implicit `COMPATIBILITY`.

```text
UNSPECIFIED + no runtime profile
→ cognition BLOCKED
→ Attention BLOCKED
→ side effects BLOCKED
→ run_pipeline fails before AnalysisRun creation

explicit REPLAY / FORENSIC / COMPATIBILITY + no profile
→ forensic cognition allowed
→ candidate Attention may be computed
→ no canonical AttentionPlan
→ no Watch
→ no KernelPatch
→ no Delivery

CANONICAL + explicit profile
→ deterministic desired vs resolved attestation
→ capability readiness
→ side effects only when ATTESTED
```

Canonical identity mismatch remains allowed to finish forensic cognition when technically possible, but the result is quarantined before `AttentionPlan` persistence.

## 4. Reschedule side-door closure

Dogfood review found a second authority boundary: an existing completed run with a runtime-context reschedule could return through `_reschedule()` before the new-run quarantine branch.

`_reschedule()` now receives the same `ExecutionContext` and independently requires `side_effects_authorized=true`. Without authority it returns the historical/forensic run with `reschedule_suppressed=execution-authority-required` and creates no new AttentionPlan, DeliveryEnvelope, Watch, or Patch.

Thus authority is checked for both:

```text
new cognition → candidate draft → authority gate
existing run  → reschedule       → authority gate
```

## 5. Delivery defense in depth

The normal pipeline still gates before DeliveryEnvelope creation. V0.2 adds a second downstream defense:

```text
Delivery worker execution context
→ must itself have side-effect authority

DeliveryEnvelope
→ AttentionPlan
→ AnalysisRun
→ stored_run_authority()
→ only authoritative runs may be externally delivered
```

Non-authoritative envelopes are preserved as forensic database state but are excluded from external email/push and realtime delivery. A wrongly launched worker does not mutate a legitimate envelope into failure; it simply refuses to send.

## 6. Test identity

The backend test suite no longer relies on no-profile compatibility authority. Tests load a versioned `test-rule-one-delta-v1` runtime profile. Tests that inject a different provider or decision strategy must explicitly declare a matching TEST execution identity.

This keeps the test harness honest without weakening production rules.

## 7. Validation

Focused Phase 13 + delivery authority regression:

```text
19 passed
```

Full backend regression after trust-root hardening:

```text
815 passed
63 skipped
1 failed
```

The sole failure is the pre-existing Case-K acceptance residual:

```text
expected urgency = PREEMPT
current urgency  = PRIORITY
```

It is unrelated to Execution Integrity and remains intentionally untouched.

Direct process probes:

```text
bare shell / no profile
purpose      UNSPECIFIED
attestation  UNATTESTED_NO_IDENTITY
overall      BLOCKED
cognition    BLOCKED
attention    BLOCKED
side effects false

explicit REPLAY / no profile
purpose      REPLAY
attestation  UNATTESTED_REPLAY
overall      FORENSIC
cognition    READY
attention    BLOCKED
side effects false
```

Canonical Manual dogfood after restart:

```text
purpose      CANONICAL
attestation  ATTESTED
mismatches   []
overall       READY
Observation  READY
Cognition    READY
Attention    READY
Delivery     READY
```

## 8. Frozen V0.2 invariants

1. **Identity mismatch fails closed.**
2. **Identity absence also fails closed.**
3. No-profile default execution has no cognition or side-effect authority.
4. Replay/forensic computation must be explicitly requested and is never canonical Attention authority.
5. A canonical side effect requires explicit identity + successful attestation + required capability readiness.
6. Existing-run rescheduling cannot bypass the execution authority gate.
7. Delivery revalidates stored run authority before human interruption.
8. Test convenience must not create a production compatibility bypass; tests use explicit TEST identity.

Phase 13 remains active until its previously frozen closure gates, including historical incident remediation/verification and checkpoint hygiene, are fully satisfied. This result hardens the trust root; it does not declare the phase closed.
