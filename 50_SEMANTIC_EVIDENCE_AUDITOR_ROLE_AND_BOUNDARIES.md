# Research Attention OS — Semantic Evidence Auditor Role and Boundaries

Status: **CANONICAL ROLE DEFINITION / ACTIVE MAINTENANCE CONTRACT**  
Date: 2026-09-07  
Purpose: preserve the stable role, boundaries, mental models, epistemic humility, and engineering invariants of the Semantic Evidence Auditor so future work does not silently expand or distort its responsibilities.

> **If future implementation choices seem to make the Auditor reread, repair, judge importance, or allocate attention, return to this document before changing the architecture.**

---

# 1. Why the Auditor exists

RAOS exists to achieve:

```text
Massive Information
      ↓
Minimal Human Attention
      ↓
Maximum Useful Cognitive Progress
```

A reading-comprehension error upstream can contaminate D/S/P/Delta and ultimately waste scarce human attention.

Therefore the Auditor exists to prevent **unsupported semantic interpretations** from entering the rest of the RAOS cognitive/attention ecology as if they were properly grounded.

Plain language:

> **Sensor 负责看清；Auditor 负责不让没证据的语义污染系统；D/S/P/Delta 负责理解意义；Attention Policy 负责花你的注意力。**

This is not decorative provenance. It is a cognitive-safety and attention-quality mechanism.

---

# 2. One-sentence definition

> **The Semantic Evidence Auditor checks whether the evidence currently attached to a semantic object is sufficient to support that object as written.**

Chinese compression:

> **当前引用的证据，够不够支持这个语义对象？**

A fuller statement of its operating philosophy is:

> **在明确、有限、可审计的证据条件下，尽可能判断当前语义对象是否被充分支持，并把判断依据留下来。**

This is the Auditor's core question and epistemic stance. Do not silently expand it.

---

# 3. Airport-security / regulator mental model

The Auditor is like **airport security**, a **regulatory checkpoint**, or a narrowly scoped **prosecutorial/evidentiary review gate**.

Airport security does not decide:

```text
where the passenger should travel
whether the trip is important
what the passenger should do after landing
whether another airport could provide missing paperwork
```

It only decides whether **what is currently presented at the checkpoint is sufficient to pass the gate**.

Likewise the Auditor does not decide whether a semantic claim is important, globally true, personally relevant, or attention-worthy.

It asks only:

```text
semantic object
      ↑
currently attached evidence packet

Is this edge sufficiently supported?
```

Top-level decision:

```text
SUFFICIENT
INSUFFICIENT
```

If insufficient, diagnosis explains why.

---

# 4. Preserve review authority; do not grant repair authority

The most important boundary can be stated as:

> **Auditor 要保留“审查权”，但不要拥有“重新理解世界、重新修案子”的权力。**

The Auditor MUST retain exactly these powers:

```text
1. inspect one semantic object;
2. inspect the evidence packet explicitly presented with that object;
3. decide whether those evidence items are sufficient;
4. if insufficient, explain the specific reason and unsupported aspect.
```

The Auditor MUST NOT absorb:

```text
full-source rereading
full-source search
searching for the correct paragraph
replacement-evidence retrieval
automatic provenance completion
rewriting the semantic object
automatic semantic repair
outside-world fact checking
importance / relevance scoring
D / S / P / Delta
DROP / AWARE / WATCH / ENGAGE
human cognitive commitment
```

Why this matters:

If the Auditor rereads the whole source and silently fixes Sensor errors, then:

```text
Sensor wrong
   ↓
Auditor secretly repairs it
   ↓
final output looks correct
```

The system can no longer attribute whether the Sensor was correct or whether the Auditor repaired it.

That collapses two modules back into one opaque LLM system.

Invariant:

```text
Review != Retrieval != Repair
```

If retrieval or repair is later justified by evidence, it should be a separate stage after an INSUFFICIENT verdict.

---

# 5. Epistemic humility: INSUFFICIENT is not FALSE

The Auditor is not an Oracle and should never be treated as one.

Core invariant:

$$
\boxed{INSUFFICIENT \neq FALSE}
$$

Operational meaning:

$$
\boxed{INSUFFICIENT = Not\ proven\ by\ the\ current\ evidence\ packet}
$$

