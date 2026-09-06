# Research Attention OS — Material Consequence v1 Final Validation

Status: **HUMAN GOLD FROZEN / FIRST SCORED RUN NEXT**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Semantic baseline: `18_MATERIAL_CONSEQUENCE_STUDY.md`, `19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md`  
Estimator baseline: `20_MATERIAL_CONSEQUENCE_ESTIMATOR_V1.md`

---

## 1. Frozen estimator

Version identifiers:

```text
estimator_version  material-consequence-estimator-v1
prompt_version     material-consequence-v1
profile_id         material-consequence-profile-v1
prompt_sha256      f46808899f1b1cb2c4bfb106c6e537d65ca4433428cea8494f4eedbfccf9b776
```

Freeze declaration commit:

```text
99b8c96e54102c3befd04d931156645a5b77d8e1
```

Targeted validation before freeze:

```text
9 passed, 1 unrelated Starlette/httpx deprecation warning
10-case dry-run completed
```

No scored S model measurement had been run before the fresh validation set was authored or before Human Gold was frozen.

---

## 2. Fresh validation provenance

Fresh template:

`eval/live/manifest.material_consequence_final_fresh_validation.v1.template.yaml`

Template commit:

```text
51f983d0a2aeaa2a5eb730fa913657b0e127925b
```

The template was created only after estimator/profile freeze and before Human Gold labels or model predictions were seen.

Historical development/calibration cases are excluded from fresh reporting:

```text
MC1-MC10
MS1-MS10
```

---

## 3. Frozen fresh Human Gold

Human Gold manifest:

`eval/live/manifest.material_consequence_final_fresh_human_gold.v1.yaml`

Human Gold freeze commit:

```text
cbd41ca62c0b3ed5d0fdba07fd77515d63e48c8a
```

Label provenance:

```text
HUMAN_ELICITED
```

The labels were elicited after the fresh template and estimator were frozen and before any scored model prediction on SF1-SF12.

Frozen labels:

```text
SF1   NOT_MATERIAL
SF2   MATERIAL
SF3   NOT_MATERIAL
SF4   MATERIAL
SF5   NOT_MATERIAL
SF6   MATERIAL
SF7   NOT_MATERIAL
SF8   MATERIAL
SF9   NOT_MATERIAL
SF10  MATERIAL
SF11  NOT_MATERIAL
SF12  MATERIAL
```

Observed class balance after elicitation:

```text
MATERIAL       6
NOT_MATERIAL   6
```

This balance was not assumed when the success criterion was pre-registered.

---

## 4. What the fresh set probes

The 12-case set uses six controlled contrasts across different consequence forms:

```text
SF1/SF2   huge reach with trivial change vs national public-system failure
SF3/SF4   large private gain vs sector-wide practice change
SF5/SF6   bounded local public-system failure vs shared national-system failure
SF7/SF8   famous private actor event vs binding national authority/rule change
SF9/SF10  niche cultural success vs broad cultural/industry state change
SF11/SF12 isolated scientific claim vs accepted knowledge + engineering change
```

The cases intentionally do not state whether media covered or discussed the event. Public attention is P and must not leak into S.

---

## 5. Pre-registered success criterion

```text
Exact accuracy            >= 10/12 = 0.8333333333
MATERIAL recall           >= 0.80
NOT_MATERIAL recall       >= 0.80
Technical failures        = 0
No clear repeated semantic failure mode
```

The exact class balance was not assumed before Human Gold was elicited. Recall thresholds are computed against the frozen Human labels.

This is a personal engineering validation, not a population benchmark.

---

## 6. Measurement rule

Sequence is strict:

```text
fresh template frozen
  -> Human labels elicited
  -> Human Gold manifest frozen
  -> run unchanged estimator exactly once
  -> preserve write-once first-run artifact
  -> attribute residuals before any estimator change
```

Do not modify prompt/profile/estimator after seeing Human Gold and then report this same set as fresh performance. Any such change requires a new estimator version and new fresh set.

The expected first-run artifact remains:

`eval/live/results/material_consequence_v1_final_fresh_first_run.json`

At Human Gold freeze time this artifact did not exist.

---

## 7. Closure rule

If v1 meets the pre-registered gate without a repeated semantic failure:

$$
\boxed{S\ estimator\ v1=ACCEPTED\ for\ Phase\ II\text{-}B}
$$

Then move to P rather than expanding S into a large benchmark.

If it misses only isolated attributable cases, preserve the result and make an engineering judgment consistent with the Phase-II objective. If it fails systematically, attribute the smallest failure before changing representation.

---

## 8. Current pointer

```text
S semantic contract             FROZEN
S estimator v1                  FROZEN
Fresh S template                FROZEN
Fresh S Human Gold              FROZEN
Human Gold commit               cbd41ca62c0b3ed5d0fdba07fd77515d63e48c8a
First scored S measurement      NEXT / NOT RUN
P study                         AFTER S
```
