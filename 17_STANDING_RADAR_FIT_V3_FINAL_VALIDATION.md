# Research Attention OS — Standing Radar Fit v3 Final Validation

Status: **MEASURED — PRE-REGISTERED FAIL / D SEMANTICS CLOSED / ESTIMATOR RESIDUALS ATTRIBUTED**  
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

Estimator/profile freeze commit:

```text
4c857260a146bcb2ca66bd7c600cd62d9be2a8c6
```

Only `standing_radar_fit` is scored. `substantive_anchors`, `matched_clauses`, and `reason` are diagnostics only.

Production scheduler / Attention Policy behavior remains unchanged.

---

## 3. What v3 changes

v3 does not add a new D variable. It formalizes D as Standing Attention Jurisdiction.

The estimator must:

1. interpret the stated event semantically;
2. identify substantive radar anchors;
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

The final fresh validation was authored only after the v3 prompt/profile/estimator were frozen, then labeled by the human before the model was run.

The first completed scored predictions on that frozen Human Gold are the official v3 measurement.

Do not modify the v3 prompt/profile after seeing the fresh predictions and then re-report the same set as fresh evidence.

---

## 5. Final fresh Human Gold — FROZEN

Artifact:

`eval/live/manifest.standing_radar_fit_v3_final_fresh_human_gold.yaml`

Human labels:

```text
FJ1  OUT
FJ2  OUT
FJ3  OUT
FJ4  IN
FJ5  OUT
FJ6  IN
FJ7  OUT
FJ8  IN
FJ9  OUT
FJ10 IN
```

Class balance:

```text
IN   4
OUT  6
N   10
```

The user's explicit evaluation preference for this final engineering check is that broad logical consistency matters more than cosmetic perfection; an isolated outlier should not trigger another D redesign. This does not change the pre-registered numeric criterion below. A repeated semantic failure mode still matters.

---

## 6. Pre-registered success criterion

```text
Exact accuracy >= 0.90
IN recall      >= 0.80
OUT recall     >= 0.80
Technical failures = 0 or clearly attributable without semantic fallback
No clear repeated Standing-Radar-Clause failure mode
```

At N=10, exact accuracy requires at least 9/10. With 4-IN / 6-OUT Human Gold, the recall thresholds require all 4 IN cases correct and at least 5/6 OUT cases correct.

This is a personal engineering validation, not a population benchmark.

---

## 7. Official first-run measurement — RECORDED

Artifact:

`eval/live/results/standing_radar_fit_v3_final_fresh_first_run.json`

Result commit:

```text
07ae4b3
```

Invocation:

```text
model               deepseek-v4-flash
thinking            disabled
temperature         0.1
prompt_sha256       c7ce0ed089fdcdfee69c9f986e35a860e7d6c07468801e76ad1af771a3d2ece7
technical failures  0
```

Observed:

```text
Exact accuracy       7/10 = 0.70
IN recall            2/4  = 0.50
OUT recall           5/6  = 0.8333333333
Balanced accuracy    0.6666666667
False-IN             1  (FJ2)
False-OUT            2  (FJ4, FJ6)
Technical failures   0
```

The final v3 estimator therefore **fails the pre-registered gate**. This result must not be relabeled as a pass.

### Reporting-plumbing note

The JSON artifact's embedded `success_criterion` block was inherited from the generic v1 metric helper and reports `exact>=0.8` / `balanced>=0.8`. That block is not the v3 pre-registration. The authoritative v3 criterion is the criterion frozen in this document and the final-validation manifest: `exact>=0.90`, `IN recall>=0.80`, `OUT recall>=0.80`, plus no repeated clause failure. The measurement fails under either rule, so this reporting mismatch does not affect the scientific conclusion. Preserve the first-run artifact unchanged.

---

## 8. Residual attribution

### 8.1 FJ2 — exact mismatch, but model IN is semantically acceptable under the frozen clause

```text
Gold OUT
Pred IN
```

The event explicitly develops a multimodal maintenance Agent. The frozen v3 profile explicitly says to monitor events where AI Agents / multimodal AI are substantively developed, released, evaluated, deployed, or changed.

The model's IN prediction is therefore a valid reading of the frozen Standing Radar Clause. Post-measurement human review explicitly accepted that reading as understandable and not a D-model error. Preserve the original Gold and first-run metric for provenance, but do **not** treat FJ2 as evidence that the clause semantics or estimator reasoning are wrong.

