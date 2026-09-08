# Research Attention OS — Core Module Positioning

Status: **CANONICAL SYSTEM MAP / ACTIVE MAINTENANCE CONTRACT**  
Date: 2026-09-07  
Purpose: provide one stable architectural map for the core RAOS modules so that module responsibilities do not drift as the system evolves.

> This file answers one question: **Which RAOS module is responsible for what?**

RAOS exists to achieve:

```text
Massive Information
      ↓
Minimal Human Attention
      ↓
Maximum Useful Cognitive Progress
```

Directional objective:

```text
CROA = Useful Cognitive Change / Human Attention Cost
```

The modules below are not independent products. They are stages in one attention-allocation pipeline.

---

# 1. One-screen system map

```text
Raw Source / Information
        ↓
Semantic Sensor
“这篇东西到底说了什么？”
        ↓
Candidate Semantic Skeleton
        ↓
Semantic Evidence Auditor
“你说的这些意思，当前引用的证据够不够？”
        ↓
Audited Semantic Representation
        ↓
+----------------------+----------------------+
|                                             |
v                                             v
D / S / P                                  Delta
Attention-world path                    Cognitive path
|                                             |
+----------------------+----------------------+
                       ↓
                Attention Policy
      “我现在应该花多少注意力？”
                       ↓
          DROP / AWARE / WATCH / ENGAGE
                       ↓
                 Human Feedback
                       ↓
          human-authorized cognition only
                       ↓
                  Cognitive Kernel
```

Core layering invariant:

```text
Perception != Evidence Audit != World/Cognitive Judgment != Attention Action
```

---

# 2. Semantic Sensor

## Position

**Perception / reading-comprehension layer.**

## One-sentence definition

> **Semantic Sensor reads a raw source and turns it into a compact, structured, auditable semantic representation.**

Plain language:

> **眼睛：这篇文章、PDF、帖子、访谈到底说了什么？**

## Input

```text
Raw article / PDF / post / transcript / source metadata
```

## Output

```text
Source Semantic Skeleton
- Event Frames
- Epistemic Units
- actors / objects
- actions / changes
- affected systems / populations
- temporal context
- provenance pointers / excerpts
- uncertainty
```

## It MUST do

```text
read
extract
structure
compress repeated meaning
preserve provenance
preserve source-vs-inference distinction
preserve unknowns
```

## It MUST NOT do

```text
judge D / S / P
judge Delta
allocate DROP / AWARE / WATCH / ENGAGE
silently invent missing facts
silently commit cognition
```

## Core question

```text
What does this source actually say?
```

---

# 3. Semantic Evidence Auditor

## Position

**Evidence-quality gate / semantic regulator.**

## One-sentence definition

> **The Auditor verifies whether the evidence already cited by a semantic object is sufficient to support that object.**

Plain language:

> **安检 / 监管：你说这个意思可以，但你手里的这几条证据，真的够不够？**

## Input

```text
one semantic object
+
its already-cited evidence excerpts
```

## Output

```text
verdict:
  SUFFICIENT
  INSUFFICIENT

reason_code:
  SUPPORTED
  MISSING_SUPPORT
  AMBIGUOUS_REFERENCE
  OVERSTRONG_SCOPE
  ATTRIBUTION_UNRESOLVED
  OTHER

rationale
unsupported_aspect
```

## Why it is like airport security

Airport security does not decide where you are travelling, whether the trip is important, or what you should do after landing. It only decides whether what is currently presented is safe/acceptable to pass through the gate.

Likewise the Auditor:

```text
does not decide whether the semantic claim is important

does not decide whether the claim is globally true

does not decide D / S / P / Delta

does not decide AWARE / WATCH / ENGAGE

it only checks:
“Does the cited evidence sufficiently support the semantic object as written?”
```

## It MUST keep

```text
local evidence sufficiency check
binary pass/fail decision
explicit diagnosis of why an edge fails
short source-grounded rationale
strict separation from downstream judgment
```

## It MUST NOT absorb

```text
full-source search
replacement-evidence retrieval
automatic semantic repair
outside-world fact checking
importance / relevance scoring
D / S / P / Delta
Attention Policy
```

