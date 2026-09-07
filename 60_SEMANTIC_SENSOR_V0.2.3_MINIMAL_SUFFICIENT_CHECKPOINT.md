# Semantic Sensor v0.2.3 — Minimal Sufficient Representation Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / RUN PENDING**  
Date: 2026-09-08

> Recovery purpose: resume from the representation-budget attribution without returning to Auditor tuning or max-token expansion.

---

# 1. Closed attribution entering this checkpoint

Text-first transport diagnostics established:

```text
RS11  completion_tokens = 7605   finish_reason = stop
RS05  completion_tokens = 8192   finish_reason = length
RS06  completion_tokens = 7097   finish_reason = stop
RS12  completion_tokens = 8192   finish_reason = length
```

Therefore:

```text
provider completion ceiling        ATTRIBUTED
8192-token truncation              CONFIRMED
Sensor representation budget      REPRODUCED / OPEN
PDF                                DEFERRED
Auditor strictness                 NOT CAUSAL FOR CURRENT FAILURE
```

Do not reopen PDF parsing or Auditor policy while measuring this candidate.

---

# 2. Scientific question

> **Can the Semantic Sensor say materially less without knowing materially less?**

Formal target:

$$
\boxed{
Minimal\ Redundancy
\quad subject\ to\quad
Semantic\ Sufficiency + Auditability + Bounded\ Output
}
$$

Canonical active-study document:

```text
59_SEMANTIC_SENSOR_MINIMAL_SUFFICIENT_REPRESENTATION.md
```

---

# 3. Candidate

Extractor:

```text
eval/live/semantic_evidence_extractor_v0_2_3.py
```

Version:

```text
semantic-evidence-extractor-v0.2.3
semantic-evidence-extraction-v0.2.3-minimal-sufficient
```

Controlled changes over v0.2.2:

```text
SemanticExtractionBatchV0_2 structure      unchanged
EventFrame v0.1 structure                  unchanged
temporal anchoring                         unchanged
evidence sufficiency discipline            unchanged
model / thinking / temperature             unchanged

changed:
semantic compression policy
bounded representation discipline
```

Experimental guardrails:

```text
non_event_units preferred 6..10 when sufficient
non_event_units hard policy cap 12
supports per non-event unit hard cap 4
normally 1..2 supports
minimal sufficient excerpts
```

Primary semantic rule:

> **If deleting the unit does not remove an independent meaning, merge it.**

---

# 4. Preregistration

Machine-readable manifest:

```text
eval/live/manifest.semantic_sensor_minimal_sufficient_v0_1.yaml
```

Frozen development sources:

```text
RS11
RS05
RS06
RS12
```

RS13 / RS14 remain RESERVED_UNCONSUMED.

Do not change v0.2.3 after seeing an early source and continue the same round.

---

# 5. Implementation commits

Concept / study definition:

```text
267514a11b08a4a50d4a3a7def7b7625aaeffbde
docs: define minimal sufficient semantic representation study
```

Extractor:

```text
85654941fce13557f9fa974019fc9ff74e56e382
feat: add minimal sufficient semantic extractor v0.2.3
```

Preregistration manifest:

```text
1dececc74e94a343af20145274e8bd026cbbdcbe
eval: preregister minimal sufficient sensor study
```

Runner:

```text
c82caf943882e5705a6bdbe7a031d7ec68f08195
feat: add minimal sufficient sensor development runner
```

Focused tests:

```text
faeaa88f8a61b392c2e56466015b424e3d96373c
test: cover minimal sufficient semantic extractor v0.2.3
```

---

# 6. Predeclared measurements

Transport / representation:

```text
n_scorable
n_first_pass_valid
repair_used
completion_tokens
n_event_frames
n_non_event_units
n_non_event_supports
statement_chars
support_excerpt_chars
```

Preferred engineering region:

```text
~6000 completion tokens or less
```

This is headroom below the observed 8192 ceiling, not a semantic pass criterion.

Semantic sufficiency must also be inspected for:

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

Shortness without semantic sufficiency is failure.

---

# 7. Exact next commands

Sync:

```bash
git pull --rebase
```

Focused tests:

```bash
cd backend
.venv/bin/pytest \
  tests/eval/test_semantic_evidence_extractor_v0_2_3.py -q
cd ..
```

Optional dry-run:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_dev_v0_2_3.py \
  --preregistered-round \
  --as-of 2026-09-07 \
  --dry-run
```

Formal development run:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_dev_v0_2_3.py \
  --preregistered-round \
  --as-of 2026-09-07
```

Return the generated artifact for Human Semantic Sufficiency inspection.

Do NOT run Auditor first. Sensor representation quality is the current bottleneck.

---

# 8. First analysis after the run

First inspect transport/representation outcome:

```text
Did RS05 and RS12 stop truncating?
How much did RS11 / RS06 completion tokens fall?
How many units/supports were produced?
Did first-pass validity remain intact?
```

Then inspect semantic sufficiency source by source with the SAME dimensions.

Do not immediately add another compression rule because one source is awkward.

---

# 9. What is NOT being tested yet

```text
Auditor strictness
Auditor pass rate
D / S / P
Delta
Attention Policy
end-to-end user utility
fresh validation
syntactic/serialization compression
higher provider max_tokens
```

Those remain downstream or deferred.

---

# 10. Recovery compression

```text
Current bottleneck:
Sensor output is too verbose; two of four text sources hit 8192 completion tokens.

Do NOT solve by raising max_tokens first.
Do NOT loosen Auditor to solve an upstream Sensor transport failure.

Candidate v0.2.3 keeps the same semantic schema and changes only semantic compression:
independent meanings stay separate; examples/details sharing one predicate merge.

NEXT:
run focused tests -> run RS11/05/06/12 unchanged -> inspect token reduction AND Human Semantic Sufficiency.
```

Core phrase:

> **First make the Sensor say less without knowing less.**
