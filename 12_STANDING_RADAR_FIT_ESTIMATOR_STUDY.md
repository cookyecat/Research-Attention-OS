# Research Attention OS — Standing Radar Fit Estimator Study

Status: **D CORE SUPPORTED / SEMANTIC-COMPOSITION BOUNDARY OPEN**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Related: `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`, `11_ROADMAP_AND_PROGRESS.md`

---

## 1. Research question

Can the user-specific standing-interest signal $D$ be estimated from a compact natural-language Standing Radar profile without introducing a giant domain taxonomy?

$$
\boxed{
EventText + StandingRadarProfile \rightarrow \hat D
}
$$

where:

$$
\boxed{
D=Standing\ Interest\ Fit\ independent\ of\ event\ significance
}
$$

The estimator must answer only whether the event's substantive topic belongs to a world the user wants RAOS to monitor on a standing basis.

It must not answer event significance $S$, public-attention salience $P$, AWARE/DROP disposition, or cognitive change $\Delta$.

---

## 2. Frozen measurement artifacts

Standing Radar profile:

`eval/live/standing_radar_profile.v1.yaml`

Fresh Human Gold:

`eval/live/manifest.standing_radar_fit_human_gold.v1.yaml`

The 20 FD cases were labeled by the user after the D answering instrument and Standing Radar boundaries had been calibrated, and before estimator implementation/measurement.

Earlier IN/OUT cases, H1-H10, and DH1-DH15 are calibration/development evidence and must not be reported as fresh holdout performance.

---

## 3. Measurement invariants

The estimator may consume only:

- the frozen Standing Radar profile;
- the current event text;
- the abstract D semantic contract.

It must not consume:

- FD1-FD20 gold labels;
- case-specific rationales derived from the gold labels;
- $S$ or $P$ estimates;
- AWARE/DROP labels;
- Kernel-match scores as a substitute for Standing Radar Fit;
- a hand-built domain taxonomy created to fit the holdout.

Important semantic invariants:

- incidental mention/use of AI, GPU, Python, cloud, etc. does not create D membership;
- judge the event given, not unstated inferred facts;
- D granularity follows stable user preference, not taxonomy depth;
- ordinary events in a standing-interest area may have $D=1$ even when $S=0$ and later be DROP.

---

## 4. Holdout composition

Human Gold class counts:

```text
IN   15
OUT   5
N    20
```

A trivial always-IN classifier therefore achieves 75% exact accuracy.

For that reason exact accuracy alone is not a sufficient success criterion.

---

## 5. Pre-registered metrics and success criterion

Report:

- exact accuracy;
- balanced accuracy;
- IN recall;
- OUT recall;
- false-IN count/rate;
- false-OUT count/rate;
- per-case prediction;
- model/provider/version;
- matched standing-interest areas as diagnostics only;
- brief reason as diagnostics only.

Primary engineering success criterion, frozen before the first estimator run:

$$
\boxed{
ExactAccuracy \ge 0.80
\quad\land\quad
BalancedAccuracy \ge 0.80
\quad\land\quad
NoClearSystematicFailure
}
$$

Balanced accuracy is:

$$
\frac{Recall_{IN}+Recall_{OUT}}{2}
$$

This prevents the 15/5 class imbalance from making an always-IN or near-always-IN estimator look successful.

This is a small personal engineering holdout, not a population benchmark.

---

## 6. First-run rule

$$
\boxed{First\ predictions = measurement}
$$

Do not inspect residuals, modify the estimator, and then re-report FD1-FD20 as fresh holdout performance.

If residuals exist:

1. preserve the first-run score;
2. attribute the failures;
3. distinguish isolated boundary errors from systematic representation failure;
4. do not add case-specific ontology/rules merely to reach 100%;
5. use a new holdout for any later revised estimator claim.

---

## 7. Minimal estimator hypothesis

Occam hypothesis:

> A model can perform semantic membership against a concise user Standing Radar profile well enough for $D$ estimation without a domain ontology.

Preferred structured diagnostic output:

```json
{
  "standing_radar_fit": "IN | OUT",
  "matched_interests": ["brief profile phrases"],
  "reason": "brief semantic-membership explanation"
}
```

Only `standing_radar_fit` is scored.

`matched_interests` and `reason` are diagnostics, not new production ontology.

Reuse the existing model-backed cognitive infrastructure (`backend/app/cognitive/client.py`, `model_provider.py`, validated structured JSON patterns) rather than building a second model HTTP stack.

Do not connect this estimator to production `scheduler.py` during the measurement commit.

---

## 8. Frozen first-run measurement — core D holdout

Artifact:

`eval/live/results/standing_radar_fit_v1_first_run.json`

Estimator freeze commit:

```text
be6db49af93d87e5cbb29bdf54806a5f2ae07859
```

Invocation:

```text
estimator_version     standing-radar-fit-estimator-v1
prompt_version        standing-radar-fit-v1
requested_model       deepseek-v4-flash
actual_model          deepseek-v4-flash
provider_base_url     https://api.deepseek.com
thinking_protocol     deepseek
thinking              disabled
reasoning_effort      null
timeout_seconds       60.0
temperature           0.1
measurement_timestamp 20260906T095043Z
```

Holdout result (N scored = 20, technical failures = 0):

```text
ExactAccuracy       0.90
IN recall           0.8666666666666667
OUT recall          1.0
BalancedAccuracy    0.9333333333333333
False-IN            0
False-OUT           2 (FD6, FD16)
```

The numeric gate passed. Two false-OUT residuals shared a possible interest/exclusion boundary pattern:

