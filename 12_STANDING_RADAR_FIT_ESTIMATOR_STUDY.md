# Research Attention OS — Standing Radar Fit Estimator Study

Status: **HUMAN GOLD FROZEN / ESTIMATOR NOT YET MEASURED**  
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

## 8. Current project pointer

```text
D semantics                 FROZEN
Standing Radar profile      CALIBRATED / FROZEN v1
D answering instrument      CALIBRATED
Fresh D Human Gold          FROZEN (FD1-FD20)
D estimator                 NEXT — first blind measurement
S estimator study           AFTER D decision
P estimator study           AFTER S
Complete no-Delta AWARE     AFTER D/S/P estimation studies
```

The next action is to implement the smallest model-backed D estimator and run exactly one first measurement against the frozen FD1-FD20 holdout.
