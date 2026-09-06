# Research Attention OS — Roadmap and Progress

Status: **ACTIVE PROJECT ROADMAP**  
Date: 2026-09-06  
Code/eval baseline referenced: `354d2b5011a868f0295e2ac2750822275c83db51`  
Semantic baseline: `08_COGNITIVE_TRANSITION_MODEL_V2.1.md` + Phase II-B AWARE semantics recorded in `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`

> Purpose: preserve the long-horizon research position of RAOS so that individual experiments, implementation sessions, or conversation loss cannot erase where the project is, what is already closed, and what must happen next.

---

## 1. North star

RAOS exists because external information volume has exceeded the amount a human can read, understand, and digest directly.

The product objective is not “read more”. It is:

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

Directional optimization target:

$$
CROA = \frac{Useful\ Cognitive\ Change}{Human\ Attention\ Cost}
$$

CROA is directional, not a prematurely precise scalar objective.

---

## 2. Minimal constitutional loop

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
K_t
\xrightarrow{accepted\ KernelPatch}
K_{t+1}
$$

Core invariants:

- `CognitiveChange != AttentionAction`
- `Location != UpdateTarget`
- Claim != Observation != Inference
- AI may propose cognition change; it may not silently commit protected cognition
- WATCH transfers future attention responsibility to the system
- do not replace the system with one relevance score

---

## 3. Phase map

| Phase | Objective | Status |
|---|---|---|
| Phase I — Constitutional Vertical Slice | Establish information objects, cognitive transition, AttentionPlan, KernelPatch, provenance, and human commit boundary | **CLOSED** |
| Phase II-A — Cognitive Transition Model | Make `Extract -> Locate -> Impact -> Delta` semantically reliable and freeze the cognitive model | **FROZEN / CLOSED BASELINE** |
| Phase II-B — Attention Policy Calibration | Determine how frozen cognitive judgment plus legitimate non-cognitive signals should allocate DROP/AWARE/WATCH/ENGAGE | **ACTIVE — CURRENT PHASE** |
| Phase III — Continuous Attention OS | Continuous discover/ingest/dedup/cluster/route plus real WATCH re-check responsibility | **NOT STARTED** |
| Phase IV — Longitudinal Cognitive Alignment | Keep Kernel and policy aligned as user cognition changes over time | **NOT STARTED** |
| Phase V — Personalization at Scale | Questionnaire prior + trajectory residuals + multi-user validation | **NOT STARTED** |

Current strategic position:

$$
\boxed{Phase\ II\text{-}B:\ AWARE\ signal\ estimation\ and\ policy\ calibration}
$$

The project is still answering:

> **Can RAOS reason about attention reliably enough for real use?**

Only after this is good enough should the project move to continuous world monitoring.

---

## 4. What is already closed

### 4.1 Cognitive Transition Model v2.1

`08_COGNITIVE_TRANSITION_MODEL_V2.1.md` is the frozen cognitive baseline.

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

### 4.2 AttentionPlan execution semantics

AttentionPlan is an allocation object, not a second cognitive judgment.

The same frozen AnalysisRun may produce different plans under different runtime contexts without changing `Delta`.

### 4.3 Phase II evaluation protocol

Method:

$$
\boxed{Freeze\ baseline\rightarrow Measure\rightarrow Attribute\rightarrow Improve}
$$

Oracle-Delta and fresh end-to-end evaluation are separated. Human Gold must be elicited before observing system predictions.

### 4.4 Oracle-Delta policy baseline

The 30-case Human Gold policy study established that the existing policy does not explain all attention decisions from `Delta` alone.

Recorded baseline after the targeted policy fixes:

```text
Exact Accuracy       0.5333333333
Mean Distance        0.5
False DROP           0.1333333333
Over-attention       0.1666666667
Under-attention      0.3
Critical Under       0
```

The important result was representational, not the score itself:

$$
\boxed{
\Delta=\varnothing\ \not\Rightarrow\ DROP
}
$$

### 4.5 Oracle-Awareness wiring and provenance repair

Production `AwarenessSignals` currently contains three separate fields and is optional; production does not yet estimate them from real-world information.

The Oracle-Awareness experiment and provenance repair are closed at baseline commit:

```text
354d2b5011a868f0295e2ac2750822275c83db51
```

Synthetic truth-table results and Human-elicited results must remain provenance-separated. Synthetic 8/8 is a wiring test, not Human Gold generalization evidence.

---

## 5. Current AWARE research baseline

For the current no-cognitive-change gap:

$$
\Delta_t=\varnothing
$$

AWARE means:

> **Situational awareness without cognitive commitment.**

No Kernel write. No continuing WATCH obligation. Low-cost human awareness only.

The current Phase II-B candidate gate is:

$$
\boxed{
AWARE\iff S\land(D\lor P)
}
$$

where:

$$
D=Standing\ Interest\ Fit\ independent\ of\ event\ significance
$$

