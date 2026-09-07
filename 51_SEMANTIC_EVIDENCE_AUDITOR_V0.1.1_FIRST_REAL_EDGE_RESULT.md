# Semantic Evidence Auditor v0.1.1 — First Real Sensor-Edge Result

Status: **DEVELOPMENT RESULT / LOCAL VERIFIER SUPPORTED / PROVENANCE RESIDUALS ATTRIBUTED**  
Date: 2026-09-07

> This is a development audit of actual Semantic Sensor v0.2.2 provenance edges. There is no Human Gold attached to the full 17-edge set, so this document must not be interpreted as an Auditor accuracy benchmark.

---

# 1. Input and measurement identity

Input Sensor artifact:

```text
eval/live/results/semantic_evidence_dev_v0_2_2/
semantic_evidence_dev_v0_2_2_20260907T103010Z.json
```

Auditor output artifact:

```text
eval/live/results/semantic_evidence_auditor_real_edges_v0_1_1/
semantic_evidence_auditor_real_edges_v0_1_1_20260907T125803Z.json
```

Measurement HEAD:

```text
78c2848c4e0e99b2354f0ff74c9424fe6710001b
```

Auditor:

```text
semantic-evidence-auditor-v0.1.1
binary sufficiency
thinking disabled
one semantic object vs currently attached evidence only
```

---

# 2. Topline

Observed:

```text
n_edges              17
n_scorable           17
n_first_pass_valid   17
n_sufficient         12
n_insufficient        5

reason_counts:
  SUPPORTED               12
  MISSING_SUPPORT           4
  ATTRIBUTION_UNRESOLVED    1
```

This is NOT:

```text
12/17 accuracy
```

because the real-edge set has no independent Human Gold.

It is an audit profile of actual Sensor provenance.

---

# 3. Primary success — the known bad edge was caught

Known Sensor v0.2.2 residual:

```text
semantic object:
  affected system = Cursor codebase

currently attached supports:
  PARA 0004 -> joined Cursor / PR volume / codebase context
  PARA 0011 -> auto-merge into main
```

Auditor result:

```text
INSUFFICIENT
MISSING_SUPPORT
```

The source contains stronger explicit support elsewhere (`PARA 0005` identifies the code as Cursor code), but the Auditor did not search for or add it.

This is exactly the intended behavior:

```text
bad current provenance edge
        ↓
blocked
```

without turning the Auditor into a retrieval/repair system.

---

# 4. Obvious good edges were not broadly overblocked

Several locally well-supported semantic objects passed directly, including:

```text
PR volume:
  1000 PRs previous month / ~800 first 12 days
  <- PARA 0004
  -> SUFFICIENT

auto-merge behavior:
  20 PRs automatically entered main
  <- PARA 0011
  -> SUFFICIENT

verification bottleneck:
  AI coding bottleneck is verification rather than generation
  <- PARA 0007
  -> SUFFICIENT

agent verification capability:
  Chrome DevTools / simulators / feature map
  <- PARA 0009
  -> SUFFICIENT

skill testing workflow:
  sub-agents / coordinator rubric / model cross-check / iterate
  <- PARA 0010
  -> SUFFICIENT
```

This does not prove low false-positive rate, but it is evidence that the binary Auditor is not simply rejecting all compressed semantic objects by default.

---

# 5. Attribution of the five INSUFFICIENT edges

The five failures are not all the same type.

## 5.1 Actor/object identity and role — genuine provenance incompleteness

Semantic object included:

```text
name = Lauren Tan
role = Cursor engineer who uses AI coding agents
```

but cited evidence was only:

```text
PARA 0004
PARA 0011
```

Those excerpts describe an unnamed `she` and her Cursor/PR activity, but do not locally carry the explicit name `Lauren Tan` or full role statement.

Auditor:

```text
INSUFFICIENT / MISSING_SUPPORT
```

Interpretation:

The semantic object may be correct at full-source level, but the local provenance edge is incomplete. This is a real distinction:

```text
Semantic correctness may hold
while
Local evidence sufficiency fails
```

Likely missing provenance lives in the source identity/biographical context such as `PARA 0003`.

## 5.2 Affected system = Cursor codebase — known provenance residual

Auditor:

```text
INSUFFICIENT / MISSING_SUPPORT
```

This is the previously observed case and remains a useful real catch.

The current edge does not cite the strongest explicit support identifying the code as Cursor code.

Result: **real provenance residual reproduced and blocked**.

## 5.3 Temporal uncertainty — audit-packet / evidence-type mismatch

Semantic object:

```text
Absolute calendar dates are unknown
because source publication time is unknown.
```

Auditor received only:

```text
PARA 0004
```

and correctly rejected the packet because that paragraph does not say `published_at=unknown`.

However, this semantic object's basis is not ordinary prose. It comes from deterministic source metadata:

```text
source.published_at = unknown
```

The current Event Frame already carries source metadata separately, but the real-edge projection passed only textual EvidenceV0_1 items.

Therefore this failure must NOT be simplistically classified as Sensor hallucination.

It reveals a representation/projection gap:

