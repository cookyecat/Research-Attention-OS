# Research Attention OS — Semantic Sensor System v1.0

Status: **CANONICAL CONCEPTUAL MODEL / ACTIVE ENGINEERING FRONTIER**  
Date: 2026-09-07  
Purpose: consolidate the motivation, terminology, semantic source skeleton, provenance discipline, compression principle, lifecycle/storage model, and evaluation method for the RAOS Semantic Sensor Front-End.

> Short definition: **The Semantic Sensor reads raw information and turns it into a compact, auditable semantic representation. It answers “what does this source actually say?” before D/S/P/Delta decide “what does it mean for attention or cognition?”**

---

# 1. Motivation — this is machine reading comprehension

The most intuitive analogy is high-school reading comprehension.

A real article is not a clean event tuple. It may contain:

```text
title / clickbait
source metadata
background
people and organizations
concrete occurrences
numbers and results
quotes
opinions
methods
claims
advertising
comments
relative time expressions
irrelevant detail
```

But downstream RAOS reasoning needs a much cleaner representation:

```text
who / what
what happened or changed
when / where
who or what is affected
what is a source claim
what is a direct observation
what is an extractor inference
what are the author's / speaker's methods, beliefs or principles
what evidence supports each semantic statement
what remains unknown
```

Therefore the Semantic Sensor problem is:

$$
\boxed{
RawSource
\rightarrow
Compact\ Auditable\ Semantic\ Representation
}
$$

Plain language:

> **给 RAOS 一篇真实文章，看它能不能像做语文阅读理解一样，把真正有用的信息要素读出来，而且每一条结论都能指出原文依据。**

This is not ordinary summarization. The output must remain suitable for downstream reasoning and audit.

---

# 2. Why this comes after Oracle-style experiments

RAOS has deliberately used staged experiments that temporarily assume an upstream layer is already correct, so a downstream layer can be tested in isolation.

## 2.1 Oracle-Delta scoring

Conceptually:

```text
Oracle gives the system the intended cognitive change Delta
                    ↓
              test Attention Policy only
```

Motivation:

> **先把“这条信息造成了什么认知变化”直接告诉系统，只考试 Attention Policy 会不会正确分配注意力。**

## 2.2 D / S / P controlled evaluation

Conceptually:

```text
Human-prepared clean semantic factors / event description
                    ↓
              test D / S / P only
```

Motivation:

> **先假设文章已经被正确理解，只考试 Standing Attention Jurisdiction、Material Consequence 和 Collective Attention Salience 的判断。**

## 2.3 Semantic Sensor evaluation

Now remove that oracle assumption:

```text
Raw article / paper / post / transcript
                    ↓
             Semantic Sensor
                    ↓
        extracted semantic evidence
                    ↓
                 D / S / P
                 Delta
```

The methodological progression is therefore:

$$
\boxed{
Downstream\ isolation
\rightarrow
Upstream\ realism
\rightarrow
End\text{-}to\text{-}end\ attribution
}
$$

Plain language:

> **以前研究“大脑怎么判断”；现在开始研究“眼睛能不能先看清楚”。**

---

# 3. Semantic Sensor — definition

A physical sensor converts an external phenomenon into a representation that a system can reason over:

```text
camera:      physical scene -> image signal
microphone:  acoustic world -> audio signal
```

RAOS Semantic Sensor:

$$
\boxed{
Article/PDF/Post/Transcript
\rightarrow
Semantic\ Signal
}
$$

The Semantic Sensor is responsible for recovering:

```text
actors / objects
concrete actions and changes
results
scope / affected systems
source and event time
claims / observations / inferences
methods / beliefs / principles
uncertainty / missingness
provenance
```

It is NOT responsible for deciding:

```text
D
S
P
Delta
AWARE / DROP / WATCH / ENGAGE
user relevance
importance
```

System boundary:

```text
Semantic Sensor
      ↓
“What does the source say?”
      ↓
D / S / P / Delta
      ↓
“What does it mean for this user/world?”
      ↓
Attention Policy
      ↓
“What should receive attention?”
```

Invariant:

$$
\boxed{
Sensing\neq State\ Estimation\neq Policy
}
$$

---

# 4. Source Semantic Skeleton

A raw source should not be treated as one opaque text blob.

RAOS uses a lightweight conceptual **Source Semantic Skeleton**.

This is not a giant ontology and does not require a global Internet knowledge graph.

Conceptually:

