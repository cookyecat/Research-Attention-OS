# Research Attention OS — Roadmap and Progress

Status: **ACTIVE PROJECT ROADMAP**  
Date: 2026-09-06  
Production/eval baseline referenced: `354d2b5011a868f0295e2ac2750822275c83db51`  
Semantic baseline: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md` + Phase II-B AWARE semantics in `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`  
D semantic baseline: `16_STANDING_ATTENTION_JURISDICTION.md`  
D final validation: `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`  
Product/recommender boundary: `13_RAOS_VS_RECOMMENDATION_SYSTEMS.md`

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

Product contrast recorded in `13_RAOS_VS_RECOMMENDATION_SYSTEMS.md`:

> **Recommendation systems compete for attention; RAOS budgets attention.**

More rigorously, RAOS optimizes attention efficiency rather than assuming that more consumption / engagement is the desired outcome.

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
\boxed{Phase\ II\text{-}B:\ S=Material\ Consequence\ NOW}
$$

D semantic research is closed. The v3 estimator has attributable implementation residuals and is not certified as a passed estimator; do not expand D into another offline synthetic benchmark now.

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
\boxed{D=D(E,u)=\mathbf 1[E\in\mathcal J_u]}
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
- S may be technical, economic, scientific, social, cultural, political, or institutional consequence

---

## 6. D study — SEMANTICS CLOSED / ESTIMATOR RESIDUALS PRESERVED

### 6.1 Canonical D definition

`16_STANDING_ATTENTION_JURISDICTION.md` is the frozen D semantic baseline.

$$
\boxed{
\mathcal J_u
=
\{E\mid\exists\rho_i\in\mathcal R_u,\rho_i(Sem(E),u)=1\}
}
$$

$$
\boxed{D(E,u)=\mathbf 1[E\in\mathcal J_u]}
$$

Standing Radar Clauses are applicability conditions, not domain weights. Clauses may concern a substantive topic, actor/entity/person, work/content object, place/governance scope, or stable affiliation. These semantic forms do not justify separate D sub-variables or a typed ontology.

Exclusions remain:

$$
\boxed{Exclusion=ScopeGuard,\quad Exclusion\neq Veto}
$$

### 6.2 Historical v1 measurement

First blind holdout:

```text
ExactAccuracy       0.90
BalancedAccuracy    0.9333333333333333
IN recall           0.8666666666666667
OUT recall          1.0
False-IN            0
False-OUT           FD6, FD16
Technical failures  0
```

This supported compact natural-language Standing Radar representation and argued against building a giant domain ontology.

### 6.3 Intersection diagnostic

The v1 intersection diagnostic failed its pre-registered criterion at 6/8 and exposed semantic-composition/scope problems. That evidence led to the substantive-facet, scope-guard, and later Standing-Attention-Jurisdiction formalization. Historical results remain preserved and must not be rewritten as fresh evidence.

### 6.4 Final v3 fresh measurement

Artifact:

`eval/live/results/standing_radar_fit_v3_final_fresh_first_run.json`

Result commit:

```text
07ae4b3
```

Observed:

```text
Exact accuracy       0.70
IN recall            0.50
OUT recall           0.8333333333
Balanced accuracy    0.6666666667
False-IN             FJ2
False-OUT            FJ4, FJ6
Technical failures   0
```

The v3 estimator **failed the pre-registered final-validation gate** and is not certified as a passed estimator.

Residual attribution is recorded in `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`:

- FJ2 is internally consistent with the frozen AI-Agent clause and is treated as a human-policy boundary / possible noisy-label residual rather than evidence for changing D semantics.
- FJ4 is a real clause-application failure: the model recognized OpenAI as a substantive actor but imposed an extra significance/topic-development condition not present in the clause.
- FJ6 is a real stable-affiliation extraction/application failure despite an explicit direct-family clause.

The formal model is more general than the diagnostic `substantive anchor -> clause match` implementation view. Future integrated implementation may evaluate clauses more directly over `Sem(E),u`.

Research decision:

```text
D semantic definition                  CLOSED / FROZEN
D clause representation                SUPPORTED
D v3 estimator                         NOT CERTIFIED
Known estimator residuals              ATTRIBUTABLE
Further synthetic D benchmark work     STOP
```

Do not introduce domain weights or a large ontology from this result. Revisit implementation only if integrated dogfooding exposes a repeated real-world failure pattern.

---

## 7. Immediate next steps

Execute in this order:

```text
NOW
  ↓
Formalize S = Material Consequence
  ↓
Calibrate the S answering instrument
  ↓
Freeze fresh S Human Gold
  ↓
Implement / measure S estimator
  ↓
Study / estimate P
  ↓
Evaluate complete no-Delta AWARE gate
  ↓
Fresh real-world end-to-end dogfooding
  ↓
Phase II exit decision
```

Estimator sequence remains:

$$
\boxed{D\rightarrow S\rightarrow P}
$$

D is no longer the active research question.

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
