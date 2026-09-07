# Semantic Evidence Auditor v0.1 — Design, Experiment, and Recovery Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / FIRST CONTROLLED RUN PENDING**  
Date: 2026-09-07

> Recovery purpose: this document is the current restore point for the RAOS Semantic Sensor frontier. Resume from here without reopening CLOSED Semantic Sensor issues unless new evidence requires it.

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

The Semantic Sensor and Semantic Evidence Auditor are not goals by themselves. They exist because downstream attention allocation is only trustworthy when RAOS first understands the source and can explain where that understanding came from.

Current plain-language decomposition:

```text
Semantic Sensor
= 眼睛：文章到底说了什么？

Semantic Evidence Auditor
= 复核：你说这个意思，引用的证据真的够吗？

D / S / P / Delta
= 大脑：这些信息意味着什么？

Attention Policy
= 行动：人应该花多少注意力？
```

Do not let the front-end grow into a general knowledge system unrelated to the attention-budget objective.

---

# 2. Methodology continuity

The current research line follows the same isolation logic as earlier Oracle experiments.

```text
Oracle-Delta
  give cognitive change directly
  -> test Attention Policy only

Clean D/S/P evaluation
  give already-organized event semantics
  -> test D/S/P only

Semantic Sensor
  give raw article/post/paper
  -> test reading comprehension / extraction

Semantic Evidence Auditor
  give one extracted semantic object + its cited evidence
  -> test whether the evidence edge is actually valid
```

Methodological principle:

```text
isolate one layer
-> measure it
-> attribute the failure
-> add only the missing mechanism
-> then restore more real-world complexity
```

This is the same scientific discipline used elsewhere in RAOS and STAR performance engineering.

---

# 3. Why the Auditor exists

Semantic Sensor v0.2.2 showed that provenance can be structurally valid but semantically wrong.

Observed RS02 residual:

```text
semantic object:
  affected system = Cursor codebase

cited evidence:
  PARA 0004 -> PR counts
  PARA 0011 -> auto-merge into main

missing actual support:
  PARA 0005 -> explicitly identifies the code as Cursor code
```

Therefore:

```text
Traceable Provenance != Sufficient Provenance
```

and:

```text
Structural Provenance Validation != Semantic Evidence Audit
```

A Pydantic/schema validator can check that a support id exists. It cannot decide whether the cited excerpt actually supports the meaning carried by that edge.

---

# 4. Occam's Razor boundary

v0.1 deliberately solves the smallest missing problem.

The Auditor receives:

```text
one semantic object
+
its already-cited evidence excerpts
```

and returns only:

```text
SUFFICIENT
INSUFFICIENT
UNCERTAIN
+
brief rationale
+
unsupported/ambiguous aspect when needed
```

It MUST NOT:

```text
read/search the whole source
retrieve replacement evidence
repair the extractor output
rewrite the semantic object
cluster events
build a knowledge graph
verify outside-world truth
judge D/S/P/Delta
allocate attention
```

Core local edge:

```text
semantic object <- cited evidence
```

This boundary is intentional. Do not add retrieval/repair until the pure verifier is shown to work.

---

# 5. Verdict semantics

## SUFFICIENT

The cited excerpts alone support every material part of the semantic object, allowing conservative paraphrase and ordinary linguistic entailment.

## INSUFFICIENT

At least one material part is absent from the cited evidence, depends on outside context, or requires an uncited passage.

Missing evidence is **INSUFFICIENT**, not UNCERTAIN.

## UNCERTAIN

The cited evidence genuinely bears on the object, but ambiguity of wording, reference, scope, or attribution prevents a confident support judgment.

Use UNCERTAIN only for real ambiguity in the supplied evidence.

---

# 6. v0.1 controlled experiment

Use RS02 only. These are development/calibration cases and can never become fresh validation evidence.

## Case A — correct support

```text
object:
The affected system is the Cursor codebase.

support:
PARA 0005
“这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。”

Human Gold:
SUFFICIENT
```

## Case B — wrong but traceable support

```text
object:
The affected system is the Cursor codebase.

support:
PARA 0004
“上个月已经合入了 1000 个 PR。这个月才过去 12 天，她又合入了接近 800 个。”

Human Gold:
INSUFFICIENT
```

## Case C — evidence relevant but scope ambiguous

```text
object:
Boris achieved approximately the same PR throughput as Lauren Tan.

support:
PARA 0006
“很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。”

Human Gold:
UNCERTAIN
```

Reason: `类似的效率` is relevant but does not specify that the compared quantity is PR throughput.

Primary development question:

```text
Can the auditor distinguish:
correct support
vs merely traceable support
vs genuinely ambiguous support?
```

Do not report a general auditor accuracy claim from only three development cases.

---

# 7. Implementation

Files:

```text
eval/live/semantic_evidence_auditor_v0_1.py
eval/live/run_semantic_evidence_auditor_dev_v0_1.py
backend/tests/eval/test_semantic_evidence_auditor_v0_1.py
```

