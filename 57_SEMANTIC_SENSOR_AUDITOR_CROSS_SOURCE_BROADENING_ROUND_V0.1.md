# Semantic Sensor / Auditor — Cross-Source Broadening Round v0.1

Status: **PREREGISTERED / DEVELOPMENT-ONLY / RUN PENDING**  
Date: 2026-09-07

> Recovery purpose: this is the current restore point after RS02 saturation. Resume here without tuning RS02 or changing frozen mechanisms inside the round.

---

# 1. Why this round exists

RAOS semantic-perception development has learned a great deal from RS02, including:

```text
Semantic Sensor representation
Temporal anchoring
Evidence sufficiency
Semantic Evidence Auditor
Evidence Packet
metadata/context/stability residuals
```

That source has now shaped enough design decisions that further rule changes driven by RS02 alone would create a serious overfitting risk.

Canonical methodology is in:

```text
56_SENSOR_AUDITOR_GENERALIZATION_AND_ANTI_OVERFITTING_PROTOCOL.md
```

Current decision:

```text
RS02 = SATURATED_DEVELOPMENT
```

Use it for regression and bug reproduction only.

The next scientific question is no longer:

> “How do we make RS02 look better?”

It is:

> **Which observed semantic/provenance/audit failure structures actually repeat across materially different kinds of information?**

---

# 2. Core strategy

```text
Stop tuning RS02
      ↓
Freeze current mechanisms
      ↓
Cross-source broadening
      ↓
Human adjudication of repeated patterns
      ↓
Only then consider redesign
```

This is the semantic-system analogue of avoiding train-set overfitting.

Important:

> **Model weights need not change for the research process itself to overfit. Human design decisions can train the system against repeatedly inspected examples.**

---

# 3. Formal preregistration artifact

Machine-readable round manifest:

```text
eval/live/manifest.semantic_sensor_auditor_broadening_v0_1.yaml
```

Commit:

```text
182af1b9bf4532217bd81237fda6d4d95202127c
eval: preregister semantic sensor auditor broadening round v0.1
```

The manifest freezes:

```text
source list and order
Sensor identity
Sensor prompt SHA
Auditor identity
Auditor prompt SHA
evidence policy
predeclared observation dimensions
anti-overfitting interpretation rules
```

---

# 4. Frozen mechanism identities

## Semantic Sensor

```text
version:
semantic-evidence-extractor-v0.2.2

prompt version:
semantic-evidence-extraction-v0.2.2

prompt SHA256:
52bae84a3d06bbaa597cdbf43460c8945dcd13cb53616390c05a6a40995dfbe9

schema:
SemanticExtractionBatchV0_2

thinking:
disabled

temperature:
0.1
```

Temporal policy remains:

```text
measurement-time-never-substitutes-source-time-v0.2.1
```

Audit-discipline policy remains:

```text
sufficient-provenance-attribution-locator-dedup-v0.2.2
```

## Semantic Evidence Auditor

```text
version:
semantic-evidence-auditor-v0.1.1

prompt version:
semantic-evidence-audit-v0.1.1

prompt SHA256:
d22540217a0bec35468e327c6b6df8041eee7fb1c79dd676cfa38935774b81bb

policy:
binary-sufficiency-v0.1.1

scope:
one semantic object vs explicitly cited evidence only

thinking:
disabled

temperature:
0.1
```

Canonical role remains in:

```text
50_SEMANTIC_EVIDENCE_AUDITOR_ROLE_AND_BOUNDARIES.md
```

---

# 5. Evidence policy for Round 1

Use:

```text
BASELINE_CITED_EVIDENCE_ONLY
```

Do NOT automatically inject Evidence Packet v0.1 citation-context or source-metadata augmentation in this broadening round.

Why?

Evidence Packet v0.1 currently has only partial RS02 development support:

```text
metadata can help metadata-dependent semantics
irrelevant metadata can destabilize Auditor judgment
same-container context did not resolve the tested workflow overreach
```

Those are development observations, not yet universal rules.

Promoting Packet v0.1 to the default before cross-source evidence would itself be an overfit.

Therefore Round 1 first measures the frozen baseline provenance edges produced by Sensor v0.2.2.

---

# 6. Source list — heterogeneous development broadening

Run these sources as one frozen round, in this order:

```text
RS11 — news/release-like article
RS05 — technical tutorial / methods
RS06 — long interview / mixed epistemic content
RS04 — healthy PDF / paper-like source
```

Why this order?

It deliberately expands genre complexity:

```text
news/release
   ↓
method/tutorial
   ↓
long mixed discourse
   ↓
PDF / paper-like source
```

The exact order is not a scoring variable. It is frozen mainly to preserve reproducibility and prevent cherry-picking.

Reserved sources remain protected:

```text
RS13 — RESERVED_UNCONSUMED
RS14 — RESERVED_UNCONSUMED
```

Do not touch them in this round.

---

# 7. Critical no-between-source-tuning rule

The four sources constitute **one development round**.

After beginning the round:

```text
DO NOT inspect RS11 and change the Sensor before RS05
DO NOT inspect RS05 and change the Auditor before RS06
DO NOT change evidence policy before RS04
DO NOT add a reason code because one early source is awkward
DO NOT insert lexical examples copied from a broadening source into prompts
```

If an actual instrumentation/implementation bug makes the run invalid:

