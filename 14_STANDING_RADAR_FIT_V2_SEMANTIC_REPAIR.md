# Research Attention OS — Standing Radar Fit v2 Semantic Repair

Status: **REPAIR CALIBRATED / FRESH HUMAN VALIDATION NEXT**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Historical baseline: `12_STANDING_RADAR_FIT_ESTIMATOR_STUDY.md`

---

## 1. Why v2 exists

The v1 D estimator showed strong core performance but failed the narrow intersection diagnostic:

```text
FD holdout: 0.90 exact / 0.933 balanced
Intersection diagnostic: 6/8 exact
Positive-intersection recall: 2/4
```

The diagnostic exposed a narrow semantic-composition problem: multi-facet events can be collapsed into one dominant domain. It also suggested that Standing Radar scope wording matters at event-role granularity.

The repair remains semantic and minimal. It does not introduce domain weights, a domain ontology, or a new attention variable.

---

## 2. Repaired semantic model

Candidate representation:

$$
\boxed{E\rightarrow F_s(E)=\{substantive\ semantic\ facets\}}
$$

Decision rule:

$$
\boxed{D(E)=IN\iff\exists f\in F_s(E):Match(f,StandingRadarScope)}
$$

An event may have multiple substantive facets. Do not force a single dominant domain.

A substantive facet is not a bare keyword. It must preserve what the event is actually about and the role the topic plays in the event. Incidental tools, implementation details, organizational context, or application setting do not become standing-interest matches merely by appearing.

---

## 3. Exclusion semantics

Standing exclusions are **scope guards**, not negative votes and not vetoes.

They constrain inherited or over-broad matching. They do not cancel an independently valid substantive standing-interest match.

$$
\boxed{
Exclusion\ constrains\ over\text{-}broad\ matching;
\quad Exclusion\ does\ not\ veto\ a\ genuine\ substantive\ match.
}
$$

This preserves:

$$
Using\ AI\ method\neq Being\ an\ AI\ event
$$

while allowing genuine robotics / AI / compute / other monitored facets to remain visible inside an otherwise excluded application domain.

---

## 4. RV scope calibration — BEFORE v2 measurement

The first v2 draft was written before RV1-RV8 were human-labeled. The model was **not** run on RV1-RV8.

Human labels:

```text
RV1 OUT
RV2 IN
RV3 OUT
RV4 OUT
RV5 OUT
RV6 IN
RV7 OUT
RV8 IN
```

Because RV4 corrected the profile scope, RV1-RV8 are now **calibration/development evidence**, not fresh holdout evidence.

Calibration artifact:

`eval/live/manifest.standing_radar_fit_v2_scope_calibration.yaml`

The important distinction is:

- RV2: an industrial company **develops** an autonomous inspection robot -> robotics itself is a monitored development -> IN.
- RV6: a satellite operator **develops** a multimodal AI Agent -> AI Agent itself is a monitored development -> IN.
- RV8: a studio **releases** a film -> the monitored artifact itself is the event -> IN.
- RV4: a hospital merely **introduces / uses** a cancer-treatment device in local practice -> the user does not monitor routine dynamics of an individual hospital as such -> OUT.

This does **not** create a universal rule that adoption is always OUT. It shows that Standing Radar scope is profile-specific and event-role-sensitive.

---

## 5. Standing Radar profile v2 — calibrated scope

Artifact:

`eval/live/standing_radar_profile.v2.yaml`

Historical v1 remains frozen.

Cancer/tumor scope is now recorded as:

> cancer/tumor research and field development, including development/release of diagnostic, treatment, clinical, surgical, or medical technologies; routine local hospital adoption/operation as such is not a standing interest.

This is narrower than the initial v2 draft and matches the latest human calibration.

No other interest taxonomy was expanded.

---

## 6. Estimator v2

Eval-only estimator:

`eval/live/standing_radar_fit_v2.py`

Version identifiers remain:

```text
estimator_version  standing-radar-fit-estimator-v2
prompt_version     standing-radar-fit-v2
profile_id         standing-radar-profile-v2
```

The prompt itself did not need a second repair. It already requires:

1. all substantive semantic facets;
2. no single dominant-domain collapse;
3. separation of substantive facets from incidental tools/context;
4. Standing Radar matching per substantive facet;
5. IN when at least one substantive facet genuinely matches;
6. exclusions as scope guards only.

The scope correction is carried by the calibrated Standing Radar profile. Production scheduler behavior remains unchanged.

---

## 7. Fresh validation contract — RESET AFTER CALIBRATION

The original RV template must not be used as fresh v2 evidence because its Human labels informed the final profile calibration.

New fresh template:

`eval/live/manifest.standing_radar_fit_v2_fresh_validation.v2.template.yaml`

It contains eight new paired cases and intentionally has no Human Gold yet.

Pre-registered target remains:

```text
Exact >= 7/8
IN recall >= 3/4
OUT recall >= 3/4
Complete pair flips >= 3/4
No clear semantic-composition failure
```

The old FD1-FD20, IX1-IX8, and RV1-RV8 sets must not be re-reported as fresh v2 performance.

The first scored v2 run on the new frozen fresh Human Gold is the measurement.

---

## 8. Current pointer

```text
D semantics                         FROZEN
D v1 historical baseline            PRESERVED
D v2 semantic repair                IMPLEMENTED
RV scope calibration                RECORDED / DEVELOPMENT ONLY
Standing Radar profile v2           CALIBRATED BEFORE MEASUREMENT
Fresh v2 Human Gold                 NEXT
Fresh v2 model measurement          AFTER HUMAN GOLD FREEZE
S estimator study                   AFTER D v2 closure decision
```

Do not expand D into a larger benchmark. If v2 passes the new fresh repair validation without a new systematic residual, close D for Phase II-B and move to S.
