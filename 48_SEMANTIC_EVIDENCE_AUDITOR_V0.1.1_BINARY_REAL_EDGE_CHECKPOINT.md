# Semantic Evidence Auditor v0.1.1 — Binary Sufficiency and Real-Edge Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / FIRST REAL-EDGE RUN PENDING**  
Date: 2026-09-07

> Recovery purpose: this is the current restore point for the RAOS Semantic Sensor / Evidence Auditor frontier. Resume here without reopening CLOSED issues unless new evidence requires it.

---

# 1. Keep the RAOS north star visible

Research Attention OS exists to reduce human information burden:

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

The Evidence Auditor is not an end in itself. It exists to prevent unsupported semantic interpretations from contaminating D/S/P/Delta and therefore wasting human attention.

Plain-language role:

```text
Semantic Sensor
= 阅读理解：文章说了什么？

Semantic Evidence Auditor
= 机场安检 / 监管闸门：你说这个意思，当前引用的证据够不够？

D / S / P / Delta
= 大脑：这些信息意味着什么？

Attention Policy
= 人应该花多少注意力？
```

Important separation:

```text
AuditVerdict != AttentionAction
```

The Auditor does NOT decide AWARE/WATCH/ENGAGE. It protects the semantic inputs that those downstream decisions depend on.

---

# 2. Why v0.1.1 exists

Semantic Evidence Auditor v0.1 initially used three verdicts:

```text
SUFFICIENT
INSUFFICIENT
UNCERTAIN
```

Two controlled runs showed that the third top-level state was not necessary for the actual audit question.

The audit question is binary:

> **Are the currently cited excerpts sufficient to support the semantic object as written?**

If a reference is ambiguous, then the evidence is not sufficient for the specific object. The ambiguity is valuable as diagnosis, but it does not require a third decision state.

Therefore:

```text
Decision = binary
Diagnosis = descriptive
```

This is an Occam's Razor simplification, not an increase in system complexity.

---

# 3. v0.1.1 contract

Input:

```text
one semantic object
+
its already-cited evidence excerpts
```

Output:

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

rationale:
  concise source-grounded explanation

unsupported_aspect:
  empty when sufficient; otherwise the unsupported/ambiguous material part
```

Semantics:

## SUFFICIENT

Every material part of the semantic object is supported by the cited evidence alone, allowing conservative paraphrase and ordinary linguistic entailment.

## INSUFFICIENT

At least one material part is not supported by the cited evidence, depends on uncited context, is stronger than the evidence, or remains unresolved by ambiguity/reference/attribution.

Examples:

```text
missing actor identity       -> INSUFFICIENT / ATTRIBUTION_UNRESOLVED
missing system identity      -> INSUFFICIENT / MISSING_SUPPORT
ambiguous pronoun/reference  -> INSUFFICIENT / AMBIGUOUS_REFERENCE
claim stronger than excerpt  -> INSUFFICIENT / OVERSTRONG_SCOPE
```

No third verdict is needed.

---

# 4. Occam boundary — still strict

The Auditor MUST NOT:

```text
reread/search the full source
retrieve replacement evidence
repair extractor semantics
rewrite semantic objects
verify outside-world truth
judge D/S/P/Delta
allocate DROP/AWARE/WATCH/ENGAGE
```

It verifies only:

```text
semantic object <- cited evidence
```

If evidence is insufficient, v0.1.1 reports why. It does not fix the edge.

Future retrieval/repair, if ever justified, must remain a separate stage.

---

# 5. Development Gold policy

Development Gold may improve.

Correct process:

```text
model feedback
   ↓
human review / adjudication
   ↓
better Development Gold
   ↓
future regression/calibration
```

But a post-run adjudicated case must not be retrospectively counted as fresh validation evidence.

Therefore preserve Gold provenance such as:

```text
PREDECLARED_INITIAL
POST_RUN_ADJUDICATED_...
PREDECLARED_CALIBRATION_AFTER_INITIAL_RUN
```

Development data is for learning/calibration. Frozen holdout data is for proving generalization.

---

# 6. What v0.1 already demonstrated

RS02 development cases showed:

```text
correct support
  Cursor codebase <- PARA 0005
  -> SUFFICIENT

wrong but traceable support
  Cursor codebase <- PARA 0004
  -> INSUFFICIENT
```

This is the core capability the Auditor was introduced to test:

```text
Traceable Provenance != Sufficient Provenance
```

and:

```text
Structural Provenance Validation != Semantic Evidence Audit
```

The initial ternary UNCERTAIN experiments instead helped simplify the interface to binary sufficiency.

---

# 7. New frontier — audit actual Sensor output

Do not continue creating many artificial RS02 mini-cases.

The next increase in realism is:

```text
Semantic Sensor v0.2.2 artifact
        ↓
actual extractor-produced provenance edges
        ↓
Semantic Evidence Auditor v0.1.1
        ↓
SUFFICIENT / INSUFFICIENT + diagnosis
```

No Human Gold is attached to this first real-edge run.

This is NOT an accuracy benchmark. It is a development audit/inspection of actual Sensor output.

---

# 8. Real-edge projection

The new runner reads a real Semantic Sensor v0.2.2 JSON artifact and projects existing structures into local audit edges.

Audited edge families:

```text
Event Frame:
  actor/object
  action/change
  affected system/population
  uncertainty

Non-event:
  epistemic unit
