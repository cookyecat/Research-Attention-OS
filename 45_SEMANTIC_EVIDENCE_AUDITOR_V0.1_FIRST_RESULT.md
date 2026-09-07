# Semantic Evidence Auditor v0.1 — First Controlled Result

Status: **DEVELOPMENT RESULT — CORE SEPARATION SUPPORTED / GOLD BOUNDARY CORRECTION REQUIRED**  
Date: 2026-09-07

## 1. North-star context

RAOS exists to reduce human information burden:

```text
Massive Information
      ↓
Minimal Human Attention
      ↓
Maximum Useful Cognitive Progress
```

The Semantic Evidence Auditor is only an engineering verifier for one local provenance edge:

```text
semantic object <- cited evidence
```

It does not reread the source, retrieve replacement evidence, repair extraction, judge D/S/P/Delta, or allocate attention.

## 2. First real controlled run

Artifact:

`eval/live/results/semantic_evidence_auditor_v0_1/semantic_evidence_auditor_v0_1_20260907T120218Z.json`

Measurement HEAD:

`07a379af2512962cf3819571ee6e9b197733a2a4`

Observed:

```text
n_cases             3
n_scorable          3
n_first_pass_valid  3
n_verdict_match     2   (against the predeclared development Gold)
model               deepseek-v4-flash
repair_used         false for all 3
```

This is development/calibration evidence only and must not be reported as general auditor accuracy.

## 3. Case-level findings

### Case A — correct support

Object:

`The affected system is the Cursor codebase.`

Evidence:

`PARA 0005`: explicitly identifies the code as Cursor code.

Gold: `SUFFICIENT`  
Predicted: `SUFFICIENT`

Rationale correctly states that the excerpt directly identifies the code as Cursor's code.

Result: **PASS**.

### Case B — wrong but traceable support

Object:

`The affected system is the Cursor codebase.`

Evidence:

`PARA 0004`: gives PR counts only.

Gold: `INSUFFICIENT`  
Predicted: `INSUFFICIENT`

Rationale correctly identifies the missing material component: codebase identity is not present in the cited evidence.

Result: **PASS**.

This directly supports the core motivation for the Auditor:

```text
Traceable Provenance != Sufficient Provenance
```

The Auditor can distinguish at least this observed correct-vs-merely-traceable pair.

### Case C — original ambiguous-efficiency case

Object:

`Boris achieved approximately the same PR throughput as Lauren Tan.`

Evidence:

`PARA 0006`: says Boris and others reported achieving `类似的效率` with coding agents.

Predeclared Gold: `UNCERTAIN`  
Predicted: `INSUFFICIENT`

The model's rationale identifies that the cited evidence does not specify the metric as PR throughput and does not explicitly establish the claimed Boris-vs-Lauren PR-throughput comparison.

## 4. Human-Gold adjudication

The original Case C Gold was too permissive for the v0.1 verdict definitions.

The auditor contract already states:

```text
INSUFFICIENT
= at least one material part is absent from the cited evidence

UNCERTAIN
= evidence genuinely bears on the object, but ambiguity of wording/reference/scope/attribution prevents a confident support judgment
```

Case C contains a stronger material claim:

```text
PR throughput
```

but the excerpt only states:

```text
类似的效率
```

Therefore the specific metric `PR throughput` is missing rather than merely ambiguous.

Adjudicated development label:

```text
RS02-AUD-003 -> INSUFFICIENT
```

Important methodology note:

> This adjudication occurred after seeing the model output. The original run remains recorded as **2/3 against predeclared Gold**. The corrected label may be used for future development/calibration, but MUST NOT be retroactively reported as a fresh 3/3 accuracy result.

## 5. What still needs to be tested

The first run now supports:

```text
SUFFICIENT vs INSUFFICIENT separation    OBSERVED SUPPORT
first-pass structural validity           3/3
repair dependence                        0/3
```

But it does **not** yet cleanly test `UNCERTAIN`.

The next development case should isolate genuine reference/scope ambiguity without adding a plainly missing material claim.

Recommended replacement/additional case:

```text
object:
Boris achieved efficiency similar to Lauren Tan's.

evidence:
“很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。”

Gold:
UNCERTAIN
```

Reason:

- `类似的效率` makes the evidence relevant;
- the local excerpt does not explicitly resolve what `类似` refers to;
- unlike the original Case C, the object does not additionally invent the specific metric `PR throughput`.

This is a cleaner test of the intended `UNCERTAIN` boundary.

## 6. Occam interpretation

Do **not** change the Auditor prompt/model architecture based on this first run.

The measured issue is currently a test-label design problem, not a demonstrated verifier-capability failure.

Therefore the minimal next step is:

```text
keep Auditor v0.1 unchanged
-> correct the development Gold for AUD-003
-> add one clean UNCERTAIN calibration case
-> rerun the tiny controlled set
```

No retrieval, repair, full-source rereading, knowledge graph, or additional model stage is justified yet.

## 7. Current status

```text
Semantic Sensor v0.2.2                     DEVELOPMENT / usable for current frontier
Temporal Anchor                            CLOSED
Structural provenance validation           SUPPORTED
Semantic Evidence Auditor v0.1             FIRST REAL RUN COMPLETE
Correct support -> SUFFICIENT               OBSERVED PASS
Wrong traceable support -> INSUFFICIENT     OBSERVED PASS
UNCERTAIN boundary                         NOT YET CLEANLY TESTED
Original predeclared result                 2/3
Post-run Gold adjudication                  AUD-003 -> INSUFFICIENT
Fresh validation                            NONE
```

Core lesson:

> **When an experiment exposes ambiguity in the Gold label rather than in the model behavior, fix the measurement definition before changing the mechanism.**