- FD6: commercial-space context + substantive on-orbit robotics;
- FD16: general-biomed context + cancer-surgery assistance device.

Because the shared pattern was based on only two cases, it was not sufficient to declare a systematic failure. A narrow causal diagnostic was therefore pre-registered rather than retuning the prompt.

---

## 9. Intersection / Semantic Composition Diagnostic v1 — RECORDED

Human Gold manifest:

`eval/live/manifest.standing_radar_intersection_diag.v1.yaml`

First-run artifact:

`eval/live/results/standing_radar_intersection_diag_v1_first_run.json`

Result commit:

```text
99a95841a5b7be00509aacf359bb43c81d009f64
```

The frozen v1 estimator and prompt were reused unchanged:

```text
estimator_version  standing-radar-fit-estimator-v1
prompt_version     standing-radar-fit-v1
prompt_sha256      92179131d684d84e9b6f214389c0166cb9137a12e22f44826380d2fc063da749
```

Diagnostic structure: four controlled pairs. Each pair contains an excluded-context-only case and a matched case in which a substantive standing-interest facet is added.

Human Gold was answered twice with identical labels:

```text
IX1 OUT   IX2 IN
IX3 OUT   IX4 IN
IX5 OUT   IX6 IN
IX7 OUT   IX8 IN
```

Pre-registered diagnostic target:

```text
Exact >= 7/8
Positive-intersection recall >= 3/4
Complete pair flips >= 3/4
No persistent exclusion-overrides-substantive-interest pattern
```

Observed:

```text
Exact accuracy                6/8 = 0.75
Balanced accuracy             0.75
Excluded-context-only recall  4/4 = 1.00
Positive-intersection recall  2/4 = 0.50
Complete pair flips           2/4 = 0.50
Technical failures            0
```

Errors:

```text
IX2  commercial space + substantive on-orbit maintenance robot  Gold IN / Pred OUT
IX4  general biomed + cancer-surgery assistance device          Gold IN / Pred OUT
```

Correct positive intersections:

```text
IX6  fusion + substantive reactor-inspection robot              Gold IN / Pred IN
IX8  industrial-electronics context + server CPU                Gold IN / Pred IN
```

The diagnostic therefore **failed its pre-registered criterion**.

---

## 10. Attribution after the diagnostic

The result does **not** support a simple global rule that “explicit exclusions always win.” The estimator successfully allowed a substantive standing interest to override excluded context in IX6 and IX8.

The remaining failures are narrower.

### 10.1 Space + robotics: dominant-domain arbitration

For IX2, the model explicitly recognized that robotics is a standing interest but still concluded that the event's substantive topic was “space operations, not robotics development.”

This indicates a tendency to collapse a multi-facet event into one dominant domain instead of representing multiple substantive facets.

Candidate semantic model:

$$
\boxed{
E\rightarrow F_s(E)=\{substantive\ semantic\ facets\}
}
$$

and then:

$$
\boxed{
D(E)=IN
\iff
\exists f\in F_s(E): Match(f,StandingRadar)
}
$$

This is different from a weighted competition among domains.

### 10.2 Cancer-surgery device: Standing Radar scope wording

For IX4, the model classified a cancer-surgery assistance device as “general non-AI biomedicine outside cancer/tumor research,” despite the event being explicitly about tumor resection.

The frozen profile currently says:

```text
Cancer and tumor research, including ordinary ongoing cancer/tumor science
```

Human Gold demonstrates that the user's actual standing radar is broader than research papers alone and includes substantive cancer/tumor clinical or technical events such as cancer-surgery assistance technology.

This may therefore be partly a **profile scope representation mismatch**, not purely estimator arbitration.

### 10.3 Current interpretation

The evidence now supports:

$$
\boxed{Compact\ natural\ language\ StandingRadar\ representation:\ SUPPORTED}
$$

$$
\boxed{D\ core\ estimator:\ STRONG\ but\ not\ semantically\ complete}
$$

$$
\boxed{Multi\text{-}facet\ composition/scope\ boundary:\ OPEN}
$$

Do not add domain weights or a domain ontology from this result.

---

## 11. Candidate minimal repair — NOT YET MEASURED

The smallest current hypothesis is semantic, not numeric:

1. Extract the set of **substantive semantic facets** of the event.
2. Distinguish substantive facets from incidental tools, methods, or context.
3. Treat Standing Radar exclusions as guards against over-broad matching, not as independent negative votes with veto power.
4. Set $D=IN$ if at least one substantive facet genuinely matches a standing interest.
5. Represent user-interest scope accurately; do not make “cancer/tumor” narrower than the calibrated human preference.

In shorthand:

$$
\boxed{
Event
\rightarrow
SubstantiveFacets
\rightarrow
StandingRadarMembership
}
$$

not:

$$
Event\rightarrow DomainWeights\rightarrow WeightedSum
$$

No v1 prompt/profile change should be reported as fresh performance on FD1-FD20 or IX1-IX8. Any revised estimator claim requires fresh evidence or later real-world integration evidence.

---

## 12. Current project pointer

```text
D semantics                         FROZEN
Standing Radar profile v1           FROZEN historical baseline
Fresh D Human Gold                  FROZEN (FD1-FD20)
D estimator v1 core measurement     0.90 exact / 0.933 balanced
Intersection diagnostic             FAILED pre-registered criterion
D representation hypothesis         SUPPORTED
Semantic-composition/scope boundary OPEN
S estimator study                   AFTER D repair/closure decision
P estimator study                   AFTER S
```

The next D action, if taken, must be a **minimal semantic repair**, not weight tuning, ontology expansion, or retuning on the existing Gold.
