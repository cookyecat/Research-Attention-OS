# Auditor Packet Component / Stability Study — Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / RUN PENDING**  
Date: 2026-09-07

> Recovery purpose: resume here after the first Evidence Packet v0.1 A/B. Do not modify Auditor v0.1.1 until the component/stability residual is attributed.

---

# 1. Why this study exists

The first Packet v0.1 A/B on 17 real RS02 edges produced:

```text
INSUFFICIENT -> INSUFFICIENT   4
INSUFFICIENT -> SUFFICIENT     1
SUFFICIENT   -> INSUFFICIENT   1
SUFFICIENT   -> SUFFICIENT    11
```

The expected positive recovery occurred on the metadata-dependent temporal uncertainty edge.

Three known provenance defects remained blocked.

But one obvious positive control (PR-count action) unexpectedly flipped from SUFFICIENT to INSUFFICIENT after only irrelevant source metadata was added.

Therefore a new open question exists:

```text
Audit Stability / Irrelevant-Evidence Invariance
```

Do not attribute this from one stochastic LLM call.

---

# 2. Important logical invariant under test

Evidence sufficiency is directional:

$$
Evidence \Rightarrow SemanticObject
$$

It is not an equivalence requirement:

$$
SemanticObject \not\equiv Evidence
$$

If evidence contains extra information that the semantic object does not repeat, that alone should not make a supported object insufficient.

Working stability expectation:

> Adding irrelevant, non-contradictory evidence should not systematically flip a genuinely supported edge to INSUFFICIENT.

This is not yet declared a frozen theoretical law; it is the engineering property being tested.

---

# 3. Occam scope

Do NOT run a full 17-edge × 4-condition matrix.

Use only three diagnostic real edges.

## Case A — positive PR-count control

```text
audit_id:
RS02:evt-rs02-001:action_change:1

conditions:
BASELINE
METADATA_ONLY
```

Question:

> Does irrelevant metadata reproducibly induce a false reject?

## Case B — temporal uncertainty

```text
audit_id:
RS02:evt-rs02-001:uncertainty:1

conditions:
BASELINE
METADATA_ONLY
```

Question:

> Does the useful metadata-driven recovery reproduce?

## Case C — workflow discourse context

```text
audit_id:
RS02:non_event_unit:neu-rs02-005

conditions:
BASELINE
CONTEXT_ONLY
```

Question:

> Does full same-pointer PARA 0006 context reproducibly change the verdict?

---

# 4. Repetition design

Default:

```text
repeats = 3 per condition
```

Total calls:

```text
3 cases × 2 conditions × 3 repeats = 18
```

This is enough to distinguish a one-off flip from a repeated directional effect without creating a large experiment matrix.

No Human Gold accuracy claim is attached.

---

# 5. Fixed variables

```text
Sensor artifact       fixed
semantic objects      fixed
Auditor v0.1.1        fixed
Auditor prompt        fixed
model configuration   fixed
```

Changed only:

```text
BASELINE
vs
METADATA_ONLY
or
CONTEXT_ONLY
```

No adjacent retrieval. No repair. No source search.

---

# 6. Implementation

Runner:

```text
eval/live/run_semantic_evidence_auditor_component_stability_v0_1.py
```

Commit:

```text
4116670f2cf386f680510361c85c9b23912fccc5
feat: add auditor packet component stability study
```

Focused tests:

```text
backend/tests/eval/test_semantic_evidence_auditor_component_stability_v0_1.py
```

Commit:

```text
51a4063ac4c1132a5345c1fe979c71632ed7f70b
test: cover auditor packet component stability study
```

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
  tests/eval/test_semantic_evidence_auditor_v0_1_1.py \
  tests/eval/test_semantic_evidence_packet_v0_1.py \
  tests/eval/test_semantic_evidence_auditor_component_stability_v0_1.py -q
cd ..
```

Run study:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_component_stability_v0_1.py \
  --sensor-artifact eval/live/results/semantic_evidence_dev_v0_2_2/semantic_evidence_dev_v0_2_2_20260907T103010Z.json \
  --repeats 3
```

---

# 8. How to interpret the next result

## PR-count positive control

If:

```text
BASELINE       mostly SUFFICIENT
METADATA_ONLY  mostly SUFFICIENT
```

then the prior flip was likely stochastic/noise.

If:

```text
BASELINE       mostly SUFFICIENT
METADATA_ONLY  repeatedly INSUFFICIENT
```

then irrelevant metadata is systematically perturbing Auditor judgment. Packet should become more selective.

## Temporal uncertainty

If:

```text
BASELINE       mostly INSUFFICIENT
METADATA_ONLY  mostly SUFFICIENT
```

then metadata utility is reproducibly supported.

## Workflow discourse context

If:

```text
BASELINE       mostly INSUFFICIENT
CONTEXT_ONLY   mostly SUFFICIENT
```

then same-container discourse context has reproducible value.

If both remain INSUFFICIENT, human adjudication should determine whether the Sensor semantic object is mildly overstrong or the Auditor is too conservative.

---

# 9. Current frontier

```text
Semantic Sensor v0.2.2                  DEVELOPMENT / PARTIAL PASS
Semantic Evidence Auditor v0.1.1        ROLE SUPPORTED / STABILITY RESIDUAL OPEN
Evidence Packet v0.1                    PARTIAL SUPPORT
Metadata-dependent evidence utility     OBSERVED ONCE
Same-container context utility          NOT YET DEMONSTRATED
Irrelevant-evidence stability           OPEN
Automatic retrieval/repair              NOT IMPLEMENTED
Fresh validation evidence               NONE
```

---

# 10. Recovery compression

```text
Packet v0.1 successfully rescued the metadata-dependent temporal edge
without leaking adjacent provenance into known bad edges.

But one obvious positive control flipped to INSUFFICIENT after irrelevant metadata.
Do not modify Auditor yet.

NEXT:
repeat only three diagnostic edges under isolated packet components.
```