```text
Source
│
├── Source Metadata
│   ├── author / speaker
│   ├── publisher / platform
│   ├── published_at / captured_at
│   ├── locator / URL / file identity
│   └── media type
│
├── Event Frames [0..N]
│   ├── actors / objects
│   ├── actions / changes
│   ├── event time
│   ├── place / scope when supported
│   ├── affected systems / populations
│   └── evidence supports
│
├── Epistemic Units [0..N]
│   ├── findings
│   ├── methods
│   ├── beliefs / opinions
│   ├── principles
│   ├── explanations
│   └── evidence supports
│
└── Provenance / Uncertainty
    ├── source pointers
    ├── diagnostic excerpts
    ├── epistemic status
    └── unresolved / conflicting information
```

The skeleton is deliberately small. It captures the reading-comprehension structure needed by RAOS without pretending to model every possible concept in the world.

---

# 5. Event Frame

An **Event Frame** represents a concrete occurrence, change or result in the world.

Examples:

```text
OpenAI releases a model.
A regulator changes a rule.
A company raises a funding round.
A benchmark result increases from X to Y.
Twenty PRs are automatically merged into main and later checked.
```

Typical reading-comprehension questions apply:

```text
Who / what?
What happened?
When?
Where, if relevant and supported?
What changed?
What was the result?
Who / what was affected?
What evidence supports this?
```

Conceptual routing:

$$
\boxed{
Concrete\ occurrence/change/result
\rightarrow
EventFrame
}
$$

Plain language:

> **Event Frame 就是“这篇文章里具体发生了什么事”的故事骨架。**

Not every source contains an Event Frame.

---

# 6. Epistemic Unit

An **Epistemic Unit** is a meaningful piece of knowledge or cognition contained in the source that is not itself best represented as a concrete event.

Typical examples:

```text
method
belief
principle
interpretation
finding
argument
preference
explanation
prediction
lesson learned
```

Examples:

```text
“AI coding 最大问题不是生成，而是验证。”
“应该先给 agent 建完整 verification capability。”
“某方法比 prompt engineering 更像 engineering management。”
“某研究者认为 scaling is slowing.”
```

Conceptual routing:

$$
\boxed{
Method/belief/principle/finding
\rightarrow
EpistemicUnit
}
$$

Plain language:

> **Event 是“发生了什么”；Epistemic Unit 是“这篇文章告诉了我什么值得理解的观点、方法、发现或知识”。**

Important:

$$
\boxed{
Non\text{-}event\neq Unimportant
}
$$

A paper, essay or interview may contain few concrete events but many high-value Epistemic Units.

---

# 7. Event vs Epistemic Unit — why the distinction matters

The distinction is not literary taxonomy for its own sake. It supports different downstream reasoning paths.

Example:

```text
“NVIDIA releases a new GPU.”
        ↓
Event Frame
        ↓
D / S / P are natural questions
```

Versus:

```text
“A researcher argues that verification, not generation, is the bottleneck.”
        ↓
Epistemic Unit
        ↓
Delta / cognitive relation may be the more natural first question
```

This is not a hard prohibition: an Event may also create cognitive change, and an Epistemic Unit may also be attention-worthy. The purpose is to preserve the semantic nature of what the source contains rather than force everything into one event template.

---

# 8. Evidence-preserving Semantic Compression

The Semantic Sensor should not merely transcribe every sentence or comment.

It should compress repeated evidence into higher-level semantic units while preserving the evidence trail.

Example raw discussion:

```text
User A: Gemma is reliable.
User B: Gemma 31B is still excellent.
User C: Gemma is easy to talk to.
User D: Gemma works well for email.
```

Bad representation:

```text
4 near-duplicate semantic units
```

Better representation:

```text
Several participants describe Gemma-family models as dependable daily workhorses,
with recurring praise for usability / understanding, while noting limits for some coding tasks.

supports:
- PARA ...
- PARA ...
- PARA ...
- PARA ...
```

Therefore:

$$
\boxed{
Many\ observations
\rightarrow
Fewer\ semantic\ units
\quad\text{while keeping}\quad
Evidence\ supports
}
$$

Call this:

$$
\boxed{
Evidence\text{-}preserving\ Semantic\ Compression
}
$$

Plain language:

> **像语文课做段落归纳：把重复意思合并成更高层的总结，但不能把原文依据丢掉。**

The objective is NOT simply to minimize unit count.

A better engineering principle is:

$$
\boxed{
Minimal\ Redundancy
\quad subject\ to\quad
Semantic\ Sufficiency + Auditability
}
$$

---

# 9. Provenance — every meaning needs an audit trail

RAOS must be able to answer:

> **“你凭什么这么说？”**

For every important derived semantic statement, the system should preserve a path back to original evidence:

```text
Semantic statement
      ↓
Source identity
      ↓
PARA / PAGE / timestamp / span pointer
      ↓
short diagnostic excerpt
      ↓
original raw source when retained / retrievable
```

Core principle:

$$
\boxed{
Every\ derived\ meaning\ should\ have\ an\ audit\ trail
}
$$

And:

> **Provenance should be not only traceable, but cheaply auditable.**

