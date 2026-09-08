# Phase 7A — External World Model Fidelity Result

Status: **SUFFICIENT FOR PHASE 7 / WORKING BASELINE SELECTED / NOT OPEN-WORLD COMPLETE**
Date: 2026-09-08

## 1. Question

Phase 7A did not ask whether the Sensor could emit more facts or achieve a cosmetically higher admission rate.

It asked:

> **Does the External World Model preserve the source-grounded semantic state that downstream cognition and attention actually depend on?**

The operational target is **Decision-Sufficient Semantic Precision**.
## 2. Causal experiment

The main attribution probe compared:

```text
A — production-valid world
Sensor → Auditor → admitted semantics → same Delta / Attention machinery

B — diagnostic information-availability world
pre-audit Sensor semantics → same Delta / Attention machinery
```

Condition B is not production truth and not an oracle. A stable A/B difference only shows that semantic admission changed the world shown downstream.

Key finding:

> **Low admission rate != bad world model.**

RS05 could retain only a small subset of units and still preserve the decisive `CHALLENGE → ENGAGE` relation when the right semantic predicate survived.
## 3. RS15 causal failure

The first production-valid RS15 representation admitted only 2/7 cognitive units and consistently redirected Delta from the pre-audit `Q2` meaning toward `B2`.

Root cause:

```text
cohesive semantic unit
+ one unsupported adjunct
↓
binary Auditor rejection
↓
supported core meaning also disappears
↓
External World Model loses the world-model / implicit-coordination meaning
↓
Delta lands on a different Kernel object
```

This established a real causal bottleneck. It justified Sensor work because the upstream residual had now changed downstream cognition / attention.
## 4. Controlled Sensor revisions

### v0.2.4 — evidence-complete cohesion

Added one rule: every materially distinct clause must be covered by cited evidence; narrow unsupported adjuncts instead of discarding supported core meaning.

Result:

```text
RS15: causal Q2 meaning recovered
RS05: regressed badly; Auditor admitted 0/9 and Delta lost CHALLENGE
```

Interpretation: a locally successful repair can overfit a source style.

### v0.2.5 — context-bearing evidence

Added the requirement that experimental setup / scope evidence must travel with conclusions whose truth conditions depend on that setup.

This repaired evidence closure for the key RS05 workload unit, but the downstream CHALLENGE still did not reliably return.
### v0.2.6 — predicate-explicit context-bearing

Added a final general rule: do not replace an explicit causal/comparative/dominance relation with only a semantic label that requires downstream re-decoding.

Example:

```text
weak representation:
"overhead-bound"

relation-preserving representation:
"kernel preparation / launch dominates useful computation"
```

Canonical research memory:

> **A semantic label is not a substitute for the relation it summarizes.**

> **语义标签不能替代它所概括的关系本身。**
## 5. v0.2.6 decision-fidelity results

Targeted heterogeneous probes:

```text
RS15
Audited 7/10 → REINFORCE(Q2) 3/3
Full   10/10 → REINFORCE(Q2) 3/3

RS05
Audited 4/10 → CHALLENGE(CF-B-PERF) → ENGAGE 3/3
Full   10/10 → CHALLENGE(CF-B-PERF) → ENGAGE 3/3
```

Cross-source regression:

```text
RS11: NONE / DROP remained stable.
RS12: weak positive Delta showed boundary jitter, but no stable representation-driven landing-point divergence repeated across runs.
```

Therefore v0.2.6 is selected as the **Phase 7A working Sensor baseline**, not as a claim of open-world semantic perfection.
## 6. Working formulation

Phase 7A supports the following engineering formulation:

```text
Decision-Sufficient Semantic Precision
=
Evidence Fidelity
+ Scope Fidelity
+ Relational Fidelity
```

This is an engineering decomposition, not a new frozen mathematical variable.

Research memory:

> **Sensor 真正需要的不是“多”，而是“在正确的语义位置上精准”。**

> **A good Sensor does not flood the downstream system with facts. It delivers the right semantic state at the point where the decision depends on it.**

> **好的 Sensor 不是把事实灌满下游，而是在决策真正依赖的地方，精准交付正确的语义状态。**
## 7. GPT-5.6 Sol reference

A GPT-5.6 Sol assistant-authored one-pass reference was evaluated through the same Auditor and downstream decision probe.

Observed lesson:

```text
stronger hierarchical abstraction
!= automatic provenance-contract compliance
```

RS15 retained the intended Q2 meaning cleanly. RS05 one-pass wording over-specified one critical measurement beyond what its attached support marker directly carried, so the binary Auditor rejected the unit and the audited CHALLENGE disappeared.

An explicitly labeled audit-guided curated oracle narrowed unsupported wording without adding outside knowledge. It then preserved:

```text
RS15 → Q2 / WATCH
RS05 → CHALLENGE / ENGAGE
```

This is an upper-bound workflow reference, not a one-pass model score or Human Gold.
## 8. Auditor noise and metric discipline

Repeated audits showed that identical semantic units can receive different binary admission counts across model calls. Therefore:

> **Single-run Auditor admission rate is not a model-capability score.**

Prefer repeated downstream decision fidelity and stable causal direction over superficial pass-rate comparisons.

## 9. Anti-overfitting lesson

v0.2.4 is a concrete researcher-overfitting example:

```text
fix RS15 locally
→ RS15 improves
→ RS05 regresses
```

A mechanism should not graduate because it repairs the case that created it. It must survive materially different source styles and downstream causal checks.

This reinforces `56_SENSOR_AUDITOR_GENERALIZATION_AND_ANTI_OVERFITTING_PROTOCOL.md`.
## 10. Phase decision

```text
Semantic Sensor production/development working baseline:
    v0.2.6 predicate-explicit context-bearing

External World Model fidelity:
    SUFFICIENT TO MOVE FORWARD
    NOT CLOSED AS AN OPEN-WORLD PROBLEM

Known residuals:
    model-capability dependence
    semantic/audit stochasticity
    weak-Delta / policy-boundary jitter
    future unseen source-style failures
```

Do not keep tuning Sensor prompts on RS05/RS15 now.

Next:

```text
Phase 7B — Dynamic P / simulated collective-attention evidence
Phase 7C — Minimal Trusted Brain World Model
then Phase 8 — Narrow Continuous Attention Loop
```

Phase 7A exit rule is satisfied because remaining errors are observable and attributable rather than silent and mysterious.
## 11. Precision does not mean decimal maximalism

The RS05 `23.104 us` case exposed a useful distinction.
Keeping an exact measurement can be correct, but the number is not automatically a first-class semantic unit.

For the downstream decision, the important state was the scoped relation:

```text
64x64 bf16 matmul+add under the measured setup:
GPU kernel time is tiny relative to CPU wall time,
so kernel preparation / launch dominates useful computation.
```

`23.104 us` is valuable as quantitative support for that relation. It is not valuable merely because it has three decimal places.

> **Semantic precision means preserving the decision-bearing relation with sufficient evidence, not maximizing numerical detail.**

This also refines the earlier packaging failure: Sensor factual correctness and Auditor correctness can coexist when statement granularity, support granularity, and audit granularity are misaligned.
