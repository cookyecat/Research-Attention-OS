# Integrated no-Delta AWARE — Round-2 Human Adjudication

Status: **POST-HOC ADJUDICATION / NOT FRESH VALIDATION**  
Date: 2026-09-07  
Source first-run artifact: `eval/live/results/no_delta_awareness_integration_v1_fresh_first_run.json`  
Raw round-2 labels: `eval/live/manifest.no_delta_aware_integrated_human_gold.round2_raw.yaml`

> Purpose: distinguish Human label drift / definition recall errors from estimator or policy errors without re-running the model. The original first-run predictions remain frozen; round-2 labels are used only to re-score and adjudicate the already-observed predictions.

---

## 1. Methodological status

Round-2 labels were supplied after the annotator had already seen the first integrated predictions. Therefore they are not blinded fresh Human Gold and must not replace the historical first-run record.

Correct procedure:

```text
frozen first-run predictions
        +
post-hoc Human adjudication
        ↓
re-score / attribution
```

Do **not** re-call the model merely because labels changed. A second model call would mix Human-label correction with stochastic model variation.

---

## 2. Raw round-2 labels — literal re-score

Using the round-2 list exactly as supplied:

```text
D      11/12 = 0.9166666667
       IN recall  = 4/5 = 0.80
       OUT recall = 7/7 = 1.00
       mismatch   = IA9

S      11/12 = 0.9166666667
       MATERIAL recall     = 5/5 = 1.00
       NOT_MATERIAL recall = 6/7 = 0.8571428571
       mismatch            = IA8

P      10/10 = 1.00 on scorable cases
       SALIENT recall     = 5/5 = 1.00
       NOT_SALIENT recall = 5/5 = 1.00
       IA7 / IA11 remain insufficient_evidence

Final  10/10 = 1.00 under original v1 all-components-required integration
```

Human component labels -> frozen gate consistency:

```text
11/12
mismatch = IA8 only
```

This is a major change from the original Human Gold and shows that much of the apparent first-run error came from Human annotation drift rather than downstream policy failure.

---

## 3. Two round-2 adjudication tensions

### 3.1 IA9 — prose says OUT, raw list says IN

The annotator explicitly clarified:

> trivial internal OpenAI catering is not worth monitoring.

That semantic intent corresponds to:

```text
IA9 D = OUT
```

The raw list nevertheless contains `D=IN`. Treat this as a prose/list transcription tension, not estimator evidence.

If IA9 is adjudicated to `D=OUT`, D becomes:

```text
12/12
IN recall  = 4/4 = 1.00
OUT recall = 8/8 = 1.00
```

This removes all D errors on the integrated IA set.

### 3.2 IA8 — raw S conflicts with frozen S semantics and frozen gate

Raw round-2 label:

```text
D = IN
S = NOT_MATERIAL
P = SALIENT
Final = AWARE
```

But frozen gate gives:

```text
NOT_MATERIAL AND (IN OR SALIENT) = DROP
```

The case text explicitly states that the new foundation model independently and reproducibly reduces long-horizon tool-use cost, improves success rate, and moves the capability/cost frontier. Under frozen S semantics, this strongly matches a material disturbance to a shared technical capability frontier.

Therefore `IA8 S=NOT_MATERIAL` is a remaining adjudication tension. Do not silently rewrite it, but do not treat it as evidence against S or the gate either.

If IA8 is adjudicated to `S=MATERIAL`, then S also becomes 12/12 and Human component labels become 12/12 consistent with the frozen gate.

---

## 4. Partial determinacy correction

Integration v1 required D/S/P all to be scorable before producing Final. This was stricter than the frozen Boolean policy.

Under v1.1 partial determinacy:

```text
IA7: D=IN, S=MATERIAL, P=UNKNOWN
     => AWARE regardless of P

IA11: D=OUT, S=MATERIAL, P=UNKNOWN
      => unresolved because Final depends on P
```

Therefore with the same frozen first-run component predictions, 11 cases have a logically determined Final rather than 10.

Against the round-2 Final labels:

```text
v1.1 determined Final = 11/11 correct
IA11 remains legitimately unresolved
```

No model re-run is involved.

---

## 5. Revised interpretation of the first integrated run

The original aggregate `final accuracy = 0.70` should not be read as evidence that the frozen policy is wrong.

After Human adjudication:

```text
S estimator:       no observed semantic error except IA8 label tension
P estimator:       10/10 where observable
D estimator:       raw round-2 11/12; likely 12/12 after IA9 prose/list correction
Final policy:      10/10 under v1 on scorable cases
Final policy v1.1: 11/11 on logically determined cases
Wiring mismatch:   0
```

The dominant remaining product uncertainty is increasingly upstream:

```text
raw information
    ↓
semantic evidence extraction / sensing
    ↓
D / S / P state estimation
    ↓
frozen AWARE policy
```

---

## 6. Research decision

```text
Original first-run artifact                  PRESERVE
Original v1 Human Gold                       PRESERVE
Round-2 labels                               POST-HOC ADJUDICATION ONLY
Re-run model solely because Gold changed     DO NOT DO
Re-score frozen predictions                  YES
Frozen AWARE gate                            UNCHANGED
Partial-determinacy integration              SUPPORTED
Next major work                              SEMANTIC EVIDENCE EXTRACTION FRONT-END
```

Do not report round-2 rescoring as a new fresh accuracy number. It is an adjudication result showing that the first integrated run was substantially confounded by Human label drift / forgotten component definitions.
