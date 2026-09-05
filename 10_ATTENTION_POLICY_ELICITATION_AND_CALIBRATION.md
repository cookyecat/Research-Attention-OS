# Research Attention OS — Attention Policy Elicitation and Calibration

Status: **DESIGN NOTE / v2.2 CANDIDATE INSIGHT**  
Date: 2026-09-05  
Baseline: Cognitive Transition Model v2.1 (`08_COGNITIVE_TRANSITION_MODEL_V2.1.md`)  
Related: `09_ATTENTION_POLICY_INPUT_CLARIFICATION.md`  
Implementation status: **Not a production-policy change.** The v2.1 cognitive-transition baseline remains frozen.

> This document records an empirical/product-method insight discovered during Phase II Attention Policy calibration: users need not specify an Attention Policy explicitly. A compact set of controlled counterfactual judgments can elicit a stable latent policy well enough to initialize attention allocation, after which real trajectories can refine residual personalization.

---

## 1. Motivation

Research Attention OS treats human attention as a scarce resource. Time, cognitive capacity, and interruption budget are capital: spending attention on one item necessarily forgoes another use.

This suggests an allocation view:

$$
\text{Attention Allocation} \sim \text{Capital Allocation}
$$

The practical problem is that asking a user to define a scheduler directly is unnatural. Few users can or should specify rules such as:

```text
if target_importance > 0.6 and challenge > 0.5 then ENGAGE
```

But the same user can often answer a concrete judgment question immediately:

> Given this information, this cognitive effect, and this current situation, should I DROP, AWARE, WATCH, or ENGAGE?

The engineering hypothesis is therefore:

> **Elicit policy from judgments, rather than asking users to program policy.**

---

## 2. Core elicitation hypothesis

Let $x$ denote a controlled attention-allocation situation and $y$ the user's disposition judgment:

$$
y \in \{DROP, AWARE, WATCH, ENGAGE\}
$$

A questionnaire supplies carefully designed $x_i$ that vary one factor at a time where possible. The observed judgments

$$
\{(x_i,y_i)\}_{i=1}^{N}
$$

constrain a latent user policy $\pi_u$.

The user does not need to know the parameterization of $\pi_u$. The system can estimate or select it from judgments.

This turns cold-start personalization from an open-ended learning problem into a small calibration problem.

---

## 3. Candidate latent structure: present value, option value, awareness value

The first 30-case elicitation pilot suggests that the four dispositions may not be four unrelated classes. They can be interpreted through at least three kinds of value plus runtime context:

$$
\boxed{
AttentionPolicy \approx f(V_{now}, V_{future}, V_{aware}, R)
}
$$

where:

- $V_{now}$ — **current processing value**: is it worth spending substantial human cognition now?
- $V_{future}$ — **future option value**: if not worth deep processing now, is it valuable to preserve the option by monitoring future evidence?
- $V_{aware}$ — **awareness value**: even without deep processing or future monitoring, is knowing that the event/concept exists useful?
- $R$ — runtime constraints such as deadline, interruptibility, available attention, cognitive capacity, and overlap with active work.

A candidate interpretation is:

$$
\begin{aligned}
ENGAGE &: V_{now}\ \text{high} \\
WATCH &: V_{now}\ \text{not high enough, but}\ V_{future}\ \text{high} \\
AWARE &: V_{now},V_{future}\ \text{low, but}\ V_{aware}>0 \\
DROP &: V_{now},V_{future},V_{aware}\ \text{all low}
\end{aligned}
$$

This is a **candidate explanatory model**, not yet a frozen production equation.

### WATCH as preserved optionality

A particularly useful interpretation is:

$$
\boxed{WATCH = preserve\ valuable\ optionality}
$$

WATCH does not simply mean “medium importance.” It means that current human processing is not justified, but losing the future branch would be costly. The system therefore assumes responsibility for future attention.

This is consistent with the Phase III meaning of WATCH as a future attention obligation.

---

## 4. Relationship to cognitive transition $\Delta$

The elicitation pilot reinforces the v2.1 separation:

$$
\boxed{CognitiveChange \neq AttentionAction}
$$

In particular, the pilot produced repeated judgments where:

$$
\Delta=\varnothing
$$

but the desired disposition was AWARE rather than DROP.

Candidate hypothesis:

$$
\boxed{\Delta=\varnothing \not\Rightarrow DROP}
$$

Instead:

$$
\Delta=\varnothing
\Rightarrow
\begin{cases}
DROP & \text{no useful awareness value} \\
AWARE & \text{worth knowing, but no cognitive write / watch obligation}
\end{cases}
$$

This is intentionally **not yet a production change**. It must first be tested against the frozen Oracle-Δ Attention Policy baseline.