If later RAOS needs evidence retrieval or repair, those should be separate stages after an INSUFFICIENT result.

## Core question

```text
Do the currently cited excerpts sufficiently support this semantic object?
```

## Core invariant

```text
AuditVerdict != AttentionAction
```

and:

```text
Traceable Provenance != Sufficient Provenance
```

---

# 4. D — Standing Attention Jurisdiction

## Position

**Standing user-world membership judgment.**

## One-sentence definition

> **D asks whether the event belongs to a world the user wants RAOS to monitor on a standing basis.**

Plain language:

> **这是不是“我的世界”——是不是我长期希望 RAOS 替我盯着的事？**

Formal:

```text
D(E,u) = 1[E in J_u]
```

## Input

```text
audited event semantics
+
user standing attention jurisdiction / radar clauses
```

## Output

```text
D or D-hat
```

## It MUST NOT mean

```text
importance
material consequence
public attention
current urgency
```

## Core question

```text
Is this inside my standing attention jurisdiction?
```

---

# 5. S — Material Consequence

## Position

**Objective consequence judgment.**

## One-sentence definition

> **S asks whether the event materially disturbs a consequential shared/public system.**

Plain language:

> **这件事本身有没有真后果？**

## Input

```text
audited event semantics
```

## Output

```text
S or S-hat
```

## It MUST NOT mean

```text
user interest
media volume
actor fame
technical novelty alone
large private/local change alone
public attention
```

## Core question

```text
Did something consequential in the shared world materially change?
```

---

# 6. P — Collective Attention Salience

## Position

**Collective-attention state estimation.**

## One-sentence definition

> **P asks whether genuine collective attention has formed or is clearly forming within the event's objective attention constituency.**

Plain language:

> **在真正相关的人群里，这事现在是不是大家真的在看？**

## Input

```text
audited event semantics
+
objective constituency
+
current / recent attention evidence
```

## Output

```text
P or P-hat
```

## It MUST NOT mean

```text
user interest
material consequence
raw media count alone
importance
```

## Core question

```text
Has genuine collective attention formed in the right reference group?
```

---

# 7. Delta — Potential Cognitive Change

## Position

**Cognitive-impact judgment.**

## One-sentence definition

> **Delta predicts how correctly absorbed information would change the user's current cognition.**

Plain language:

> **如果我真正理解这条信息，我的认知会不会变、怎么变？**

Canonical states:

```text
NONE / empty
REINFORCE(k)
CHALLENGE(k)
OPEN_NEW
```

## Input

```text
audited epistemic/event semantics
+
current Cognitive Kernel K_t
+
location candidates L_t
```

## Output

```text
Delta_t
```

## It MUST NOT mean

```text
attention action itself
permanent cognitive mutation
importance score
```

## Core question

```text
What would this information change in my current understanding?
```

---

# 8. Attention Policy

## Position

**Scarce-human-attention allocation layer.**

## One-sentence definition

> **Attention Policy decides how much human attention the information should receive now.**

Plain language:

> **我现在应该忽略、知道一下、继续盯着，还是认真投入？**

Current action vocabulary:

```text
DROP
AWARE
WATCH
ENGAGE
```

For the frozen no-Delta AWARE gate:

```text
AWARE iff S and (D or P)
```

## Input

```text
Delta
D / S / P
runtime context
current attention obligations
```

## Output

```text
Attention Action A_t
```

## It MUST NOT do

```text
rewrite evidence
reinterpret raw source
silently mutate protected cognition
```

## Core question

```text
How much scarce human attention should be allocated now?
```

---

# 9. Cognitive Kernel and Human Feedback

## Cognitive Kernel K_t

Position:

```text
protected, reviewable user cognition state
```

Plain language:

> **我现在已经知道、相信、在问、在做什么。**

The Kernel is not a dumping ground for every source RAOS sees.

Invariant:

```text
Information seen != Cognition committed
```

## Human Feedback H_t

Position:

```text
final human correction / authorization boundary
```

Plain language:

> **系统可以建议认知变化，但只有人确认过的变化才能真正写进下一版“我”。**

