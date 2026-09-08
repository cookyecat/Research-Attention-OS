# Semantic Sensor / Auditor — Generalization and Anti-Overfitting Protocol

Status: **CANONICAL DEVELOPMENT METHODOLOGY / ACTIVE MAINTENANCE CONTRACT**  
Date: 2026-09-07

> Purpose: prevent RAOS semantic-perception work from overfitting to repeatedly inspected development examples while preserving the ability to learn from mistakes.

---

# 1. Why this protocol exists

RAOS development repeatedly inspects model outputs, attribution failures, evidence packets, and Human Gold.

Even when no model parameters are trained, the research process itself can overfit:

```text
observed case
   ↓
human notices residual
   ↓
prompt / schema / architecture changes
   ↓
same case improves
```

This is a form of adaptive development pressure.

Therefore:

> **A system can overfit through researcher decisions even when the underlying LLM weights never change.**

---

# 2. Four overfitting risks

## 2.1 Sample overfitting

Tuning rules to one source's wording, discourse style, entities, or failure pattern.

Example anti-pattern:

```text
RS02 failed on Cursor codebase
-> add a special rule shaped around Cursor / PR language
```

## 2.2 Prompt overfitting

Adding clauses or examples that encode the lexical form of known failures rather than the general semantic principle.

## 2.3 Architectural overfitting

Adding a new state, module, retrieval stage, reason code, or mechanism solely because one repeatedly inspected case is awkward.

## 2.4 Evaluation overfitting

Repeatedly observing the same development example and adapting the system until that example looks good, then mistaking that improvement for generalization.

---

# 3. Core separation: Development vs Validation

## Development / Calibration sources

May be repeatedly inspected and used for:

```text
failure attribution
Human Gold improvement
prompt calibration
schema debugging
engineering decisions
regression tests
```

Their Gold may improve through:

```text
model feedback
   ↓
human adjudication
   ↓
better Development Gold
```

But they do not remain fresh evidence of generalization.

## Frozen Validation / Holdout sources

Must be protected before the system version is frozen.

They are used to answer:

> **Does the frozen mechanism work on sources that did not shape it?**

After a holdout source is inspected in a way that changes the system, it becomes consumed and is no longer fresh holdout evidence for that version.

Invariant:

```text
Development data is for learning.
Holdout data is for proving.
```

---

# 4. Source lifecycle states

Use explicit lifecycle labels:

```text
RESERVED_UNCONSUMED
DEVELOPMENT_ACTIVE
SATURATED_DEVELOPMENT
FROZEN_VALIDATION
CONSUMED_VALIDATION
```

### RESERVED_UNCONSUMED
Protected for later evaluation; do not inspect for mechanism design.

### DEVELOPMENT_ACTIVE
May be used to learn and calibrate.

### SATURATED_DEVELOPMENT
Repeatedly inspected enough that it should no longer justify new rules by itself. Retain for regression/debugging only.

### FROZEN_VALIDATION
Evaluation source selected before seeing system outputs under the frozen version.

### CONSUMED_VALIDATION
A former holdout whose results have now been inspected. If it drives system changes, it joins development evidence for future versions.

---

# 5. Stop rule for a saturated source

A development source should be declared SATURATED when it has shaped multiple rounds of mechanism or evaluation design.

Once saturated:

```text
DO use it for regression
DO use it to reproduce known bugs
DO use it for deterministic unit tests

DO NOT add new semantic rules because of it alone
DO NOT add prompt examples shaped around it alone
DO NOT add architecture because of it alone
DO NOT claim generalization from it
```

Current explicit decision:

```text
RS02 = SATURATED_DEVELOPMENT / CALIBRATION SOURCE
```

---

# 6. What should justify a new mechanism change

Prefer this evidence hierarchy:

```text
1. repeated pattern across heterogeneous sources
2. Human-adjudicated failure with the same causal structure across sources
3. controlled A/B showing the mechanism addresses that structure
4. regression proving old capabilities are preserved
```

One unusual source or one model fluctuation is not enough.

A useful working rule:

> **Do not convert a local residual into a general mechanism until the residual repeats across materially different sources.**

---

# 7. Heterogeneity matters

Generalization should be tested across different information forms, not merely more examples of one style.

For the current Semantic Sensor / Auditor frontier, useful development broadening includes:

```text
news / release
technical tutorial / methods article
long interview / mixed claims and interpretation
healthy PDF / paper-like source
```

Different genres stress different semantic functions:

```text
actors and events
deictic time
methods and beliefs
cross-paragraph discourse
metadata dependence
attribution
compression
provenance granularity
```

---

# 8. Freeze before broadening

Before a broadening run, record and freeze:

```text
Sensor version
Sensor prompt SHA
Auditor version
Auditor prompt SHA
Evidence Packet version/policy
model settings
source list
predeclared metrics / inspection targets
```

Do not change these between sources inside the same broadening round merely because an early source looks awkward.

If a serious implementation bug makes the round invalid, stop, repair the instrumentation, version the change, and restart or clearly separate the measurements.

---

# 9. Predeclare what will be measured

Before opening results, define targets such as:

```text
Sensor semantic omission
Sensor semantic overreach
Event/Epistemic decomposition
provenance traceability
provenance sufficiency
metadata dependence
context dependence
Auditor false accept
Auditor false reject
Auditor stability
first-pass structural validity
```

Do not invent a new success criterion only after seeing the output.

---

# 10. Human Gold discipline

Human Gold is not infallible.

Correct process:

```text
predeclared Gold
   ↓
model / evaluator disagreement
   ↓
human adjudication
   ↓
Gold may be corrected
```

But preserve provenance:

```text
PREDECLARED
POST_RUN_ADJUDICATED
```

Never rewrite history by presenting post-run Gold as if it had been frozen beforehand.

---

# 11. Auditor-specific anti-overfitting rules

Do not tune the Auditor merely to increase pass rate.

The Auditor's role remains:

> **In a bounded, explicit, auditable evidence packet, decide whether the semantic object is sufficiently supported and preserve the rationale.**

Avoid these anti-patterns:

```text
known false reject -> weaken gate globally
known false accept -> make gate globally stricter
one ambiguous sentence -> add a new verdict state
one missing paragraph -> add automatic full-source retrieval
```

First determine whether the pattern repeats across sources.

---

# 12. Evidence Packet-specific anti-overfitting rules

Do not optimize for maximum evidence volume or maximum SUFFICIENT rate.

The target is:

> **minimal sufficient auditable dossier**

Potential packet components must be justified by semantic dependency, not universally injected because one case benefited.

Observed RS02 development evidence suggests:

```text
metadata can help metadata-dependent semantics
irrelevant metadata can destabilize judgment
same-container context does not always resolve semantic overreach
```

These observations motivate broader testing; they are not yet universal production rules.

---

# 13. Broadening before redesign

Current methodological decision:

```text
STOP tuning on RS02
FREEZE current mechanisms
BROADEN across heterogeneous development sources
ADJUDICATE repeated causal patterns
ONLY THEN decide whether v0.2.3 / v0.1.2 or new packet policy is justified
```

This is the semantic-system analogue of avoiding train-set overfitting.

---

# 14. Current source policy

Existing development corpus contains already-consumed development sources and reserved sources.

For the next broadening round, prefer heterogeneous already-development-eligible sources such as:

```text
RS11 — news/release-like article
RS05 — technical tutorial/method
RS06 — long interview / mixed epistemic content
RS04 — healthy PDF
```

Keep reserved sources such as RS13 / RS14 unconsumed for later holdout use unless the validation plan is explicitly changed beforehand.

---

# 15. Memorable compressions

> **开发集用来学，留出集用来证明。**

> **模型参数不变，不代表研究过程不会过拟合。**

> **反复看同一个样本并据此改系统，本身就是一种训练。**

> **不要把一个局部 residual 直接升级成一个全局机制。**

> **先看问题是否跨来源重复，再决定是否值得增加复杂度。**

> **RS02 现在是回归样本，不再是新规则生成器。**

---

# 16. Maintenance rule

If future work changes:

```text
source lifecycle policy
holdout policy
Gold adjudication policy
mechanism-change evidence threshold
broadening protocol
```

update this document in the same research change.

Do not rely on conversational memory for anti-overfitting discipline.

---

# 17. Phase 7A concrete overfitting case

Phase 7A produced a direct example of researcher-level overfitting.

```text
v0.2.4 evidence-complete cohesion
was motivated by RS15
↓
RS15 causal world-model loss improved
↓
RS05 technical tutorial regressed from a stable CHALLENGE path to NONE
```

Therefore:

> **A mechanism does not graduate because it repairs the case that created it.**

A candidate must survive materially different source styles and downstream causal checks before it becomes a working baseline.

v0.2.6 was selected only after targeted RS15/RS05 decision-fidelity probes plus RS11/RS12 cross-source regression.
