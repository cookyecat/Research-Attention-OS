# Research Attention OS — Roadmap and Progress

Status: **ACTIVE PROJECT ROADMAP**  
Date: 2026-09-06  
Production/eval baseline referenced: `354d2b5011a868f0295e2ac2750822275c83db51`  
Semantic baseline: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md` + Phase II-B AWARE semantics in `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`  
Current D study: `12_STANDING_RADAR_FIT_ESTIMATOR_STUDY.md`

> Purpose: preserve the long-horizon research position of RAOS so that individual experiments, implementation sessions, or conversation loss cannot erase what is closed, what is active, and what happens next.

---

## 1. North star

RAOS exists because external information volume has exceeded what a human can read, understand, and digest directly.

$$
\boxed{
Massive\ Information
\rightarrow
Minimal\ Human\ Attention
\rightarrow
Maximum\ Useful\ Cognitive\ Progress
}
$$

Canonical product definition:

> **RAOS estimates how new information changes the user's current cognition, then allocates bounded human attention accordingly.**

Long-term requirement:

> **Continuously keep that estimate aligned as the user's cognition changes.**

Directional objective:

$$
CROA = \frac{Useful\ Cognitive\ Change}{Human\ Attention\ Cost}
$$

CROA is directional, not a prematurely precise scalar objective.

---

## 2. Constitutional loop

$$
(I_t,K_t)
\rightarrow
\Delta_t
\rightarrow
A_t
\rightarrow
HumanFeedback
\rightarrow
K_{t+1}
$$

Kernel mutation remains human-authorized:

$$
K_t\xrightarrow{accepted\ KernelPatch}K_{t+1}
$$

Core invariants:

- `CognitiveChange != AttentionAction`
- `Location != UpdateTarget`
- `Claim != Observation != Inference`
- AI may propose cognition change; it may not silently commit protected cognition
- WATCH transfers future attention responsibility to the system
- do not replace the system with one relevance score

---

## 3. Phase map

| Phase | Objective | Status |
|---|---|---|
| Phase I — Constitutional Vertical Slice | Information objects, cognitive transition, AttentionPlan, KernelPatch, provenance, human commit boundary | **CLOSED** |
| Phase II-A — Cognitive Transition Model | Reliable `Extract -> Locate -> Impact -> Delta`; freeze cognitive semantics | **FROZEN / CLOSED BASELINE** |
| Phase II-B — Attention Policy Calibration | Determine how frozen cognitive judgment plus legitimate non-cognitive signals allocate DROP/AWARE/WATCH/ENGAGE | **ACTIVE — CURRENT PHASE** |
| Phase III — Continuous Attention OS | Continuous discover/ingest/dedup/cluster/route plus real WATCH re-check responsibility | **NOT STARTED** |
| Phase IV — Longitudinal Cognitive Alignment | Keep Kernel and policy aligned as user cognition changes | **NOT STARTED** |
| Phase V — Personalization at Scale | Questionnaire prior + trajectory residuals + multi-user validation | **NOT STARTED** |

Current strategic position:

$$
\boxed{Phase\ II\text{-}B:\ D\ estimator\ first\ blind\ measurement\ NEXT}
$$

The project is still answering:

> **Can RAOS reason about attention reliably enough for genuine personal use?**

Do not move to broad continuous monitoring until this is good enough; do not over-polish offline policy once the phase exit condition is met.

---

## 4. Closed / frozen baselines

### 4.1 Cognitive Transition Model v2.1 — FROZEN

`08_COGNITIVE_TRANSITION_MODEL_V2.1.md` is the cognitive baseline.

$$
E_t=Extract(I_t)
$$

$$
L_t=Locate(E_t,K_t)
$$

$$
\Delta_t=F_\theta(E_t,K_t,L_t)
$$

$$
\Delta_t\in\{\varnothing,REINFORCE,CHALLENGE,OPEN\_NEW\}
$$

The transition model is not to be redesigned merely to improve Attention Policy results.

### 4.2 AttentionPlan semantics — CLOSED

AttentionPlan is allocation, not a second cognitive judgment.

A frozen AnalysisRun may yield different plans under different runtime contexts without changing $\Delta$.

### 4.3 Phase II evaluation protocol — FROZEN

$$
\boxed{
Formalize
\rightarrow
Calibrate\ instrument
\rightarrow
Freeze\ Gold
\rightarrow
Measure
\rightarrow
Attribute
\rightarrow
Improve
}
$$

Human Gold must be elicited before seeing the system prediction used as measurement.

### 4.4 Oracle-$\Delta$ policy baseline — RECORDED

After the targeted policy fixes:

```text
Exact Accuracy       0.5333333333
Mean Distance        0.5
False DROP           0.1333333333
Over-attention       0.1666666667
Under-attention      0.3
Critical Under       0
```

Key representational result:

$$
\boxed{\Delta=\varnothing\not\Rightarrow DROP}
$$

### 4.5 Oracle-Awareness wiring / provenance — CLOSED

Baseline commit:

```text
354d2b5011a868f0295e2ac2750822275c83db51
```

Synthetic truth-table results and Human-elicited results remain provenance-separated. Synthetic 8/8 is a wiring test, not Human Gold generalization evidence.

Production does not yet estimate the real-world awareness signals.

---

## 5. Phase II-B AWARE semantic baseline — FROZEN FOR MEASUREMENT

Scope:

$$
\Delta_t=\varnothing
$$

AWARE means:

$$
\boxed{AWARE=Situational\ Awareness\ without\ Cognitive\ Commitment}
$$

No Kernel write. No continuing WATCH obligation. Low-cost human awareness only.

Current candidate no-$\Delta$ gate:

$$
\boxed{AWARE\iff S\land(D\lor P)}
$$

where:

$$
\boxed{D=Standing\ Interest\ Fit\ independent\ of\ event\ significance}
$$

$$
\boxed{S=Material\ consequence\ of\ the\ underlying\ event,\ independent\ of\ user\ interest\ and\ public\ attention}
$$

$$
\boxed{P=Current/emerging\ public\ attention\ salience,\ independent\ of\ user\ interest\ and\ intrinsic\ significance}
$$

Human-language contract:

> **For information with no cognitive update, AWARE is justified when the underlying event has real substance and either belongs to the user's standing attention radar or has entered the public/industry attention radar.**

Physical interpretation:

- `S` = value gate
- `D` = standing personal-radar channel
- `P` = public-attention channel

These are candidate orthogonal explanatory dimensions. The project is not committed to a linear weighted model.

Important invariants:

- `D != S`
- `S != P`
- `D != P`
- incidental mention/use of a radar technology does not create D membership
- technical novelty is not event significance
- artifact quality is not event significance
- S may be technical, economic, scientific, social, cultural, or institutional consequence
- D granularity follows stable preference, not taxonomy depth

---

## 6. D study status

### 6.1 Measurement instrument — CALIBRATED

D asks only:

> **Ignoring how important this particular event is, does its substantive topic belong to a world the user wants RAOS to monitor on a standing basis?**

Do not answer:

- AWARE/DROP
- event significance
- public popularity
- Kernel change

Earlier `IN/OUT`, H1-H10, and DH1-DH15 exercises are calibration/development evidence, not fresh holdout performance.

### 6.2 Standing Radar profile v1 — FROZEN

Artifact:

`eval/live/standing_radar_profile.v1.yaml`

The profile records stable semantic interests plus a small number of calibrated exclusions. It is intentionally not a giant inherited domain taxonomy.

Key boundary principle:

$$
\boxed{D\ granularity=stable\ preference\ granularity}
$$

### 6.3 Fresh D Human Gold v1 — FROZEN

Artifact:

`eval/live/manifest.standing_radar_fit_human_gold.v1.yaml`

The user labeled FD1-FD20 after the instrument/profile were calibrated and before the estimator was measured.

Class composition:

```text
IN   15
OUT   5
N    20
```

These labels are now frozen. Do not use them to modify the estimator and then report the same set as fresh holdout evidence.

### 6.4 D estimator — NEXT

Research hypothesis:

$$
\boxed{EventText+StandingRadarProfile\rightarrow\hat D}
$$

Occam constraint: do not build a giant domain ontology unless residual evidence forces it.

Pre-registered measurement details live in:

`12_STANDING_RADAR_FIT_ESTIMATOR_STUDY.md`

Because an always-IN classifier already scores 75% exact accuracy, the success criterion is:

$$
\boxed{
ExactAccuracy\ge0.80
\land
BalancedAccuracy\ge0.80
\land
NoClearSystematicFailure
}
$$

First predictions are the measurement.

---

## 7. Immediate next steps

Execute in this order:

```text
NOW
  ↓
