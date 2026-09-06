# Research Attention OS — Material Consequence Estimator v1

Status: **FROZEN — FRESH HUMAN GOLD NEXT**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Semantic baseline: `18_MATERIAL_CONSEQUENCE_STUDY.md`, `19_MATERIAL_CONSEQUENCE_REFERENCE_SCALE.md`

---

## 1. Objective

Implement the first eval-only estimator for:

$$
\boxed{S=Material\ Consequence}
$$

using the calibrated semantic contract:

> **S asks whether the event itself causes a material disturbance to at least one consequential shared reference system, independent of user interest and public attention.**

The estimator is intentionally direct. It does not introduce domain weights, an ontology, an ordinal S scale, or mandatory intermediate gates.

---

## 2. Implementation artifacts

Profile:

`eval/live/material_consequence_profile.v1.yaml`

Estimator:

`eval/live/material_consequence_v1.py`

Runner:

`eval/live/run_material_consequence_v1_eval.py`

Tests:

`backend/tests/eval/test_material_consequence_v1.py`

Version identifiers:

```text
estimator_version  material-consequence-estimator-v1
prompt_version     material-consequence-v1
profile_id         material-consequence-profile-v1
prompt_sha256      f46808899f1b1cb2c4bfb106c6e537d65ca4433428cea8494f4eedbfccf9b776
```

Production scheduler / Attention Policy behavior is unchanged.

---

## 3. Direct semantic model

The implementation deliberately evaluates S directly over event semantics:

$$
\boxed{
Sem(E)
\rightarrow
MaterialConsequence(E)
}
$$

Diagnostics such as `affected_shared_systems` and `material_changes` are explanatory only.

They are **not** mandatory intermediate gates.

This is an explicit lesson carried forward from the D study: a useful diagnostic decomposition must not become a hidden extra applicability condition.

---

## 4. Frozen semantic content encoded in the profile

The profile encodes these core principles:

- `UserInterest != S`
- `PublicAttention != S`
- `MediaCoverage != S`
- `ActorProminence != S`
- `PopulationCount != S`
- `LargeLocalRelativeEffect != S`
- `LargePrivateGain != S`
- local origin is allowed when the event actually disturbs a consequential shared system
- a narrow niche can be material when the whole relevant industry / field / rule system changes
- changes in control or option structure of a consequential shared system can themselves be material
- judge only stated consequences; do not invent plausible downstream effects

Examples of consequential shared reference systems are included only as semantic guidance: national governance, public systems, industries/fields, markets, accepted scientific knowledge, capability frontiers, and broadly shared cultural states.

These examples are not a typed ontology.

---

## 5. Output contract

The model returns:

```json
{
  "material_consequence": "MATERIAL | NOT_MATERIAL",
  "affected_shared_systems": [],
  "material_changes": [],
  "reason": "..."
}
```

Only:

`material_consequence`

is scored.

On transport/model/schema failure the estimator fails closed and never invents a label.

---

## 6. Measurement plumbing

The dedicated S metric path reports:

```text
exact_accuracy
material_recall
not_material_recall
balanced_accuracy
false_material_count
false_not_material_count
```

It intentionally does **not** embed a success criterion inside the generic metric helper.

The fresh S validation criterion is pre-registered separately after the estimator/profile freeze, avoiding the D v3 reporting-plumbing mismatch.

The first scored artifact is write-once.

---

## 7. Freeze evidence

Targeted unit test executed after implementation:

```text
backend/.venv/bin/python -m pytest \
  backend/tests/eval/test_material_consequence_v1.py -q

9 passed, 1 warning in 0.04s
```

The warning is an unrelated Starlette/httpx deprecation warning and does not affect estimator semantics or measurement.

Dry-run against the calibration-v2 Human manifest:

```text
n_cases       10
prompt_sha256 f46808899f1b1cb2c4bfb106c6e537d65ca4433428cea8494f4eedbfccf9b776
```

No model measurement was run during this freeze check.

From this point forward, the v1 prompt/profile/estimator are treated as frozen for the first fresh S validation. Any later change after Human Gold or model predictions are seen requires a new estimator version and a new fresh validation set.

---

## 8. Provenance

The following are development/calibration evidence only and must never be reported as fresh S performance:

```text
MC1-MC10
MS1-MS10
```

No calibration case IDs or case-specific examples are copied into the estimator prompt/profile.

Sequence from this freeze point:

```text
frozen estimator/profile
  -> author fresh S validation
  -> Human Gold before model run
  -> first scored measurement
  -> residual attribution
```

---

## 9. Current pointer

```text
S semantic contract              FROZEN
S estimator v1                   FROZEN
S unit tests                     PASS (9/9)
Fresh S holdout                  NEXT
S Human Gold                     NOT YET ELICITED
S first scored measurement       NOT RUN
P study                          AFTER S
```