$$
S=Material\ consequence\ of\ the\ underlying\ event,\ independent\ of\ user\ interest\ and\ public\ attention
$$

$$
P=Current/emerging\ public\ attention\ salience,\ independent\ of\ user\ interest\ and\ intrinsic\ significance
$$

Human-language contract:

> **For information with no cognitive update, AWARE is justified when the underlying event has real substance and either belongs to the user's standing attention radar or has entered the public/industry attention radar.**

Interpretation:

- `S` is the value gate.
- `D` is the standing personal-radar channel.
- `P` is the public-attention channel.

These are candidate orthogonal explanatory dimensions. The project is **not** committed to a linear weighted model.

---

## 6. Current subphase: measurement-instrument calibration

Current work is **not yet formal D estimator measurement**.

The immediate task is to make sure the Human Gold instrument asks the same question as the variable definition.

### D measurement contract

Ask only:

> **Ignoring how important this particular event is, does its substantive topic belong to a world the user wants RAOS to monitor on a standing basis?**

Do not answer:

- whether the item should be AWARE/DROP;
- whether the event is important;
- whether it is popular;
- whether it affects the current Kernel.

Important invariants under study:

- D granularity is determined by **stable preference**, not taxonomy depth.
- incidental mention/use of a radar technology does not itself create D membership.
- ordinary events inside a standing-interest area may still have `D=1, S=0` and be DROP later.
- an event outside the standing radar may still become AWARE through `S=1, P=1`.

### Measurement provenance cleanup

Earlier D `IN/OUT` elicitation became contaminated because `IN` was interpreted as AWARE and `OUT` as DROP. Those labels are calibration evidence, **not clean D Gold**.

The earlier H1-H10 cases also participated in semantic refinement and are therefore development/calibration cases, not a fresh holdout.

The current DH1-DH15 pass is being used to calibrate the answering instrument and Standing Radar boundaries. **Do not freeze it as formal estimator holdout until the identified radar-definition inconsistencies are resolved.**

---

## 7. Immediate next steps

Execute in this order:

```text
NOW
  ↓
Calibrate D answering instrument + Standing Radar boundaries
  ↓
Freeze a fresh D Human Gold holdout
  ↓
Test minimal natural-language D estimator
  ↓
Attribute residuals; do not tune to isolated cases
  ↓
Study / estimate S
  ↓
Study / estimate P
  ↓
Evaluate the complete no-Delta AWARE gate
  ↓
Fresh real-world end-to-end dogfooding
  ↓
Phase II exit decision
```

Estimator sequence:

$$
\boxed{D\ estimator\rightarrow S\ estimator\rightarrow P\ estimator}
$$

For D, the current Occam hypothesis is:

$$
EventText+StandingRadarProfile\rightarrow \hat D
$$

without a giant domain ontology unless residuals force one.

A small D holdout should be treated as engineering evidence, not population science. A useful provisional success bar is >=80% exact accuracy with no clear systematic failure mode. Isolated residuals should remain visible rather than being patched with case-specific rules.

---

## 8. Phase II-B exit condition

Phase II-B is done when the Attention Policy is reliable enough for genuine personal dogfooding, not when every synthetic benchmark reaches 100%.

Required qualitative properties:

- clear cognitive change is not silently dropped;
- no-cognitive-change AWARE has a defensible, measurable basis;
- D/S/P can be estimated sufficiently well from real information;
- WATCH remains a real future-attention obligation rather than a label;
- runtime may alter allocation without rewriting frozen cognition;
- residual policy errors are attributable rather than mysterious.

Then move to Phase III instead of endlessly polishing the offline policy benchmark.

---

## 9. Phase III — Continuous Attention OS

The next major product step is continuous responsibility over the external world:

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

Phase III should not begin by building a giant crawler or recommender feed. Start with a narrow, measurable real source loop.

---

## 10. Phase IV — Longitudinal Kernel alignment

Once continuous information flow exists, test whether RAOS remains aligned as cognition changes:

$$
K_t\rightarrow K_{t+1}\rightarrow K_{t+2}\rightarrow\cdots
$$

Questions:

- does old attention policy become stale as projects and beliefs change?
- does accepted KernelPatch correctly change future Locate/Impact decisions?
- can WATCH obligations be retired when the Kernel changes?
- can the system distinguish persistent user preference from temporary project context?

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

Do not train a personal policy from noisy click behavior before the controlled variables and causal semantics are understood.

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
6. When the phase exit condition is met, move forward rather than overfitting the current benchmark.

---

## 13. Current pointer

As of 2026-09-06:

$$
\boxed{
Phase\ II\text{-}B
\rightarrow
D/S/P\ semantics\ stabilized
\rightarrow
D\ measurement\ instrument\ calibration\ NOW
}
$$

The next formal measurement must not start until the D answering contract and Standing Radar profile are internally consistent.