This case is a useful reminder that D only asks whether the event is inside the standing world. Whether a small industrial AI-Agent development is substantial enough to surface is a separate S question.

Do not retune the AI clause to this case.

### 8.2 FJ4 — D/S separation violation in estimator reasoning

```text
Gold IN
Pred OUT
```

The model explicitly recognized `OpenAI` as a substantive anchor, yet did not apply the standing clause:

```text
Monitor OpenAI and Google DeepMind when either organization is a substantive actor/object in the event, independent of the event's significance.
```

Its reason instead required a strategic/product/research/AI-system development consequence. That imports an S-like significance condition into D.

The intended decomposition is:

```text
OpenAI is the substantive actor   -> D = IN
routine administrative reshuffle -> likely S = NOT MATERIAL
D = IN and S = 0                 -> no-Delta AWARE gate can still DROP when P is also low
```

So the model's extra `OpenAI AND SignificantDevelopment` condition is precisely the kind of cross-variable leakage D/S/P are designed to prevent.

This is a real estimator calibration / instruction-following error, not a flaw in Standing Attention Jurisdiction.

### 8.3 FJ6 — affiliation-clause instruction-following failure

```text
Gold IN
Pred OUT
```

The event explicitly states that the hospital is where the user's parent works. The frozen profile contains a direct-family-affiliation clause for a substantively involved institution.

The model nevertheless said the hospital was not monitored and omitted the stable affiliation from its matched-clause reasoning.

This is best treated as a clause execution / instruction-following failure in the current LLM estimator. It does not challenge the formal D model.

### 8.4 What the pattern means

FJ8 and FJ10 show that non-domain clauses can work: the model correctly applied hometown/local-governance and film-work clauses. Therefore the failure is not simply "only topic clauses work."

The narrower implementation issue is that the current LLM procedure does not reliably apply every heterogeneous Standing Radar Clause even when the clause is explicit. In particular, the intermediate `substantive anchor -> clause match` framing can over-constrain the more general formal model.

The formal definition is:

$$
\boxed{
D(E,u)=1
\iff
\exists\rho_i\in\mathcal R_u:\rho_i(Sem(E),u)=1
}
$$

A cleaner implementation view is therefore:

$$
\boxed{
Sem(E),u
\rightarrow
Evaluate(\rho_1,\rho_2,\ldots,\rho_n)
\rightarrow
OR
\rightarrow
D
}
$$

rather than making `AnchorExtraction` a mandatory semantic gate before clause evaluation.

This is an implementation observation, not a reason to add domain weights, a typed ontology, or new D sub-variables.

---

## 9. Research decision

Separate the semantic result from the current estimator score:

```text
D intuitive meaning                     SUPPORTED
Standing Attention Jurisdiction model   FROZEN / CLOSED SEMANTIC BASELINE
Standing Radar Clause representation    SUPPORTED
Domain weights / giant ontology         NOT JUSTIFIED
v3 first fresh estimator measurement    FAIL (0.70 exact, preserved)
FJ2 mismatch                             SEMANTICALLY ACCEPTABLE UNDER FROZEN CLAUSE
FJ4 / FJ6 residuals                     ATTRIBUTABLE IMPLEMENTATION ERRORS
```

The 0.70 first-run result remains the official measurement and is not rewritten. However, post-measurement attribution does not force a redesign of D itself. FJ4 and FJ6 are traceable failures to execute explicit frozen clauses; FJ2 is accepted as a reasonable IN under the frozen AI-Agent clause.

Given the project objective and the explicit preference not to keep expanding D for bounded residuals, **close D semantic research for Phase II-B and move to S**. Keep the estimator residuals as known implementation debt to revisit during integrated dogfooding or when a real-world repeated error pattern appears.

Do not create another synthetic D benchmark now.

---

## 10. Current pointer

```text
D semantic definition                  CLOSED / FROZEN
D historical measurements              PRESERVED
D v3 estimator                         NOT CERTIFIED; KNOWN ATTRIBUTABLE RESIDUALS
Further offline D benchmark expansion  STOP
S = Material Consequence               NOW
P = Public Attention Salience           AFTER S
```