Invariant:

```text
AI may propose cognition change;
AI may not silently commit protected cognition.
```

---

# 10. Why Auditor is not a second Semantic Sensor

This distinction is important.

Bad architecture:

```text
Sensor
  ↓
Auditor reads full source again
  ↓
Auditor searches, repairs, rewrites, judges truth
  ↓
second giant black-box reader
```

That duplicates responsibility and makes attribution harder.

Preferred architecture:

```text
Sensor
  ↓
semantic object + cited evidence
  ↓
Auditor checks only that local edge
  ↓
PASS or FAIL + diagnosis
```

If FAIL later requires repair:

```text
INSUFFICIENT
   ↓
separate Evidence Retrieval / Repair stage   [future, only if measured need justifies it]
```

Occam principle:

> **Do not add a new mechanism until a measured residual proves that the current simpler mechanism is insufficient.**

---

# 11. Module boundary table

| Module | Human analogy | One-line job | Primary input | Primary output | Must not decide |
|---|---|---|---|---|---|
| Semantic Sensor | eyes / reading comprehension | read raw information into structured semantics | raw source | semantic skeleton | D/S/P/Delta/attention |
| Evidence Auditor | airport security / regulator | verify cited evidence is sufficient for each semantic object | semantic object + cited evidence | sufficient / insufficient + diagnosis | truth, importance, attention |
| D | standing radar | decide whether this belongs to my monitored world | audited semantics + user jurisdiction | D | S/P/importance |
| S | consequence judge | decide whether there is material shared-world consequence | audited semantics | S | user interest / public attention |
| P | collective-attention sensor | decide whether genuine collective attention has formed in the right constituency | semantics + attention evidence | P | user interest / consequence |
| Delta | cognitive-change judge | predict how this changes my cognition | audited semantics + Kernel | Delta | attention action / commit |
| Attention Policy | attention budgeter | allocate scarce human attention | Delta + D/S/P + runtime context | DROP/AWARE/WATCH/ENGAGE | raw-source interpretation |
| Human Feedback / Kernel | constitutional boundary | authorize what becomes durable cognition | proposed changes + human judgment | K_{t+1} | autonomous hidden commitment |

---

# 12. One-line glossary

```text
Semantic Sensor
= 这篇东西到底说了什么？

Semantic Evidence Auditor
= 你说这个意思，当前引用的证据真的够吗？

D
= 这是不是我的世界？

S
= 这件事有没有真后果？

P
= 在真正相关的人群里，大家现在真的在看吗？

Delta
= 这会怎么改变我的认知？

Attention Policy
= 我现在应该花多少注意力？

Cognitive Kernel
= 哪些认知已经被我正式接受并保留下来？
```

---

# 13. Maintenance rule

Any future change to a core module's:

```text
role
input/output
one-sentence human contract
forbidden responsibility
position in the pipeline
```

MUST update this document in the same research change.

The Mathematical Language Registry (`35_RAOS_MATHEMATICAL_LANGUAGE_REGISTRY.md`) remains the canonical symbol/variable dictionary. This document is the canonical **module-responsibility dictionary**.

Core lesson:

> **RAOS stays understandable only if every module has one clear job, one clear boundary, and one clear place in the attention-allocation chain.**

---

# 14. Phase 6 interface clarification — audited context envelope

Phase 6A end-to-end measurement exposed an important interface rule between the Auditor and downstream judges.

Do not collapse an approved semantic object to prose alone after audit. The downstream representation should preserve the evidence context already admitted with that object:

```text
Audited Semantic Representation
=
admitted semantic objects
+
their evidence excerpts from SUFFICIENT Auditor edges
```

This does **not** authorize retrieval, repair, or resurrection of rejected semantic objects.

Invariant:

```text
Context preservation != Semantic repair
Rejected object != restored object
```

Reason: removing already-admitted evidence context can erase domain, causal, quantitative, or attribution information needed by D/S/Delta and can change final Attention Policy output even though each local Auditor verdict is individually reasonable.

The Auditor still has one job: evidence sufficiency. The context envelope is an interface property of its output, not a new Auditor responsibility or theoretical variable.