Plain language:

> **不仅要知道“来自哪篇文章”，还要能快速看到“这个具体结论是根据哪几句话得出来的”。**

This supports:

```text
human review
error attribution
model debugging
future re-interpretation
cognitive safety
```

---

# 10. Epistemic status

The Semantic Sensor must distinguish how a semantic statement is supported.

Current statuses:

```text
SOURCE_CLAIM
DIRECT_OBSERVATION
EXTRACTOR_INFERENCE
```

## SOURCE_CLAIM

The source or a speaker asserts/reports it.

Example:

```text
“User X says Gemma is the best model for them.”
```

This does NOT mean Gemma is objectively the best.

## DIRECT_OBSERVATION

The supplied material contains a direct measurement or raw observation.

## EXTRACTOR_INFERENCE

The extractor derives a semantic inference from supported content. Use sparingly and preserve supports.

Invariant:

$$
\boxed{
SourceClaim\neq WorldFact
}
$$

---

# 11. Confidence — support confidence, not truth probability

Sensor confidence means:

> **How confident is the extractor that this extraction / attribution is clearly supported by the supplied source?**

It does NOT mean:

> **How likely is the source's statement to be true in the outside world?**

Thus a clearly quoted Reddit opinion can be:

```text
SOURCE_CLAIM
confidence = HIGH
```

while its external truth remains completely unverified.

---

# 12. Temporal model

RAOS must distinguish at least three times:

$$
\boxed{
t_{measure}\neq t_{source}\neq t_{event}
}
$$

Where:

```text
t_measure = when RAOS reads / measures the source
t_source  = when the article/post/source was published or captured
t_event   = when the described event actually happened
```

Example:

```text
RAOS reads source:       Sep 7
article published:       Aug 20
article says “yesterday”
resolved event date:     Aug 19
```

Never resolve source-relative expressions such as:

```text
today
yesterday
this month
last week
just now
recently
```

against `t_measure` unless the source timestamp itself is explicitly the measurement timestamp.

Rule:

> **Relative time must be resolved against source publication/capture time when available. If the source time anchor is unknown, preserve the relative expression and mark the absolute time unresolved.**

---

# 13. Source graph / skeleton without an Internet-scale database

The Semantic Sensor should construct a graph-like skeleton for information currently relevant to RAOS, but RAOS should NOT attempt to permanently store a full semantic graph for the whole Internet.

The correct analogy is an operating-system working set or multi-level cache.

## L0 — Raw Intake Buffer

Contains:

```text
raw HTML / text / PDF snapshot or reference
content hash
source metadata
normalized text
```

Retention:

```text
short / bounded
```

Purpose:

```text
initial parsing
reproducibility
sensor retry
```

## L1 — Source Semantic Skeleton Cache

Contains:

```text
source metadata
Event Frames
Epistemic Units
provenance pointers / excerpts
uncertainties
```

Retention:

```text
recent / active information working set
```

Purpose:

```text
avoid rereading the same source
support D/S/P/Delta
human audit
```

## L2 — Event / Epistemic Working Set

Across multiple sources, RAOS may deduplicate or cluster semantically equivalent items:

```text
multiple articles
     ↓
shared event / claim / topic representation
     ↓
source-specific evidence edges remain attached
```

Retention should increase when an item is:

```text
WATCHed
linked to active Kernel questions/projects
repeatedly reinforced/challenged
currently salient
needed for audit
```

Cold items can be compressed or evicted.

## L3 — Durable Cognitive / Attention State

RAOS should NOT promote every article into durable memory.

Durable state contains only things such as:

```text
human-authorized Kernel changes
standing radar clauses
active WATCH obligations
stable provenance references needed to explain committed cognition
```

This preserves the constitutional rule:

$$
\boxed{
Information\ seen\neq Cognition\ committed
}
$$

---

# 14. Storage principle — attention-proportional retention

Internet-scale ingestion does not imply Internet-scale permanent semantic storage.

RAOS exists to reduce information burden, so its own storage should follow the same principle.

Conceptually:

$$
\boxed{
Retention\ Depth
\propto
Future\ Cognitive/Attention\ Utility
}
$$

Possible eviction / compression signals:

```text
age
no active WATCH
no Kernel linkage
no future audit obligation
no repeated evidence role
low reuse probability
source can be safely re-fetched
```

Even if full raw content is evicted, an audit record may preserve:

```text
source identity / locator
content hash
published/captured time
semantic unit
support pointer
short diagnostic excerpt
```

This yields bounded storage without losing the causal lineage of important conclusions.

---

# 15. Current engineering representation

Current development interface is intentionally smaller than the full conceptual skeleton.

`SemanticExtractionBatch v0.2` supports:

```text
0..8 Event Frames
0..20 Epistemic / non-event semantic units
multi-support provenance for semantic aggregation
```