Likewise, novelty alone does not imply monitoring:

$$
\boxed{Novelty \neq WatchWorthiness}
$$

and:

$$
\boxed{OPEN\_NEW \neq WATCH}
$$

A new branch can rationally be AWARE, WATCH, or ENGAGE depending on present value, future option value, importance/coupling, and runtime.

---

## 5. Shared policy prior plus lightweight personalization

The first pilot suggests a stronger personalization architecture than either a fully fixed universal policy or a user-specific model trained from scratch.

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

### SharedPolicyPrior

A common policy structure for professional knowledge workers. Candidate shared dimensions include:

- cognitive-change operation (`REINFORCE`, `CHALLENGE`, `OPEN_NEW`, `NONE`)
- change magnitude
- target importance
- epistemic strength
- current processing value
- future option value / tail opportunity or tail risk
- awareness value
- runtime cost and interruption constraints

The key hypothesis is that users may share the **function family** while differing mainly in coefficients, thresholds, and a small number of rare dimensions.

A schematic parameterization is:

$$
\theta_u =
(w_{challenge},
 w_{novelty},
 w_{importance},
 w_{future},
 w_{interrupt},
 \ldots)
$$

This is a modeling hypothesis, not a commitment to a linear model or these exact weights.

### QuestionnaireCalibration

A short controlled questionnaire can locate the user inside the shared policy family on day one.

The initial pilot used 30 cases. A mature product may need fewer if the questions are selected for high information gain.

### TrajectoryResidual

Real-world interaction then corrects residual error rather than learning the entire policy from scratch.

This is preferable to pure behavioral inference because an observed non-click/non-open is confounded by time, fatigue, interface visibility, forgetting, and competing work. Controlled counterfactual judgments provide cleaner causal information.

---

## 6. First elicitation pilot: 30 controlled judgments

The Phase II pilot used five six-case groups. The objective was not population validation; it was to expose the user's decision boundaries while keeping the task easy to answer.

Disposition mapping used in the questionnaire:

```text
A = DROP
B = AWARE
C = WATCH
D = ENGAGE
```

### Group 1 — no cognitive change

| Case | Controlled scenario | Gold |
|---|---|---|
| 1 | Unrelated small AI-company CEO change; no research/decision impact | DROP |
| 2 | Important organizational change at a long-followed frontier lab; no current cognitive change | AWARE |
| 3 | Popular model minor upgrade; useful to know, no current model change | AWARE |
| 4 | Viral robotics marketing release with no new evidence | AWARE |
| 5 | Benchmark maintenance-team change; no current technical/rule change | DROP |
| 6 | Fifth media retelling of an already-read original robotics release | AWARE |

Observed structure: $\Delta=NONE$ did **not** collapse to a single disposition. Four of six cases were AWARE.

### Group 2 — REINFORCE

| Case | Controlled scenario | Gold |
|---|---|---|
| 7 | Strong reliable support for a peripheral research judgment | WATCH |
| 8 | Same strength/support, related but non-core judgment | WATCH |
| 9 | Same strength/support, core research model | ENGAGE |
| 10 | Small reinforcement of an important question | AWARE |
| 11 | Material reinforcement of the same important question | WATCH |
| 12 | Strong result moves a core model from “likely” toward “high confidence” | ENGAGE |

Observed structure: both target importance and change magnitude affected allocation.

### Group 3 — CHALLENGE

| Case | Controlled scenario | Gold |
|---|---|---|
| 13 | Credible conflict with a peripheral judgment | WATCH |
| 14 | Same conflict with a moderately important judgment | ENGAGE |
| 15 | Same conflict with a core hypothesis | ENGAGE |
| 16 | Small anomaly against a core view; insufficient to overturn it | WATCH |
| 17 | Good experiment suggests a core view needs qualification | ENGAGE |
| 18 | Multiple independent high-quality experiments conflict with a core assumption | ENGAGE |

Observed structure: CHALLENGE appears to receive a lower ENGAGE threshold than equivalent REINFORCE, but magnitude still matters.

### Group 4 — OPEN_NEW

| Case | Controlled scenario | Gold |
|---|---|---|
| 19 | Interesting new concept, far from current field, little action value | AWARE |
| 20 | New idea somewhat related to current work, weak initial evidence | WATCH |
| 21 | Highly relevant new direction, only one strong demo and no independent validation | ENGAGE |
| 22 | Same direction with formal paper and substantial data, no independent replication | ENGAGE |
| 23 | Highly relevant new direction with multiple independent evidence sources; may change experiments | ENGAGE |
| 24 | Cross-domain framework offers a genuinely new way to understand the current problem | ENGAGE |

Observed structure: generative potential / future option value can justify high attention before evidence maturity is maximal; novelty by itself cannot.