Implement minimal model-backed D estimator
  ↓
Run first blind FD1-FD20 measurement exactly once
  ↓
Record exact + balanced accuracy + IN/OUT recall + residuals
  ↓
Decide D estimator sufficient? YES / NO
  ↓
If YES: study / estimate S
  ↓
Study / estimate P
  ↓
Evaluate complete no-Delta AWARE gate
  ↓
Fresh real-world end-to-end dogfooding
  ↓
Phase II exit decision
```

Estimator sequence:

$$
\boxed{D\ estimator\rightarrow S\ estimator\rightarrow P\ estimator}
$$

If D passes, do not keep polishing it for cosmetic 100% performance. Preserve isolated residuals and move to S.

If D fails systematically, attribute the failure before changing the profile, prompt, or representation. Any revised estimator claim requires a new fresh holdout.

---

## 8. Phase II-B exit condition

Phase II-B is complete when Attention Policy is reliable enough for real personal dogfooding, not when every synthetic benchmark reaches 100%.

Required qualitative properties:

- clear cognitive change is not silently dropped;
- no-cognitive-change AWARE has a defensible, measurable basis;
- D/S/P can be estimated sufficiently well from real information;
- WATCH remains a real future-attention obligation rather than a label;
- runtime may alter allocation without rewriting frozen cognition;
- residual policy errors are attributable rather than mysterious.

Then move to Phase III.

---

## 9. Phase III — Continuous Attention OS

Next major product step:

```text
discover
  -> ingest
  -> deduplicate
  -> cluster events
  -> extract / locate / impact
  -> allocate attention
  -> create / update WATCH
  -> re-check future evidence
  -> surface only when policy conditions are met
