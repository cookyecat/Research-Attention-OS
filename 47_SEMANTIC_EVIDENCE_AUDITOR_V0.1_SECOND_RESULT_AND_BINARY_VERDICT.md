# Semantic Evidence Auditor v0.1 — Second Controlled Result and Binary-Verdict Simplification

Status: **DEVELOPMENT RESULT / ARCHITECTURE SIMPLIFICATION RECOMMENDED**  
Date: 2026-09-07

## 1. Run

Artifact:

`eval/live/results/semantic_evidence_auditor_v0_1/semantic_evidence_auditor_v0_1_20260907T122518Z.json`

Measurement HEAD:

`ec986719d27cd21c13076d7e17d848be42215d4a`

Observed:

```text
n_cases            4
n_scorable         4
n_first_pass_valid 4
n_verdict_match    3
repair_used        0/4
```

Case results:

```text
AUD-001  Gold SUFFICIENT    -> SUFFICIENT    PASS
AUD-002  Gold INSUFFICIENT  -> INSUFFICIENT  PASS
AUD-003  Gold INSUFFICIENT  -> INSUFFICIENT  PASS
AUD-004  Gold UNCERTAIN     -> INSUFFICIENT  mismatch
```

## 2. AUD-004 interpretation

AUD-004 object:

```text
Boris achieved efficiency similar to Lauren Tan's.
```

Cited excerpt:

```text
很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。
```

The excerpt contains a similarity relation but does not identify Lauren Tan as the comparison target inside the cited evidence supplied to the Auditor.

Under the Auditor's local-only contract, the material comparison target is unsupported.

Therefore the model's `INSUFFICIENT` verdict is consistent with the current sufficiency semantics.

## 3. Occam finding

The Auditor asks one question:

> Are the cited excerpts sufficient to support this semantic object?

For that question, unresolved ambiguity itself means the support is not sufficient.

Therefore a three-way top-level verdict may be unnecessary.

Recommended simplification:

```text
SUFFICIENT
INSUFFICIENT
```

Preserve useful diagnostics separately, e.g.:

```text
reason_code = MISSING_SUPPORT
reason_code = AMBIGUOUS_REFERENCE
reason_code = OVERSTRONG_SCOPE
reason_code = ATTRIBUTION_UNRESOLVED
```

This preserves information while keeping the state space minimal.

Conceptually:

```text
support sufficient?  -> binary verdict
why not?              -> diagnostic reason
```

This is preferred to forcing ambiguity into a third top-level verdict.

## 4. Gold lifecycle

Corrected/adjudicated Gold should absolutely be reused for development and regression.

Development Gold is allowed to improve:

```text
model result / human review
      ↓
adjudication
      ↓
versioned Development Gold
      ↓
future regression
```

But post-run adjudicated cases must never be re-described as fresh validation evidence.

Recommended distinction:

```text
DEVELOPMENT_GOLD
  mutable through explicit adjudication/versioning

FROZEN_VALIDATION_GOLD
  fixed before model execution
```

Model feedback may trigger a Gold review, but the final Gold change must be an explicit human adjudication with rationale and provenance.

## 5. Relationship to Attention Actions

Semantic Evidence Audit is not an Attention Action signal.

Do NOT map:

```text
SUFFICIENT   -> ENGAGE
INSUFFICIENT -> DROP
```

Instead it is an upstream input-quality gate:

```text
Raw Source
  ↓
Semantic Sensor
  ↓
Evidence Audit
  ↓
trusted / unresolved semantic representation
  ↓
D / S / P / Delta
  ↓
Attention Policy
  ↓
DROP / AWARE / WATCH / ENGAGE
```

Its value is indirect but important: unsupported actor, scope, affected system, time, quantity, or causal claims can distort D/S/P/Delta and therefore misallocate scarce human attention.

Invariant:

```text
AuditVerdict != AttentionAction
```

## 6. Current status

```text
Auditor structural interface               PASS
First-pass structural validity             4/4 on controlled dev set
Repair dependence                          0/4
Correct support discrimination             OBSERVED PASS
Wrong-but-traceable support discrimination OBSERVED PASS
Overstrong-scope detection                 OBSERVED PASS
UNCERTAIN top-level class                   NOT JUSTIFIED / likely removable
Binary sufficiency verdict                 RECOMMENDED NEXT SIMPLIFICATION
Fresh validation                           NONE
```

## 7. Recommended next step

Do not tune the model to force `UNCERTAIN`.

Instead:

1. simplify the Auditor to binary `SUFFICIENT / INSUFFICIENT`;
2. keep ambiguity as a diagnostic reason, not a verdict;
3. preserve all prior v0.1 artifacts and Gold provenance;
4. then apply the simplified Auditor to real provenance edges emitted by Semantic Sensor v0.2.2.

Core lesson:

> **When a state distinction does not change the decision and can be preserved as a diagnostic attribute, prefer the simpler state space.**
