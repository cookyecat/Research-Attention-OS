# Research Attention OS — Dual World Model and Perception Discipline

Status: **CANONICAL ARCHITECTURAL INSIGHT / ACTIVE ENGINEERING PRINCIPLE**
Date: 2026-09-08
Related: `35_RAOS_MATHEMATICAL_LANGUAGE_REGISTRY.md`, `41_RAOS_SEMANTIC_SENSOR_SYSTEM_V1.0.md`, `49_RAOS_CORE_MODULE_POSITIONING.md`

> RAOS does not reason directly over reality or directly over the user's mind. It reasons over representations of both.

The system therefore has two distinct perception problems:

```text
External World
      ↓
External World Model

User Cognitive World
      ↓
Brain / Cognitive World Model
```

These two models meet inside cognitive judgment and attention allocation.
---

## 1. External World Model

The Semantic Sensor is not merely preprocessing. It constructs the semantic world that downstream RAOS is able to see.

```text
Raw Source
   ↓
Semantic Sensor
   ↓
Semantic Evidence Auditor
   ↓
Audited Semantic Representation
   ↓
External World Model available to D / S / P / Delta
```

Its job is to form:

> **在不丢失关键语义、不制造额外含义的情况下，形成最有决策价值的态势表示。**

This is closer to intelligence fusion than ordinary summarization.
The hard tradeoff is therefore not `detail vs brevity` alone. It is:

```text
Compression
+
Hierarchical Abstraction
+
Evidence Fidelity
+
Decision Sufficiency
```

A good semantic world model is neither a transcript of every sentence nor an elegant summary that outruns its evidence.

> **先保证“看见的世界”足够准确，再要求系统对这个世界聪明。**

> **Reasoning quality is downstream of world-model quality.**

> **Cognitive judgment cannot be more reliable than the semantic world it is given.**
---

## 2. Brain / Cognitive World Model

RAOS also needs a model of the user's current cognitive world: what the user currently knows, believes, questions, models, decides, is trying to achieve, and is actively monitoring.

The protected Cognitive Kernel `K_t` is the authoritative committed core of this world model.

But the two concepts are not identical:

```text
Cognitive Kernel K_t
= human-authorized durable cognitive state

Brain / Cognitive World Model
= RAOS's operational representation of the user's current cognitive world,
  anchored by K_t and other legitimate current-state context
```

Invariant:

```text
Brain World Model != permission to rewrite K_t
Estimate of cognition != committed cognition
```
A future Brain World Model may include, subject to separate validation:

```text
K_t                       committed cognition
Standing Radar clauses    durable monitored worlds
Runtime context            current task/capacity/deadline
Active WATCH obligations   delegated future attention
Recent human feedback      explicit corrections/preferences
```

These are not automatically one database object and should not be collapsed prematurely.

The architectural point is simply that Delta reasons over two represented worlds:

```text
What the external world appears to say
            ×
What the user's cognitive world currently contains
            ↓
          Delta
```

This document introduces no new canonical mathematical variable. Formalization should wait until repeated engineering evidence proves a stable abstraction is needed.
---

## 3. Intelligence-system analogy

RAOS increasingly resembles an intelligence / command pipeline:

```text
Front-line sensing / reports
        ↓
Semantic Sensor
        ↓
Evidence review / intelligence validation
        ↓
Semantic Evidence Auditor
        ↓
Situation assessment against current doctrine/state
        ↓
D / S / P / Delta
        ↓
Command-resource allocation
        ↓
Attention Policy
```

The analogy is structural, not domain-specific: RAOS currently applies it to information objects such as an article, paper, post, interview, or transcript.
A downstream decision may be internally rational and still externally wrong if the represented world is wrong:

```text
Bad Input
   ↓
Coherent Reasoning
   ↓
Rational but Wrong Decision
```

Therefore an end-to-end failure should be attributed from the earliest causal layer, not automatically blamed on the final policy.

---

## 4. Perception-before-decision discipline

Preserve these two paired rules:

> **不能因为传感器差，就修改物理定律。**

> **在质疑决策之前，先检查系统看到的是不是同一个世界。**

English companion:

> **Before blaming the decision layer, inspect the world it was shown.**
Operational debugging order:

```text
1. Raw source / source integrity
2. Semantic Sensor representation
3. Auditor admission / rejection
4. External World Model available downstream
5. Brain / Cognitive World Model state
6. Locate / Delta judgment
7. D / S / P estimates
8. Attention Policy allocation
9. Human feedback / authorization
```

Do not skip directly from a surprising final action to changing policy thresholds.

Related system lesson:

> **Local correctness does not imply system correctness.**

A locally correct Auditor decision can still expose an interface bug if its output representation removes context required by downstream judgment.
---

## 5. Research-memory rule

RAOS should preserve concise formulations when they compress a hard-won system insight without changing its meaning.

Reason:

```text
Memorable language
→ faster recovery of the correct mental model
→ less repeated rediscovery
→ lower conceptual drift across sessions
```

These phrases are not decorative slogans. They are compressed research memory and should remain subordinate to the formal definitions and experimental evidence they summarize.

Canonical memory set from this stage:

> **先保证“看见的世界”足够准确，再要求系统对这个世界聪明。**

> **在不丢失关键语义、不制造额外含义的情况下，形成最有决策价值的态势表示。**

> **Reasoning quality is downstream of world-model quality.**

> **Cognitive judgment cannot be more reliable than the semantic world it is given.**

> **不能因为传感器差，就修改物理定律。**

> **在质疑决策之前，先检查系统看到的是不是同一个世界。**

> **Before blaming the decision layer, inspect the world it was shown.**

---

## 6. Current architectural interpretation

```text
External World Model quality      current primary bottleneck candidate
Brain World Model                 conceptually required; engineering frontier later
Delta semantics                   frozen / performing well under clean input
Attention Policy                  downstream allocator, not perception repair
```

The immediate implication is not to redesign Delta. It is to improve and measure the fidelity of the worlds Delta is shown.## Observed Brain World Model authority failure — Phase 6C

Phase 6C produced a concrete example of why Brain World Model authority must be explicit.

The cognitive-impact LLM inferred `threatens_active_work=true` without receiving trusted information about the user's actual current work. The Scheduler then correctly converted that input into PREEMPT urgency.

Causal chain:

```text
Untrusted model inference about user state
→ authoritative-looking Brain/Runtime state
→ correct Attention Policy
→ wrong PREEMPT behavior
```

The fix is architectural, not a Scheduler-policy change:

> **A model inference about the user is not automatically an authoritative user state.**

Only trusted upstream Brain/Runtime sensing may assert runtime facts such as `threatens_active_work`.