```

Each audit case contains only:

```text
semantic object
+
that object's already-cited supports
```

No uncited source context is injected.

This preserves the same local-audit contract as the controlled cases.

---

# 9. Known real RS02 edge expected to be caught

Semantic Sensor v0.2.2 produced:

```text
affected system:
  Cursor codebase

cited supports:
  PARA 0004 -> PR counts
  PARA 0011 -> auto-merge into main
```

The actual source support identifying the code as Cursor code exists in PARA 0005, but it was not cited by this object.

Therefore the real-edge Auditor should judge the existing edge as:

```text
INSUFFICIENT
```

likely diagnosis:

```text
MISSING_SUPPORT
```

Important: the Auditor must NOT search for or add PARA 0005. Detecting the bad edge is the current task.

---

# 10. Implementation

Files:

```text
eval/live/semantic_evidence_auditor_v0_1_1.py
eval/live/run_semantic_evidence_auditor_real_edges_v0_1_1.py
backend/tests/eval/test_semantic_evidence_auditor_v0_1_1.py
```

Commits:

```text
81946a4068a3f21dcce3de4ed57ab4a549f52dce
feat: simplify semantic evidence auditor to binary sufficiency

eada91694c9e3b883f13721ea75b92b39a2c18d3
feat: audit real semantic sensor provenance edges

b477298d3dc818fc7d96c818131791e399f7236c
test: cover binary auditor and real edge projection
```

Auditor remains:

```text
thinking           disabled
reasoning_effort   none
timeout            45 s
response_format    json_object
scope              one semantic object vs cited evidence only
```

---

# 11. First real-edge run

Use the actual RS02 v0.2.2 artifact already produced locally:

```text
eval/live/results/semantic_evidence_dev_v0_2_2/
semantic_evidence_dev_v0_2_2_20260907T103010Z.json
```

Sync and test:

```bash
git pull --rebase

cd backend
.venv/bin/pytest \
  tests/eval/test_semantic_evidence_auditor_v0_1_1.py -q
cd ..
```

Then run:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_real_edges_v0_1_1.py \
  --artifact eval/live/results/semantic_evidence_dev_v0_2_2/semantic_evidence_dev_v0_2_2_20260907T103010Z.json
```

Optional debugging cap:

```bash
--max-edges N
```

Do not use the cap for the first formal real-edge development run unless necessary.

---

# 12. What to inspect after the run

Console summary:

```text
n_edges
n_scorable
n_first_pass_valid
n_sufficient
n_insufficient
reason_counts
```

But aggregate counts are not enough.

Inspect at least:

```text
1. known bad affected-system edge
2. a clearly supported action/change edge
3. a clearly supported epistemic unit
4. any edge marked AMBIGUOUS_REFERENCE / OVERSTRONG_SCOPE / OTHER
```

Primary scientific question:

> **Does the binary Auditor meaningfully separate trustworthy real Sensor edges from unsupported ones without rereading the source or repairing them?**

---

# 13. Decision tree after the real-edge run

## If known bad edge is caught and obvious good edges pass

Result:

```text
Semantic Evidence Auditor v0.1.1
SUPPORTED as a local development verifier
```

Next step should NOT be automatic repair yet.

First inspect the failure pattern across real edges and decide whether selective audit is enough or whether batch-level gating is justified.

## If many obviously good edges are marked insufficient

Attribute whether the issue is:

```text
semantic object rendering too broad
Auditor prompt too strict
source support granularity
or extractor provenance quality
```

Do not add retrieval/repair before attribution.

## If known bad edge passes as sufficient

The core verifier is not yet supported. Stay on the Auditor and attribute why.

---

# 14. Current status

```text
Semantic Sensor v0.2.2                  DEVELOPMENT / PARTIAL PASS
Temporal Anchor                         CLOSED
URL / locator filtering                 OBSERVED PASS
Unsupported inference residual          OBSERVED PASS
Event/Epistemic duplicate residual      OBSERVED PASS
Evidence sufficiency residual           OPEN in extractor output

Semantic Evidence Auditor v0.1          CONTROLLED CAPABILITY OBSERVED
Ternary verdict                          SIMPLIFIED AWAY
Semantic Evidence Auditor v0.1.1        IMPLEMENTED
Binary sufficiency policy               IMPLEMENTED
Real-edge projection runner             IMPLEMENTED
First real-edge run                     PENDING

Fresh validation evidence               NONE
```

---

# 15. Recovery one-screen summary

```text
RAOS NORTH STAR
Massive Information -> Minimal Human Attention -> Maximum Useful Cognitive Progress

CURRENT FRONTIER
Raw Source
  ↓
Semantic Sensor v0.2.2
  ↓
semantic objects + cited evidence
  ↓
Semantic Evidence Auditor v0.1.1   <- NOW
  binary: SUFFICIENT / INSUFFICIENT
  diagnosis: why
  ↓
Audited Semantic Skeleton
  ↓
D / S / P / Delta
  ↓
Attention Policy

ROLE
Airport security / regulatory gate for semantic evidence.
It protects downstream cognition and attention allocation from unsupported interpretations.

OCCAM BOUNDARY
No full-source search. No repair. No D/S/P. No attention action.

NEXT ACTION
Run v0.1.1 focused tests, then audit the real RS02 v0.2.2 artifact.
```

Core lesson:

> **The Auditor should not decide whether a statement is probably true. It should decide whether the currently cited evidence is sufficient for the statement as written.**
