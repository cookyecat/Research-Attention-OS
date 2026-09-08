# Phase 7 — Perception Fidelity Program

Status: **ACTIVE / CURRENT PROGRAM**
Date: 2026-09-08

## 1. Why Phase 7 exists

Phase 6 established an integrated path from raw information to four Attention Actions and a human-gated Kernel transition. The main remaining uncertainty is no longer whether Delta or Attention Policy can work under clear input. It is whether RAOS is shown sufficiently faithful representations of both worlds it reasons over.

```text
External World → External World Model
User Cognitive World → Brain World Model
                  ↓
                 Delta
                  ↓
           Attention Policy
```

Phase 7 therefore treats perception fidelity and state authority as the current P0 frontier.
## 2. Subphases and priority

```text
7A — External World Model Fidelity
7B — Dynamic P / Collective-Attention Evidence Interface
7C — Minimal Trusted Brain World Model
```

Exit principle:

> P0 perception modules do not need to be perfect before Phase 8. They need to be good enough that remaining errors are attributable, bounded, and safe enough for narrow continuous dogfooding.

Then move to:

```text
Phase 8 — Narrow Continuous Attention Loop
```

Do not wait for open-world perfection before learning from real trajectories.
## 3. Phase 7A — External World Model Fidelity

Primary question:

> Does the world representation admitted downstream preserve the source-grounded meaning needed for correct D/S/P/Delta/Attention judgment?

Target quality is not generic summarization quality. It is:

```text
Semantic Coverage
+ Hierarchical Abstraction
+ Evidence Fidelity
+ Downstream Decision Sufficiency
```

Canonical formulation:

> **在不丢失关键语义、不制造额外含义的情况下，形成最有决策价值的态势表示。**

First experiment: compare production-valid audited semantics against a diagnostic pre-audit Sensor representation under the same downstream Kernel and decision machinery. This is an attribution probe, not a production bypass.
## 4. Phase 7B — Dynamic P evidence

P remains theoretically distinct from D even if they share acquisition infrastructure.

```text
D: does this event belong to the user's standing attention jurisdiction?
P: has genuine collective attention formed, or is it clearly forming, inside the event's objective constituency now?
```

A future crawler may gather both source material and observable attention evidence, but the semantic estimators remain separate.

For Phase 7B, controlled / simulated time-varying attention evidence is explicitly acceptable. The immediate objective is to validate the dynamic evidence interface, temporal inertia, constituency normalization, and downstream AWARE behavior before investing in live acquisition.

Synthetic evidence is wiring/development evidence only; it must never be presented as a claim about current real-world salience.
## 5. Phase 7C — Minimal Trusted Brain World Model

The Brain World Model is a state-estimation problem with authority constraints. Start minimally:

```text
K_t
Standing Radar
active task / project
deadline
interruptibility
active WATCH obligations
recent explicit human feedback
```

Each operational state should eventually carry both value and authority/provenance. Preserve:

```text
State value != State authority
Model inference about user != authoritative user state
Estimated cognition != committed cognition
```

Phase 6C's `threatens_active_work` failure is the first canonical example motivating this boundary.
## 6. Phase 7 exit toward Phase 8

Move to narrow continuous dogfooding when:

- External World Model failures are measurable and attributable rather than mysterious;
- P has a reproducible dynamic evidence interface, even if live collection is not yet mature;
- Brain World Model has explicit trusted-state authority boundaries;
- frozen Delta and Attention Policy remain stable under these interfaces;
- no known perception residual creates an unbounded or silent protected-cognition risk.

Phase 8 should begin with a narrow real source domain and a real WATCH re-check loop, not a broad crawler.

Working rule:

> **Perception need not be perfect before deployment; it must be observable enough to learn safely from reality.**
## 7. Research discipline

1. Do not redesign Delta to compensate for a poor world representation.
2. Do not relax Auditor merely to increase semantic admission rate.
3. Do not treat diagnostic pre-audit Sensor output as production truth.
4. Compare downstream causal consequences before optimizing an upstream residual.
5. Preserve source/evidence provenance through abstraction.
6. Keep simulated P evidence explicitly labeled as simulated development evidence.
7. Move to Phase 8 once remaining perception errors are bounded and attributable, not when they disappear.
---

## 8. Phase 7A result — 2026-09-08

Status: **SUFFICIENT / WORKING BASELINE SELECTED**

Selected Sensor:

```text
v0.2.6 — predicate-explicit context-bearing
```

Phase 7A established a causal fidelity target rather than a generic extraction score. The working formulation is:

```text
Decision-Sufficient Semantic Precision
= Evidence Fidelity + Scope Fidelity + Relational Fidelity
```

See `72_PHASE7A_EXTERNAL_WORLD_MODEL_FIDELITY_RESULT.md`.

Phase 7A remains an open-world learning problem, but it is sufficiently observable and attributable to stop prompt tuning and move forward.
Current Phase 7 frontier:

```text
7A External World Model Fidelity     SUFFICIENT / BASELINE SELECTED
7B Dynamic P Evidence                ACTIVE / NEXT EXECUTION FRONTIER
7C Minimal Trusted Brain World Model QUEUED
```

Do not reopen v0.2.6 tuning from saturated RS05/RS15 unless a new cross-source or downstream-causal failure justifies it.
## 9. Phase 7B result — 2026-09-08

Phase 7B is **CLOSED / sufficient**. Dynamic simulated attention evidence was evaluated through frozen P v1 and the production no-Delta Attention Policy.

Three same-SHA repetitions produced 30/30 expected P(t) states and 30/30 expected DROP/AWARE actions across formation, established salience, short decline with inertia, sustained decay, rebound, paid exposure, synthetic trend volume, and organic attention formation.

This is development evidence for dynamic state-estimation and interface wiring only. It is not evidence about current real-world salience.

Do not continue adding synthetic P cases merely to increase confidence. Open-world collector uncertainty is deferred to Phase 8 dogfooding.

Current subphase: **7C — Minimal Trusted Brain World Model.**