Current Event Frame includes:

```text
event summary
source metadata
evidence
substantive actors/objects
actions/changes
affected systems/populations
temporal context
uncertainties
```

Do not expand the schema simply because the conceptual model names more literary/source metadata. Add fields only when real development evidence shows downstream value.

Invariant:

> **Conceptual completeness does not require schema maximalism.**

---

# 16. Evaluation method

## E0 — Sensor Input Integrity

Question:

> Can the raw file be faithfully surfaced to the semantic model?

Examples:

```text
PDF text-layer observability
encoding
source identity
long-context boundary
```

## E1 — Semantic Reading Fidelity

Question:

> Did the Semantic Sensor correctly recover the important semantic structure?

Inspect separately:

```text
Event vs Epistemic decomposition
actor/object fidelity
action/change fidelity
scope fidelity
temporal fidelity
epistemic typing
unsupported inference
missingness honesty
provenance quality
semantic compression
```

Do not collapse all of these into one opaque score too early.

## E2 — Downstream Invariance

Compare:

```text
Human clean semantic representation -> D/S/P/Delta
```

with:

```text
LLM-extracted semantic representation -> D/S/P/Delta
```

Question:

> Does replacing the Human reader with the Semantic Sensor materially change downstream state estimates?

## E3 — End-to-End RAOS

Only after E0/E1/E2 are understood:

```text
Raw source
  ↓
Semantic Sensor
  ↓
D/S/P + Delta
  ↓
Attention Policy
  ↓
Human attention / cognition
```

Every end-to-end error should be attributed to the earliest layer that causally explains it.

---

# 17. Engineering quality metrics

Useful Sensor metrics include:

```text
FirstPassStructuralValidity
unsupported-inference rate
provenance coverage
non-empty diagnostic support coverage
temporal-anchor correctness
semantic redundancy
semantic support preservation
Event/Epistemic decomposition fidelity
```

`FirstPassStructuralValidity` matters because schema repair is not merely cosmetic: it increases latency, token cost and failure surface.

---

# 18. One-screen glossary

| Term | Plain-language meaning |
|---|---|
| Semantic Sensor | **把文章读成结构化语义的“信息传感器”。** |
| Source Semantic Skeleton | **一篇文章经过阅读理解以后留下的结构骨架。** |
| Event Frame | **文章里具体发生了什么事。** |
| Epistemic Unit | **文章告诉了我什么观点、方法、发现、原则或知识。** |
| Provenance | **这个结论到底从哪篇文章、哪一段话来的。** |
| Cheap Auditability | **不用重新通读全文，也能快速核对一个结论的依据。** |
| Evidence-preserving Semantic Compression | **把重复信息合并，但证据链不丢。** |
| $t_{measure}$ | **RAOS 什么时候读它。** |
| $t_{source}$ | **文章什么时候发布/抓取。** |
| $t_{event}$ | **事情什么时候真正发生。** |

---

# 19. Current status

```text
Semantic Sensor conceptual model        v1.0 CANONICAL
Source Semantic Skeleton                ADOPTED conceptually
Event Frame                              SUPPORTED
Epistemic Unit                           ADOPTED terminology
Evidence-preserving compression          SUPPORTED by RS09 v0.1 -> v0.2 development A/B
Provenance cheap auditability            CORE DESIGN PRINCIPLE
Event / Epistemic decomposition          SUPPORTED by RS02 / RS09
Temporal anchoring                       known residual; prompt-level correction next
Internet-scale permanent source graph    REJECTED as default architecture
Attention-proportional multilevel cache  PREFERRED architecture direction
```

Current central question:

> **Can RAOS read real information well enough that downstream D/S/P/Delta decisions behave as if a careful Human reader had prepared the semantic evidence?**

---

# 20. Semantic Sensor as External World Model construction

Phase 6 end-to-end work clarifies that the Semantic Sensor is not ordinary preprocessing. Together with the Evidence Auditor, it constructs the semantic world that downstream RAOS is allowed to reason over.

```text
Raw Source
  ↓
Semantic Sensor
  ↓
Evidence Auditor
  ↓
Audited Semantic Representation
  ↓
External World Model available to D / S / P / Delta
```

Engineering objective:

> **在不丢失关键语义、不制造额外含义的情况下，形成最有决策价值的态势表示。**
This reframes the central quality target:

```text
not maximum detail
not minimum unit count
not elegant summarization alone

but:
Compression + Hierarchical Abstraction + Evidence Fidelity + Decision Sufficiency
```

Research memory:

> **先保证“看见的世界”足够准确，再要求系统对这个世界聪明。**

> **Reasoning quality is downstream of world-model quality.**

> **Cognitive judgment cannot be more reliable than the semantic world it is given.**