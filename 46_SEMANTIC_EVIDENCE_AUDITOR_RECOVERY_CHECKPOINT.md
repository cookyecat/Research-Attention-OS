# Semantic Evidence Auditor — Recovery Checkpoint after First Calibration Run

Status: **ACTIVE DEVELOPMENT / CORE SUPPORT CHECK PASSED / UNCERTAIN BOUNDARY CALIBRATION NEXT**  
Date: 2026-09-07

## North star

```text
Massive Information
      ↓
Minimal Human Attention
      ↓
Maximum Useful Cognitive Progress
```

CROA remains the directional objective:

```text
Useful Cognitive Change / Human Attention Cost
```

The Semantic Sensor and Auditor are support mechanisms only. Do not let this frontier expand into a general-purpose knowledge system.

## Current architecture

```text
Raw Source
  ↓
Semantic Sensor v0.2.2
  ↓
semantic object + cited evidence
  ↓
Semantic Evidence Auditor v0.1
  ↓
Audited Semantic Skeleton
  ↓
D / S / P / Delta
  ↓
Attention Policy
```

Auditor Occam boundary remains frozen for v0.1:

```text
input  = one semantic object + already-cited evidence excerpts
output = SUFFICIENT / INSUFFICIENT / UNCERTAIN + brief rationale

NO full-source reread
NO evidence retrieval
NO repair
NO D/S/P/Delta
NO outside-world truth verification
NO attention action
```

## First real run

Artifact:

`eval/live/results/semantic_evidence_auditor_v0_1/semantic_evidence_auditor_v0_1_20260907T120218Z.json`

Measurement HEAD:

`07a379af2512962cf3819571ee6e9b197733a2a4`

Original observed result:

```text
n_cases             3
n_scorable          3
n_first_pass_valid  3
n_verdict_match     2 against PREDECLARED development Gold
repair_used         0/3
```

Case-level:

```text
AUD-001 correct Cursor-code support
Gold SUFFICIENT -> Pred SUFFICIENT
PASS

AUD-002 PR-count evidence used for Cursor-code identity
Gold INSUFFICIENT -> Pred INSUFFICIENT
PASS

AUD-003 “类似的效率” used to claim same PR throughput as Lauren
Gold UNCERTAIN -> Pred INSUFFICIENT
MISMATCH against original Gold
```

## Adjudication of AUD-003

The original Gold was too permissive.

The semantic object adds the material claim:

```text
PR throughput
```

while the evidence only says:

```text
类似的效率
```

Under the already-written v0.1 verdict semantics, a missing stronger material claim is `INSUFFICIENT`, not `UNCERTAIN`.

Therefore:

```text
AUD-003 adjudicated Gold = INSUFFICIENT
Gold status = POST_RUN_ADJUDICATED_20260907
```

Methodology invariant:

> Do not retroactively report the first run as fresh 3/3. Preserve the original predeclared result as 2/3 and record the Gold correction separately.

Archived analysis:

`45_SEMANTIC_EVIDENCE_AUDITOR_V0.1_FIRST_RESULT.md`

## New clean UNCERTAIN calibration case

Added:

```text
AUD-004
object:
  Boris achieved efficiency similar to Lauren Tan's.

evidence:
  “很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。”

Gold:
  UNCERTAIN

Gold status:
  PREDECLARED_CALIBRATION_AFTER_INITIAL_RUN
```

Reason:

```text
- the evidence contains an explicit similarity relation;
- the evidence is therefore relevant;
- the local excerpt does not resolve the antecedent of “类似”;
- unlike old AUD-003, no extra missing metric such as PR throughput is injected.
```

This is intended to isolate genuine reference ambiguity.

## Development-case provenance now encoded in runner

Current controlled set:

```text
AUD-001  SUFFICIENT    PREDECLARED_INITIAL
AUD-002  INSUFFICIENT  PREDECLARED_INITIAL
AUD-003  INSUFFICIENT  POST_RUN_ADJUDICATED_20260907
AUD-004  UNCERTAIN     PREDECLARED_CALIBRATION_AFTER_INITIAL_RUN
```

Runner commit:

`a749a0f3a7c6abcedc719a39d01b4398d5118622`

Focused-test update:

`83e9b83f70535cc04a804a480e2f06aebc2ab013`

Auditor implementation remains unchanged:

`c06ba28e13d8adab8b88312be3a7a0991b156108`

## Current scientific status

```text
Semantic Sensor temporal anchor                    CLOSED
Semantic Sensor structural contract                SUPPORTED on current dev cases
Bare URL / locator residual                        OBSERVED PASS
Unsupported inference residual                     OBSERVED PASS
Event/Epistemic duplicate residual                 OBSERVED PASS
Structural provenance validation                   SUPPORTED
Evidence sufficiency need                          CONFIRMED
Semantic Evidence Auditor v0.1                     IMPLEMENTED
Correct-vs-wrong support separation                OBSERVED SUPPORT (AUD-001/AUD-002)
UNCERTAIN verdict boundary                         OPEN / calibration next
Full batch-level audit wiring                      NOT STARTED
Evidence retrieval/repair                          NOT JUSTIFIED YET
Fresh validation                                   NONE
```

## Exact next action

Sync:

```bash
git pull --rebase
```

Focused tests:

```bash
cd backend
.venv/bin/pytest tests/eval/test_semantic_evidence_auditor_v0_1.py -q
cd ..
```

Then rerun the tiny development set:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_dev_v0_1.py
```

Interpretation rule:

- AUD-001/AUD-002 are repeated sanity checks, not new evidence.
- AUD-003 checks consistency with the adjudicated insufficient boundary.
- AUD-004 is the only newly calibrated question: can the unchanged Auditor distinguish genuine ambiguity from missing support?
- Even a 4/4 result remains development/calibration, not fresh validation accuracy.

## Decision after next run

If AUD-004 -> UNCERTAIN with sensible rationale:

```text
Auditor verdict semantics are provisionally usable
-> next minimal step: apply v0.1 to a few actual v0.2.2 extraction edges
```

If AUD-004 -> INSUFFICIENT:

```text
Do not redesign architecture.
Inspect whether the prompt boundary between missing support and unresolved reference is still underspecified.
```

If AUD-001/AUD-002 regress:

```text
Stop and attribute model/prompt instability before any integration.
```

## Recovery summary

```text
NOW:
Semantic Evidence Auditor v0.1
core sufficient-vs-insufficient distinction observed
UNCERTAIN boundary not yet cleanly demonstrated

DO NOT:
add retrieval
add repair
add another model stage
wire whole-batch auditing yet

NEXT:
rerun 4-case calibrated RS02 set
focus on AUD-004 only
```

Core lesson:

> **Fix the measurement boundary before adding mechanism. The simplest system that can reliably distinguish supported, unsupported, and genuinely ambiguous evidence edges is enough for this stage.**