```text
STOP
archive the round as INVALID
fix/version the instrumentation
restart or clearly separate the new measurement
```

Do not silently patch mid-round.

---

# 8. Predeclared Sensor observations

Use the same conceptual dimensions for every source:

```text
1. first-pass structural validity
2. repair usage
3. Event Frame count
4. Epistemic Unit count
5. semantic omission
6. semantic overreach
7. actor / time / scope fidelity
8. Event vs Epistemic decomposition
9. provenance traceability
10. provenance support sufficiency
11. context dependency
12. metadata dependency
```

Do not invent a special metric after seeing one source.

Counts are descriptive, not quality scores by themselves.

---

# 9. Predeclared Auditor observations

For real Sensor-produced edges inspect:

```text
1. first-pass structural validity
2. SUFFICIENT / INSUFFICIENT counts
3. reason-code distribution
4. likely false accepts
5. likely false rejects
6. repeated failure structures across sources
```

Important:

```text
SUFFICIENT count != Auditor accuracy
```

No Human Gold is attached to the first broadening audit pass.

The purpose is failure discovery and pattern comparison, not leaderboard scoring.

---

# 10. Evidence threshold for future mechanism changes

A future Sensor v0.2.3, Auditor v0.1.2, or selective Evidence Packet policy is NOT justified merely because one source exhibits a residual.

Prefer this chain:

```text
same causal pattern
observed across heterogeneous sources
      ↓
Human adjudication confirms the pattern
      ↓
controlled mechanism A/B
      ↓
regression on existing capabilities
      ↓
consider versioned redesign
```

Working rule:

> **Do not convert a local residual into a general mechanism until the residual repeats across materially different sources.**

---

# 11. Existing instruments — no new orchestration code

No new Sensor/Auditor runner is required.

Reuse:

```text
eval/live/run_semantic_evidence_dev_v0_2_2.py

eval/live/run_semantic_evidence_auditor_real_edges_v0_1_1.py
```

This is intentional Occam discipline:

> **If the existing instrument already measures the frozen question, do not create a new mechanism merely because the research phase has a new name.**

---

# 12. Exact next commands

## Step A — sync

```bash
git pull --rebase
```

## Step B — dry-run preflight

This checks source integrity and prompt/input size without calling the LLM:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_dev_v0_2_2.py \
  --source RS11 \
  --source RS05 \
  --source RS06 \
  --source RS04 \
  --as-of 2026-09-07 \
  --dry-run
```

The dry-run is instrumentation preflight, not source-result inspection, so it does not violate the no-between-source-tuning rule.

## Step C — frozen Sensor broadening run

If preflight is healthy, run all four sources in the same command:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_dev_v0_2_2.py \
  --source RS11 \
  --source RS05 \
  --source RS06 \
  --source RS04 \
  --as-of 2026-09-07
```

This writes one multi-source Sensor artifact.

Do not change the mechanism after an early source; the runner completes the selected list under one frozen invocation identity.

## Step D — baseline real-edge Auditor pass

Use the exact Sensor artifact path printed by Step C:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_real_edges_v0_1_1.py \
  --artifact <EXACT_MULTI_SOURCE_SENSOR_ARTIFACT_PATH>
```

Do not use Evidence Packet v0.1 augmentation in this Round 1 audit.

---

# 13. What to return for analysis

Preserve both artifacts:

```text
1. multi-source Semantic Sensor v0.2.2 artifact
2. multi-source Auditor v0.1.1 real-edge artifact
```

The first analysis should compare sources side by side rather than immediately editing prompts.

Questions:

```text
Which residuals are unique to one genre?
Which causal structures recur across two or more genres?
Which Auditor rejects look like genuine provenance gaps?
Which look like possible false rejects?
Does Event/Epistemic decomposition behave differently by genre?
Do metadata/context dependencies recur outside RS02?
```

Only after this comparison should Human adjudication select repeated patterns worth deeper controlled tests.

---

# 14. What NOT to conclude from this round

Do not claim:

```text
production readiness
fresh validation accuracy
Auditor accuracy from pass rate
universal Evidence Packet policy
universal context rule
universal metadata rule
```

All four sources are development data.

This is **generalization-oriented development broadening**, not final validation.

---

# 15. Current frontier

```text
RS02                                   SATURATED_DEVELOPMENT
Semantic Sensor v0.2.2                 FROZEN FOR BROADENING ROUND
Semantic Evidence Auditor v0.1.1       FROZEN FOR BROADENING ROUND
Evidence Packet v0.1                   NOT DEFAULT IN ROUND 1
Cross-source Round v0.1                PREREGISTERED / RUN PENDING
RS11 / RS05 / RS06 / RS04              DEVELOPMENT_ACTIVE
RS13 / RS14                            RESERVED_UNCONSUMED
Fresh validation evidence              NONE
```

---

# 16. Recovery compression

```text
Do not tune RS02 anymore.

Freeze:
Sensor v0.2.2
Auditor v0.1.1
Baseline cited evidence only

Broaden:
RS11 -> RS05 -> RS06 -> RS04
as one frozen development round.

Look for repeated causal patterns across genres.
Do not change mechanisms because of a single new source.

NEXT:
dry-run preflight -> one 4-source Sensor run -> one multi-source Auditor pass.
```

Core lesson:

> **Cross-source repetition earns the right to add complexity; a single awkward example does not.**
