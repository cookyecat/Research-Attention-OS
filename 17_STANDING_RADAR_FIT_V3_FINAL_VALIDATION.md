# Research Attention OS — Standing Radar Fit v3 Final Validation

Status: **ESTIMATOR FROZEN / HUMAN GOLD NEXT**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Semantic baseline: `16_STANDING_ATTENTION_JURISDICTION.md`

---

## 1. Research question

Can a compact natural-language Standing Radar Clause profile estimate D well enough across heterogeneous standing-attention anchors without domain weights or a typed ontology?

$$
\boxed{
D(E,u)=\mathbf 1[E\in\mathcal J_u]
}
$$

with:

$$
\boxed{
\mathcal J_u
=
\{E\mid\exists\rho_i\in\mathcal R_u,\rho_i(Sem(E),u)=1\}
}
$$

Engineering hypothesis:

$$
\boxed{
EventText + StandingRadarClauses
\rightarrow
\hat D
}
$$

---

## 2. Frozen estimator

Profile:

`eval/live/standing_radar_profile.v3.yaml`

Estimator:

`eval/live/standing_radar_fit_v3.py`

Runner:

`eval/live/run_standing_radar_fit_v3_eval.py`

Version identifiers:

```text
estimator_version  standing-radar-fit-estimator-v3
prompt_version     standing-radar-fit-v3
profile_id         standing-radar-profile-v3
```

Only `standing_radar_fit` is scored. `substantive_anchors`, `matched_clauses`, and `reason` are diagnostics only.

Production scheduler / Attention Policy behavior remains unchanged.

---

## 3. What v3 changes

v3 does not add a new D variable. It formalizes D as Standing Attention Jurisdiction.

The estimator must:

1. interpret the stated event semantically;
2. identify all substantive radar anchors;
3. preserve multiple anchors instead of forcing one dominant domain;
4. distinguish substantive involvement from incidental mention/tool use/context;
5. evaluate the event against stable Standing Radar Clauses;
6. return IN if at least one clause is genuinely satisfied;
7. treat exclusions/scope guards as anti-overmatching guards, not vetoes.

A clause may be expressed over a topic, actor/entity/person, work/product, place/governance scope, or stable affiliation. These are semantic forms, not ontology classes.

---

## 4. Provenance constraints

Historical sets are development evidence only for v3:

```text
FD1-FD20
IX1-IX8
RV1-RV8
FV1-FV8
BC1-BC6
```

Do not report any of them as fresh v3 performance.

The final fresh validation must be authored only after the v3 prompt/profile/estimator are frozen, then labeled by the human before the model is run.

The first completed scored predictions on that frozen Human Gold are the official v3 measurement.

Do not modify the v3 prompt/profile after seeing the fresh predictions and then re-report the same set as fresh evidence.

---

## 5. Final-validation scope

Keep the validation small. It should probe whether the same clause mechanism generalizes across multiple semantic forms, including:

- substantive monitored topic versus incidental tool/context;
- monitored organization as substantive actor versus incidental mention;
- stable direct affiliation versus socially adjacent but non-standing relation;
- standing place/governance scope versus unrelated place;
- monitored work/content versus unmonitored production workflow.

This is not a benchmark-expansion project. The purpose is to test the unified applicability model, not to enumerate ontology types.

---

## 6. Pre-registered success criterion

For the final small balanced validation:

```text
Exact accuracy >= 0.90
IN recall      >= 0.80
OUT recall     >= 0.80
Technical failures = 0 or clearly attributable without semantic fallback
No clear repeated Standing-Radar-Clause failure mode
```

If N=10, this means at least 9/10 exact with at least 4/5 recall on both classes.

This is a personal engineering validation, not a population benchmark.

---

## 7. Closure rule

If v3 passes the fresh final validation without a new systematic residual:

$$
\boxed{D\ study=CLOSED\ for\ Phase\ II\text{-}B}
$$

Then immediately move to S.

Do not continue polishing D for cosmetic 100% performance.

If v3 fails systematically, preserve the first-run result and attribute the smallest remaining failure. Do not introduce domain weights or a large ontology without evidence forcing that step.