### Group 5 — same valuable information, different runtime

Cases 25–30 hold the information-side judgment approximately fixed: strong evidence materially reinforces a core research model.

| Case | Runtime | Gold |
|---|---|---|
| 25 | Normal capacity, no urgent task | ENGAGE |
| 26 | Ordinary material due tomorrow; low willingness to be interrupted | WATCH |
| 27 | Camera-ready due in one hour; low interruptibility | WATCH |
| 28 | Same deadline, but the information directly affects the submission's core technical judgment | ENGAGE |
| 29 | No deadline, but severe fatigue / very low cognitive capacity | AWARE |
| 30 | No urgent deadline, only ~5 minutes of available research attention | WATCH |

Observed structure: runtime can downshift a high-value item, while direct overlap with active work can restore immediate attention.

---

## 7. Boundary-case rationales and test-retest signal

Four cases initially landed near a boundary. The user later made a single choice and explained the reasoning, then independently re-answered the same four cases with the same labels.

### Case 8 — WATCH

Strong evidence supports a non-core but related judgment. The user does not want to spend deep attention now, but considers the item potentially useful to future research and wants the system to keep monitoring it.

Interpretation: current processing value is below ENGAGE, while future option value is high.

### Case 12 — ENGAGE

A strong new result materially increases confidence in a core research model. This justifies immediate attention for both instrumental value and user utility/positive confirmation value.

Interpretation: current processing value is clearly above the ENGAGE threshold.

### Case 16 — WATCH

A small anomaly against a core model is unlikely to deserve major current attention because most anomalies do not produce paradigm shifts. But rare anomalies can have very large tail value, so the system should not lose the branch and should watch for follow-up evidence.

Interpretation: modest current value, high tail option value.

### Case 19 — AWARE

A genuinely new concept is far from the user's field and has no current action value. Neither the user nor the system should invest ongoing attention now; knowing that it exists is sufficient.

Interpretation: low current value, low future option value, positive awareness value.

The second pass returned the same labels:

```text
8  WATCH
12 ENGAGE
16 WATCH
19 AWARE
```

This is only a small, immediate test-retest signal, but it supports the existence of a stable latent policy rather than purely random local choices.

---

## 8. What this does and does not establish

This pilot establishes an **engineering method worth testing**:

> controlled counterfactual judgments can expose stable attention-allocation structure with much less burden than explicit policy programming.

It does **not** yet establish:

- that the candidate latent dimensions are complete;
- that the current user represents all professional knowledge workers;
- that 30 questions are sufficient for every user;
- that 15 questions are sufficient;
- that one mathematical form is optimal;
- that the current production scheduler should immediately adopt $V_{now}$ or $V_{future}$ as new schema fields.

The current evidence is explicitly:

```text
N = 1 exploratory elicitation pilot
30 controlled judgments
4 boundary judgments re-tested immediately with identical labels
```

Population claims require multi-user evaluation.

---

## 9. Validation program

The next validation sequence is deliberately conservative:

```text
1. Freeze this user's 30 Human Gold judgments.
2. Feed the corresponding frozen Δ / Runtime cases to the current production Attention Policy.
3. Measure exact disposition, distance, false DROP, over/under-attention, and critical under-attention.
4. Attribute systematic mismatches to specific policy assumptions.
5. Only then decide whether production semantics must change.
6. Test the questionnaire with additional professional users before claiming a shared universal prior.
```

Important candidate failures to test first:

- strict `Δ=NONE → DROP` may under-allocate AWARE;
- `target_importance` may have insufficient causal effect;
- current policy may lack an explicit representation of future option value;
- `cognitive_capacity` and `available_attention_minutes` may be recorded but behaviorally inert;
- high-value OPEN_NEW may be under-allocated when evidence is immature despite high generative potential.

---

## 10. Candidate personalization architecture for a future v2.2

If the Oracle-Δ baseline and later multi-user studies support the above structure, a future cognitive/attention model may extend the current v2.1 personalization statement from:

$$
Universal\ Engine + User\ State\ K_t
$$

to:

$$
\boxed{
Universal\ Cognitive\ Engine
+
User\ Cognitive\ State
+
Calibrated\ Attention\ Policy
}
$$

with:

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

This is a **v2.2 candidate insight**, not a v2.2 frozen baseline.

No production scheduler, transition semantics, Kernel mutation rule, or Human Gold contract is changed by this document.

---

## 11. Decision

Record the discovery now; do not prematurely rewrite the constitution.

$$
\boxed{
Document\ the\ method
\rightarrow
Freeze\ Gold
\rightarrow
Measure\ current\ Policy
\rightarrow
Attribute\ errors
\rightarrow
Only\ then\ consider\ v2.2
}
$$