Implementation commits:

```text
c06ba28e13d8adab8b88312be3a7a0991b156108
feat: add semantic evidence auditor v0.1

b1c48ce3b1e326b5a485cf4f10531ef06a2683b1
feat: add semantic evidence auditor development runner

775ee01f07c94aa09c93e7ed2c1587440ce22f3d
test: cover semantic evidence auditor v0.1
```

Auditor engineering choices:

```text
model              = configured RAOS LLM (currently DeepSeek v4 Flash in development)
thinking           = disabled
reasoning_effort   = none
timeout            = 45 s
response format    = json_object
schema             = SemanticEvidenceAuditResultV0_1
repair             = one structural repair fallback
scope              = one semantic object vs cited evidence only
```

Schema output:

```text
interface_version
audit_id
verdict
rationale
unsupported_or_uncertain_aspect
```

No new RAOS theoretical variable has been introduced.

---

# 8. Current Semantic Sensor status before Auditor run

Do not reopen these without new evidence:

```text
Semantic batch v0.2 structural contract        SUPPORTED on RS02/RS09 development
First-pass structural validity                 2/2 on v0.2 RS02/RS09
RS09 Event/non-event discrimination            SUPPORTED
RS09 multi-support semantic compression        IMPROVED
Non-event provenance excerpts                  PRESENT / cheaply auditable
Confidence semantics                           clarified as extraction support confidence
Temporal Anchor residual                       CLOSED in v0.2.1
Bare URL / locator residual                    OBSERVED PASS in v0.2.2
Unsupported 'presumably' attribution residual  OBSERVED PASS in v0.2.2
Event/Epistemic duplicate residual              OBSERVED PASS in v0.2.2
Evidence sufficiency                            OPEN
Semantic Evidence Auditor                      IMPLEMENTED / FIRST RUN PENDING
```

Fresh validation evidence remains:

```text
NONE
```

All RS01-RS12 are development data. RS13-RS14 remain reserved/unconsumed unless explicitly changed by a later protocol.

---

# 9. Exact next commands

Sync:

```bash
git pull --rebase
```

Run focused tests:

```bash
cd backend
.venv/bin/pytest \
  tests/eval/test_semantic_evidence_auditor_v0_1.py -q
cd ..
```

Then run the first real controlled audit experiment:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_dev_v0_1.py
```

Expected console summary contains:

```text
n_cases
n_scorable
n_first_pass_valid
n_verdict_match
```

Inspect each case individually. Do not celebrate only the aggregate 3/3 without checking the rationale and whether verdict semantics were used correctly.

---

# 10. Decision tree after the first run

## If 3/3 with sensible rationales

Do NOT immediately build a large auditing framework.

Next minimal step:

```text
apply the auditor to a small set of actual v0.2.2 extraction edges
```

First target should include the known RS02 wrong edge:

```text
Cursor codebase <- PARA 0004 / PARA 0011
```

Expected:

```text
INSUFFICIENT
```

Only after actual extracted edges work should we consider batch-level audit wiring.

## If SUFFICIENT vs INSUFFICIENT works but UNCERTAIN fails

Calibrate verdict boundary only. Do not redesign the architecture.

## If correct and incorrect support cannot be separated

Attribute whether the problem is:

```text
prompt semantics
model capability
evidence presentation
or Human Gold ambiguity
```

Do not add retrieval/repair until the verifier itself is understood.

---

# 11. Future stages — not yet implemented

Only after v0.1 is supported:

```text
SemanticExtractionBatch
        ↓
select semantic edges
        ↓
Semantic Evidence Auditor
        ↓
Audited Semantic Skeleton
```

Possible later stage, if needed:

```text
INSUFFICIENT edge
        ↓
source-grounded evidence retrieval / repair
```

That would be a separate mechanism. Do not merge it into Auditor v0.1.

---

# 12. Recovery one-screen summary

```text
RAOS NORTH STAR
Massive Information -> Minimal Human Attention -> Maximum Useful Cognitive Progress

CURRENT FRONTIER
Raw Source
  ↓
Semantic Sensor v0.2.2
  ↓
Semantic object + cited evidence
  ↓
Semantic Evidence Auditor v0.1   <- NOW
  ↓
Audited Semantic Skeleton
  ↓
D / S / P / Delta
  ↓
Attention Policy

WHY NOW
Schema can prove an evidence edge points somewhere.
It cannot prove that the evidence actually supports the meaning.

OCCAM BOUNDARY
Auditor only judges object <- cited evidence.
No full-source search. No repair. No D/S/P. No attention action.

NEXT ACTION
Run test_semantic_evidence_auditor_v0_1.py
then run_semantic_evidence_auditor_dev_v0_1.py

STATUS
Implementation ready; first real 3-case controlled run pending.
```

Core lesson carried forward:

> **The system should add a new mechanism only when a measured residual proves that the existing simpler mechanism cannot represent or verify what matters.**