```text
Valid evidence can be text evidence OR trusted source metadata,
but metadata-derived semantics need explicit metadata provenance in the audit packet.
```

Important principle:

```text
Auditor should not infer/fetch missing metadata.
The packet must explicitly present it.
```

## 5.4 `not AI slop / Cursor code` tied to Lauren's merged PRs — attribution edge incomplete

Semantic object:

```text
The PRs merged by Lauren Tan are not AI slop code,
but Cursor product code used daily.
```

Evidence:

```text
PARA 0005
“这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。”
```

The excerpt supports the `not AI slop / Cursor code` content, but by itself does not locally name Lauren or explicitly bind the sentence to Lauren's merged PRs.

Auditor:

```text
INSUFFICIENT / ATTRIBUTION_UNRESOLVED
```

Interpretation:

This is another example where the semantic statement may be correct in discourse context, but the currently attached local excerpt does not carry all attribution required by the object.

## 5.5 One-hour video / workflow / efficiency — local support weaker than compressed statement

Semantic object:

```text
Lauren shared her workflow in a one-hour video,
explaining step-by-step how she achieved her efficiency.
```

Evidence:

```text
PARA 0006
“Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。”
```

Auditor:

```text
INSUFFICIENT / MISSING_SUPPORT
```

The excerpt locally supports `one-hour video` and `hand-by-hand explanation of how she got here`, but the stronger labels `workflow` and `efficiency` depend on surrounding discourse context not present in the excerpt.

Interpretation:

Likely provenance-granularity / cross-sentence-context residual rather than clear semantic hallucination.

---

# 6. Main scientific conclusion

The first real-edge experiment supports the Auditor's intended role as a local evidence gate.

It successfully demonstrated both sides:

```text
known bad provenance edge
  -> blocked

several obvious good local edges
  -> passed
```

while also revealing that an `INSUFFICIENT` verdict must be attributed carefully.

Three distinct causes now exist:

```text
A. Sensor provenance incomplete
B. semantic object stronger than local cited excerpt
C. audit packet omitted a legitimate evidence type such as source metadata
```

Therefore:

```text
INSUFFICIENT
!=
Sensor hallucination
```

and:

```text
Auditor failure diagnosis
must itself be attributed before changing the Sensor or Auditor.
```

---

# 7. Auditor status after this run

Current development conclusion:

```text
Binary decision contract                  SUPPORTED
First-pass structural validity            17/17
Known bad real edge detection              OBSERVED PASS
Obvious good real-edge passage             OBSERVED PASS on sampled edges
Local evidence-gate role                   SUPPORTED in development
Full accuracy / false-positive rate        NOT MEASURED
Production hard-gate readiness             NOT YET CLAIMED
```

Do NOT change the Auditor prompt merely because five edges failed.

The failures are informative and largely consistent with the Auditor's intended strict local contract.

---

# 8. Next minimal engineering questions

Do not add retrieval/repair to the Auditor.

First resolve two smaller questions.

## 8.1 Evidence-type completeness

The audit interface must be able to receive all evidence types already legitimately attached to the semantic representation, including deterministic source metadata when a semantic object depends on it.

Current concrete residual:

```text
temporal uncertainty
<- source.published_at = unknown
```

The real-edge projection currently provides only text evidence.

This should be corrected without giving the Auditor search/retrieval powers.

## 8.2 Human adjudication of real-edge failures

Before making the Auditor a hard production gate, create development Human Gold for at least:

```text
the five INSUFFICIENT real edges
+
a small sample of SUFFICIENT edges
```

The purpose is not a publishable benchmark score. It is to distinguish:

```text
true provenance defects
vs
legitimate conservative entailment
vs
audit-packet representation errors
```

Only then decide whether Sensor provenance generation needs a new revision or whether some edge renderings/pointers need adjustment.

---

# 9. Relationship to the RAOS north star

The value of the Auditor is now concrete:

```text
Unsupported semantic edge
        ↓
prevented from silently contaminating
D / S / P / Delta
        ↓
reduces risk of bad attention allocation
```

The Auditor is therefore not a side project.

It is an upstream quality regulator serving the same final objective:

```text
Massive Information
-> Minimal Human Attention
-> Maximum Useful Cognitive Progress
```

---

# 10. Recovery summary

```text
Semantic Sensor v0.2.2
  real provenance output audited

Semantic Evidence Auditor v0.1.1
  binary SUFFICIENT / INSUFFICIENT
  first real-edge run COMPLETE

RESULT
  17/17 scorable
  17/17 first-pass valid
  12 SUFFICIENT
  5 INSUFFICIENT

IMPORTANT
  counts are NOT accuracy

KNOWN GOOD
  PR counts, auto-merge, verification bottleneck,
  verification capability, skill-testing workflow passed

KNOWN CATCH
  Cursor-codebase provenance residual blocked

NEW RESIDUAL
  metadata-derived semantic objects need explicit metadata evidence in audit packets

NEXT
  do not modify Auditor logic
  first complete evidence-type representation + targeted Human adjudication
```

Core lesson:

> **The Auditor does not tell us whether the semantic object is false. It tells us whether the evidence currently attached to that object is strong enough to let the object pass into the rest of RAOS.**
