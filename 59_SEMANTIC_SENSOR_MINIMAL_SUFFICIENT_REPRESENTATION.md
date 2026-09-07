# Semantic Sensor — Minimal Sufficient Representation

Status: **ACTIVE RESEARCH / PREREGISTERED DEVELOPMENT STUDY**  
Date: 2026-09-08

> Purpose: reduce Semantic Sensor representation cost without losing the independent source-grounded semantics needed by downstream RAOS reasoning and evidence audit.

---

# 1. Why this study exists

Cross-source text broadening exposed a representation-budget problem before a semantic-quality problem could be measured cleanly.

Observed under frozen Semantic Sensor v0.2.2 / DeepSeek v4 Flash:

```text
RS11  completion_tokens = 7605   finish_reason = stop
RS05  completion_tokens = 8192   finish_reason = length
RS06  completion_tokens = 7097   finish_reason = stop
RS12  completion_tokens = 8192   finish_reason = length
```

Two of four heterogeneous text sources hit the provider completion ceiling exactly; the two successful sources also ran close to it.

Therefore the open problem is no longer merely:

> “Can we increase max_tokens?”

It is:

> **What is the smallest semantic representation that preserves the source distinctions RAOS actually needs?**

This problem is upstream of the Auditor and has higher current priority.

---

# 2. Core objective

Let:

$$
R = Sensor(I)
$$

where $I$ is the raw information source and $R$ is the Semantic Sensor representation.

The target is not maximal detail. The target is:

$$
\boxed{
Minimal\ Redundancy
\quad subject\ to\quad
Semantic\ Sufficiency + Auditability + Bounded\ Output
}
$$

This extends the existing Evidence-Preserving Semantic Compression principle.

A representation is not good merely because it is short.

A representation is not good merely because it is detailed.

It is good when it is **small enough to operate cheaply while still preserving the independent semantics needed to understand what the source says and audit why the Sensor says it.**

---

# 3. What MUST be preserved

The Sensor should preserve distinct source-grounded information such as:

```text
concrete events / changes / results
independent claims or positions
methods and mechanisms
causal relations
important quantitative results or comparisons
conditions / constraints / caveats
counterexamples or conflicting claims
actor / speaker attribution
temporal status
uncertainty
minimal provenance sufficient for audit
```

These are semantic distinctions, not user-importance labels.

The Sensor must still NOT compute:

```text
D
S
P
Delta
Attention Action
user relevance
importance
```

Compression must not become hidden downstream policy.

---

# 4. What should normally be merged

The Sensor should NOT create a separate semantic unit merely because the source contains another sentence or example.

Prefer merging when several passages express the same underlying semantic predicate.

Typical merge candidates:

```text
multiple examples supporting one claim
multiple benchmark numbers supporting one comparison
multiple implementation variants illustrating one mechanism
repeated restatements of the same conclusion
background details already subsumed by a stronger semantic unit
several nearby details with identical attribution, temporal role, and causal meaning
```

A support example can remain in provenance without becoming its own semantic unit.

---

# 5. Semantic Independence Test

Create a separate semantic unit only when removing it would lose a distinct proposition that cannot be reconstructed from the remaining units without changing one of:

```text
truth-conditional meaning
actor / speaker attribution
causal relation
method / mechanism
quantitative conclusion
temporal status
scope / condition
uncertainty
```

Memorable form:

> **If deleting the unit does not remove an independent meaning, merge it.**

This is the primary semantic compression rule.

The numeric unit budget below is only an engineering guardrail.

---

# 6. Minimal sufficient provenance

Auditability does not require copying large portions of the source into JSON.

For each semantic unit:

```text
use the fewest supports necessary
quote the smallest excerpt that actually proves the semantic claim
add another support only when the claim genuinely depends on another passage
```

Therefore:

$$
\boxed{Evidence\ Preservation \neq Source\ Duplication}
$$

The evidence excerpt is an audit pointer with enough local substance to verify the claim. It is not a backup copy of the article.

---

# 7. Candidate v0.2.3 compression policy

The first controlled candidate keeps the existing SemanticExtractionBatchV0_2 structure so the experiment isolates **semantic compression**, not serialization tricks.

No row arrays, abbreviated JSON keys, binary encoding, or external evidence registry are introduced yet.

Candidate policy:

```text
event_frames:
  unchanged schema limit <= 8
  create only for concrete events / results / state changes

non_event_units:
  preferred range = 6..10 when source semantics permit
  experimental hard policy cap = 12

supports per non-event unit:
  normally 1..2
  experimental hard policy cap = 4

statement:
  one compact semantic statement / cluster

support_excerpt:
  smallest diagnostic source excerpt sufficient for audit

note:
  empty unless it carries necessary uncertainty/qualification not represented elsewhere
```