The semantic object may be true in the full source or in the outside world. The Auditor says only:

> **The evidence currently presented to this gate is not enough to carry the object as written.**

Chinese compression:

> **INSUFFICIENT 不是在说“这句话一定错了”，而是在说“你现在拿出来的证据还撑不起这句话”。**

This is an important form of epistemic humility. RAOS should not seek an Auditor that is imagined to be infallible. The actual goal is:

> **不是追求一个永不犯错的 Auditor，而是构建一个证据边界明确、错误可审计、理由可追溯、权限受约束的监管层。**

This framing matters because real semantic interpretation is context-sensitive and even careful human institutions can make evidentiary mistakes. The engineering objective is therefore bounded, reviewable judgment—not omniscience.

---

# 6. Binary decision, descriptive diagnosis

Current canonical engineering policy:

```text
verdict:
  SUFFICIENT
  INSUFFICIENT
```

Diagnosis is separate:

```text
reason_code:
  SUPPORTED
  MISSING_SUPPORT
  AMBIGUOUS_REFERENCE
  OVERSTRONG_SCOPE
  ATTRIBUTION_UNRESOLVED
  OTHER
```

Principle:

```text
Decision = binary
Diagnosis = descriptive
```

Why no third UNCERTAIN verdict?

If ambiguity prevents the current evidence packet from sufficiently supporting the specific object, then the gate decision is still:

```text
INSUFFICIENT
```

The ambiguity remains valuable as diagnosis:

```text
INSUFFICIENT / AMBIGUOUS_REFERENCE
```

This is simpler and more faithful to the gate's purpose.

---

# 7. Evidence Packet quality bounds Audit quality

Real semantic meaning is not always recoverable from one isolated sentence.

Conceptually:

$$
\boxed{Meaning \approx f(LocalExcerpt,\ DiscourseContext,\ SourceMetadata)}
$$

Therefore:

$$
\boxed{AuditQuality \le EvidencePacketQuality}
$$

A weak or truncated packet can make a semantically correct object impossible to approve locally.

The right response is **not** to grant the Auditor more authority. Instead, upstream may explicitly prepare a better evidence packet.

Memorable boundary:

> **Auditor 不应该拥有更多权力，但可以获得更完整的卷宗。**

Invariant:

$$
\boxed{Better\ Context \neq More\ Auditor\ Authority}
$$

A better packet remains explicit, finite, and auditable. The Auditor still does not search beyond it.

---

# 8. What counts as an Evidence Packet

Conceptually, evidence is broader than a short prose excerpt:

```text
Evidence Packet
├── Primary evidence
│   directly cited source span / page / observation
├── Citation context
│   bounded context belonging to the already-cited container
│   needed to preserve discourse meaning or references
└── Trusted source metadata
    deterministic metadata such as published_at / captured_at
```

Examples may include:

```text
source text excerpt
full cited paragraph container
PDF page/span
transcript span
direct observation
trusted/deterministic source metadata
```

But every item must be **explicitly presented to the Auditor**.

The Auditor must not obtain missing evidence by searching, inference, or browsing.

This distinction matters for statements derived from metadata, such as:

```text
source publication time = unknown
```

A prose paragraph may not support that statement; trusted source metadata can.

If the packet omits the metadata evidence, the Auditor should fail the current packet rather than silently fetch or infer the missing basis.

Likewise, if an excerpt omits wording that exists inside its already-cited paragraph container, upstream may explicitly include that bounded citation context. This improves the dossier without turning the Auditor into a source-search engine.

---

# 9. Semantic plausibility, truth, and evidence sufficiency are different

The Auditor does NOT ask:

> “Is this statement probably true?”

It asks:

> **“Do these explicitly supplied evidence items support this statement?”**

A clearly attributed source claim can pass the Auditor even if the source is later proven wrong.

Therefore:

```text
Semantic plausibility != Evidence sufficiency
Statement truth       != Evidence sufficiency
World fact             != Evidence sufficiency
Traceability           != Evidence sufficiency
Source claim           != World fact
```

Example:

```text
object:
  affected system = Cursor codebase

current evidence:
  PARA 0004 -> PR volume
  PARA 0011 -> auto-merge

possible missing support elsewhere:
  PARA 0005 -> explicitly identifies Cursor code
```