```

Key principle:

> **WATCH means RAOS has accepted future attention responsibility.**

Start with a narrow measurable real-source loop, not a giant crawler or recommendation feed.

---

## 10. Phase IV — Longitudinal Cognitive Alignment

Once continuous information flow exists:

$$
K_t\rightarrow K_{t+1}\rightarrow K_{t+2}\rightarrow\cdots
$$

Test whether accepted Kernel changes correctly alter future Locate/Impact/Attention decisions, whether WATCH obligations become stale, and whether standing preference remains distinct from temporary project context.

---

## 11. Phase V — Personalization

Only after real trajectories exist should personalization move beyond initial calibration.

Candidate architecture:

$$
\boxed{
AttentionPolicy_u
=
SharedPolicyPrior
+
QuestionnaireCalibration_u
+
TrajectoryResidual_u
}
$$

Do not train personal policy from noisy click behavior before the controlled variables and causal semantics are understood.

---

## 12. Working discipline

For every open research question:

$$
\boxed{
Formalize
\rightarrow
Calibrate\ instrument
\rightarrow
Freeze\ Gold
\rightarrow
Measure
\rightarrow
Attribute
\rightarrow
Improve
}
$$

Rules:

1. Do not optimize a black box.
2. Do not add ontology because one boundary case is awkward.
3. Do not convert development cases into holdout evidence after discussing their labels.
4. Do not let Attention Policy manufacture cognitive change.
5. Prefer residual evidence over a cosmetically perfect score.
6. When a phase exit condition is met, move forward rather than overfitting the current benchmark.
