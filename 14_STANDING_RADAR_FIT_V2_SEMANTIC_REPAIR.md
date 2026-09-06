# Research Attention OS — Standing Radar Fit v2 Semantic Repair

Status: **REPAIR IMPLEMENTED / FRESH HUMAN VALIDATION NEXT**  
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

The diagnostic did not support a global rule that exclusions always win. Instead it exposed two narrower problems:

1. multi-facet events can be collapsed into one dominant domain;
2. the v1 cancer/tumor standing-interest wording was narrower than the user's demonstrated standing preference.

The repair therefore remains semantic and minimal. It does not introduce domain weights, a domain ontology, or a new attention variable.

---

## 2. Repaired semantic model

Candidate representation:

$$
\boxed{
E\rightarrow F_s(E)=\{substantive\ semantic\ facets\}
}
$$

Decision rule:

$$
\boxed{
D(E)=IN\iff\exists f\in F_s(E):Match(f,StandingRadar)
}
$$

A substantive facet is itself part of what is being developed, released, studied, deployed, measured, changed, or operated. Incidental tools, implementation details, organizational context, or application setting do not become standing-interest matches merely by appearing in the event.

An event may have multiple substantive facets. Do not force a single dominant domain.

---

## 3. Exclusion semantics

Standing exclusions are reinterpreted as **scope guards**, not negative votes and not vetoes.

They answer:

> What broad inherited match should NOT automatically count as a standing interest?

They do not answer:

> What positive standing-interest facet should be cancelled?

Thus:

$$
\boxed{
Exclusion\ constrains\ over\text{-}broad\ matching;
\quad Exclusion\ does\ not\ veto\ a\ genuine\ substantive\ match.
}
$$

This preserves the earlier invariant:

$$
Using\ AI\ method\neq Being\ an\ AI\ event
$$

while allowing a genuine substantive robotics/AI/compute/cancer facet to remain visible inside an otherwise excluded application domain.

---

## 4. Standing Radar profile v2

New artifact:

`eval/live/standing_radar_profile.v2.yaml`

Historical v1 remains frozen.

The only intentional scope repair beyond the general composition semantics is the cancer/tumor interest wording. v2 records the demonstrated preference as including substantive cancer/tumor scientific, diagnostic, treatment, clinical, surgical, and technical developments rather than only research-paper-like events.

No other interest taxonomy was expanded.

---

## 5. Estimator v2

New eval-only estimator:

`eval/live/standing_radar_fit_v2.py`

Version identifiers:

```text
estimator_version  standing-radar-fit-estimator-v2
prompt_version     standing-radar-fit-v2
profile_id         standing-radar-profile-v2
```

The v2 prompt requires the model to:

1. identify all substantive semantic facets;
2. preserve multiple substantive facets;
3. distinguish substantive facets from incidental tools/context;
4. match each substantive facet against the Standing Radar;
5. return IN if at least one substantive facet genuinely matches;
6. treat exclusions only as scope guards.

Diagnostic output now includes `substantive_facets`, but only `standing_radar_fit` is scored. The facet list is diagnostic evidence, not a production ontology.

Production scheduler behavior remains unchanged.

---

## 6. Fresh validation contract

Template:

`eval/live/manifest.standing_radar_fit_v2_fresh_validation.template.yaml`

The template contains eight fresh paired cases and intentionally has no Human Gold yet.

Human labels must be elicited before model measurement.

Pre-registered target:

```text
Exact >= 7/8
IN recall >= 3/4
OUT recall >= 3/4
Complete pair flips >= 3/4
No clear semantic-composition failure
```

The old FD1-FD20 and IX1-IX8 sets must not be re-reported as fresh v2 evidence.

The first scored v2 run on frozen fresh Human Gold is the measurement.

---

## 7. Current pointer

```text
D semantics                         FROZEN
D v1 historical baseline            PRESERVED
D v2 minimal semantic repair        IMPLEMENTED
Fresh v2 Human Gold                 NEXT
Fresh v2 model measurement          AFTER HUMAN GOLD FREEZE
S estimator study                   AFTER D v2 closure decision
```

Do not expand D into a larger benchmark. If v2 passes the fresh repair validation without a new systematic residual, close D for Phase II-B and move to S.