The cap of 12 is not a claim that every source has twelve meaningful ideas. It is a guardrail against returning to sentence-level transcription.

---

# 8. Why not solve this with max_tokens first

Raising the provider completion ceiling could hide the current failure but would not solve:

```text
latency
cost
storage
Auditor input cost
future context pressure
online system scaling
```

Therefore:

> **First reduce semantic representation cost. Increase transport capacity only if a semantically sufficient representation still genuinely needs it.**

---

# 9. Why not use syntactic compression first

We could reduce tokens by changing:

```text
JSON objects -> fixed rows
long field names -> abbreviated keys
inline provenance -> shared evidence table
```

Those techniques may become useful later.

But they would mix two questions:

```text
How much meaning should the Sensor keep?
How efficiently should that meaning be serialized?
```

Round v0.2.3 studies the first question only.

If semantic compression alone is sufficient, the simpler architecture wins.

---

# 10. Development study sources

Use the already-consumed text broadening sources:

```text
RS11 — news / release-like
RS05 — technical tutorial / method
RS06 — long interview / mixed epistemic content
RS12 — industry / technical interview
```

These are development data, not fresh validation.

RS02 remains SATURATED_DEVELOPMENT and is not a rule generator.

RS13 / RS14 remain RESERVED_UNCONSUMED.

---

# 11. Frozen comparison conditions

Baseline identity:

```text
Semantic Sensor v0.2.2
prompt SHA256 = 52bae84a3d06bbaa597cdbf43460c8945dcd13cb53616390c05a6a40995dfbe9
thinking = disabled
temperature = 0.1
model = deepseek-v4-flash
```

Candidate:

```text
Semantic Sensor v0.2.3
same semantic schema family
same temporal policy
same evidence-sufficiency discipline
same source list
same model settings
changed only: semantic compression policy / output budget discipline
```

Do not change the candidate between the four sources.

---

# 12. Predeclared measurements

## Transport / representation

```text
scorable completion
first-pass structural validity
finish_reason where diagnostic data are available
completion tokens
semantic unit count
support count
statement characters
support-excerpt characters
```

Provider hard ceiling observed:

```text
8192 completion tokens
```

Preferred engineering safe region for this study:

```text
approximately <= 6000 completion tokens
```

This is an engineering headroom target, not a semantic law.

## Semantic sufficiency

Human inspection uses the same dimensions across sources:

```text
missing independent event/result
missing independent claim/method/mechanism
missing material quantitative result
lost condition/caveat/counterexample
actor attribution error
time/scope error
semantic overreach
Event/Epistemic decomposition
provenance traceability
provenance sufficiency
```

A shorter representation that materially worsens these is a failed compression.

---

# 13. Acceptance logic

A candidate is promising only if BOTH are true:

```text
A. representation cost falls materially / truncation disappears
B. Human Semantic Sufficiency remains acceptable across heterogeneous sources
```

Do not optimize for token count alone.

Do not optimize for unit count alone.

Do not treat Auditor pass rate as semantic coverage.

---

# 14. Anti-overfitting rule

The same v0.2.3 policy must run across all four development sources unchanged.

Do not modify the prompt after seeing RS11 before running RS05/RS06/RS12.

One awkward source is not enough to add another special rule.

Any further mechanism change should be based on a repeated causal pattern across sources.

Canonical anti-overfitting protocol:

```text
56_SENSOR_AUDITOR_GENERALIZATION_AND_ANTI_OVERFITTING_PROTOCOL.md
```

---

# 15. Relationship to Auditor

Current priority order:

```text
Semantic Sensor minimal sufficient representation
        ↓
stable bounded semantic output
        ↓
provenance quality
        ↓
Semantic Evidence Auditor
        ↓
downstream D / S / P / Delta / Attention Policy
```

Auditor strictness is not causal for the current 8192-token Sensor failure.

Memorable compression:

> **First make the Sensor say less without knowing less. Then ask the Auditor whether what remains is supported.**

---

# 16. Current frontier

```text
PDF parsing                              DEFERRED
Provider 8192 completion ceiling         ATTRIBUTED
Sensor representation-budget problem     REPRODUCED / OPEN
Minimal sufficient representation        ACTIVE RESEARCH
Auditor strictness                       NOT CURRENT BOTTLENECK
Fresh validation                         NONE
```

---

# 17. Memorable formulations

> **少而全，不是单纯少。**

> **If deleting the unit does not remove an independent meaning, merge it.**

> **Evidence preservation is not source duplication.**

> **First make the Sensor say less without knowing less.**

> **The Sensor should compress semantics, not merely compress JSON syntax.**