The Auditor must still return INSUFFICIENT for the current packet if PARA 0005 is not explicitly included.

It is not allowed to rescue the edge by searching for PARA 0005.

---

# 10. Auditor is not an Attention Policy

Invariant:

```text
AuditVerdict != AttentionAction
```

Never infer:

```text
SUFFICIENT   -> ENGAGE
INSUFFICIENT -> DROP
```

The actual relationship is upstream quality control:

```text
Raw Source
   ↓
Semantic Sensor
   ↓
Candidate semantic object + evidence packet
   ↓
Semantic Evidence Auditor
   ↓
Audited semantic representation
   ↓
D / S / P / Delta
   ↓
Attention Policy
   ↓
DROP / AWARE / WATCH / ENGAGE
```

The Auditor helps attention allocation **indirectly but critically** by preventing unsupported interpretations from contaminating downstream judgments.

Causal risk:

```text
Bad Evidence Edge
   ↓
Bad Semantic Input
   ↓
Bad D/S/P/Delta
   ↓
Bad Attention Allocation
   ↓
Human attention wasted
```

---

# 11. Relation to Semantic Sensor

Semantic Sensor responsibility:

> **What does this source actually say?**

Auditor responsibility:

> **Do the evidence items currently presented with each extracted meaning actually support that meaning?**

The Sensor may produce a semantically plausible object but attach incomplete evidence.

The Auditor is specifically designed to detect that distinction.

Therefore:

```text
Sensor semantic quality
!=
Provenance edge quality
```

and:

```text
A semantically correct statement can still have an insufficient provenance edge.
```

---

# 12. Relation to D / S / P / Delta

The Auditor is an engineering evidence gate, not a new RAOS theoretical state variable.

It protects the inputs to:

```text
D     — Is this in my standing attention world?
S     — Does this have material consequence?
P     — Is genuine collective attention forming / present?
Delta — How would this change my cognition?
```

It must not redefine or absorb those questions.

Layering invariant:

```text
Perception
!= Evidence Audit
!= World/Cognitive Judgment
!= Attention Action
```

---

# 13. Development and evaluation discipline

Development Gold may improve through:

```text
model feedback
   ↓
human adjudication
   ↓
better Development Gold
   ↓
future regression/calibration
```

But post-run corrected Gold cannot be counted retroactively as fresh validation evidence.

Likewise, Auditor real-edge runs without Human Gold are development audits, not accuracy benchmarks.

Do not turn:

```text
12 sufficient / 5 insufficient
```

into an “Auditor accuracy” number without independent Human Gold.

---

# 14. Memorable compressions

Use these sentences when recovering context:

> **Sensor 负责看清；Auditor 负责不让没证据的语义污染系统；D/S/P/Delta 负责理解意义；Attention Policy 负责花你的注意力。**

> **Auditor 要保留审查权，但不要拥有重新理解世界、重新修案子的权力。**

> **不是判断“这个说法可能对不对”，而是判断“这些证据够不够”。**

> **在明确、有限、可审计的证据条件下，尽可能判断当前语义对象是否被充分支持，并把判断依据留下来。**

> **INSUFFICIENT 不是在说“这句话一定错了”，而是在说“你现在拿出来的证据还撑不起这句话”。**

> **Auditor 不应该拥有更多权力，但可以获得更完整的卷宗。**

> **能追溯到某处，不等于那处真的足以支持这个意思。**

> **安检负责放不放行；为什么不放行属于诊断；去哪儿、值不值得去、到了以后做什么，都不是安检的职责。**

> **不是追求一个永不犯错的 Auditor，而是构建一个证据边界明确、错误可审计、理由可追溯、权限受约束的监管层。**

---

# 15. Maintenance rule

If any future change modifies:

```text
Auditor core question
input/evidence-packet scope
binary verdict semantics
diagnosis semantics
review-vs-repair boundary
relationship to Sensor / D/S/P/Delta / Attention Policy
```

then this document and `49_RAOS_CORE_MODULE_POSITIONING.md` MUST be reviewed in the same research change.

Do not rely on conversational memory for these boundaries.
