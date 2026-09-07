# Semantic Sensor — Research / Production Model Strategy

Status: **ACTIVE METHODOLOGY / ENGINEERING PRINCIPLE**  
Date: 2026-09-08

> **研发阶段买清晰度，生产阶段买效率。**  
> **During research, buy clarity. During production, buy efficiency.**

---

# 1. Why this principle exists

Semantic Sensor development currently has two very different optimization problems:

```text
Research question:
What representation / stopping rule / semantic basis is actually correct?

Production question:
How can the same useful behavior be delivered cheaply, privately, and at scale?
```

Trying to solve both at once creates attribution confusion.

A weaker local model may be attractive for eventual production, but during early research it can make every failure ambiguous:

```text
Did the representation idea fail?
Did the prompt fail?
Did the model simply lack capability?
```

Therefore the current development strategy is:

```text
Research phase
  use strong remote models as capability / quality probes
  establish the semantic target and failure taxonomy first
  measure model-vs-formulation residuals explicitly

Production phase
  move routine Semantic Sensor work toward local/open models
  distill or reproduce the validated behavior
  use selective escalation to stronger remote models only when needed
```

---

# 2. Research-phase objective

Strong models are not the production architecture by default. They are research instruments.

Their purpose is to answer questions such as:

```text
Can an LLM construct a minimal sufficient semantic basis at all?
Can a stronger model stop naturally instead of filling a hard cap?
Which omissions come from model capability rather than task formulation?
What quality target should a future local model reproduce?
```

This establishes an empirical upper bound before optimizing deployment cost.

---

# 3. Production-phase objective

For production, repeated full-source remote calls are structurally expensive even if downstream semantic compression is good.

Likely long-term architecture:

```text
Raw Source
    ↓
Local Semantic Sensor
    ↓
Minimal Sufficient Representation
    ↓
confidence / ambiguity / complexity gate
    ↓
selective stronger-model escalation when necessary
    ↓
Auditor / D / S / P / Delta / Attention Policy
```

Local-first production can reduce:

```text
remote input-token cost
privacy exposure
latency
network dependency
large-scale operating cost
```

Semantic compression still has independent value because it also reduces downstream Auditor/reasoning/storage/context cost.

---

# 4. Attribution rule

Do not prematurely optimize against a weak deployment model while the semantic target itself is still uncertain.

Prefer:

```text
strong-model upper-bound probe
        ↓
freeze the desired semantic behavior
        ↓
measure local-model gap
        ↓
distill / prompt / fine-tune / route
```

Memorable form:

> **先把“应该是什么”研究清楚，再研究“怎么便宜地做到”。**

This principle complements the existing RAOS discipline:

```text
Instrument -> Attribute -> Optimize
```

and the anti-overfitting rule:

```text
Do not turn one development residual into a universal mechanism.
```
