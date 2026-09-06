# Collective Attention Salience (P)

Status: **P SEMANTIC CONTRACT — FROZEN / CLOSED BASELINE**  
Date: 2026-09-07  
Phase: **II-B Attention Policy Calibration**

> Purpose: freeze the semantic meaning of `P` before estimator design. This document defines the theoretical variable. It does not prescribe a particular observable-data source, lookup table, LLM prompt, threshold, or production implementation.

---

## 1. Canonical definition

For an event `E` at time `t`:

$$
\boxed{
P(E,t)
=
\text{Collective Attention Salience of }E\text{ at }t
}
$$

Human-language contract:

> **P judges whether, at the current time, an event has already formed, or is clearly forming, a salient state of genuine collective attention within the event's objective attention constituency. Attention is interpreted relative to the scale of that constituency and has temporal inertia.**

Chinese compression:

> **P 判断一件事在当前时刻，是否已在它客观对应的受众共同体中形成、或明显正在形成显著的真实共同注意；注意力按该共同体尺度归一，并具有时间惯性。**

P is independent of:

- whether the user personally cares (`D`), and
- whether the event itself has material consequence (`S`).

Therefore the theoretical dependency remains:

$$
\boxed{P=P(E,t)}
$$

not:

$$
P=P(E,u,t)
$$

---

## 2. Objective Attention Constituency

Let:

$$
\boxed{
\mathcal G_E
=
Constituency(Sem(E))
}
$$

where `G_E` is the **Objective Attention Constituency** of event `E`.

Definition:

> **`G_E` is the reference audience/community that is implied by the event's own semantics and within which attention penetration should naturally be judged. It must be identifiable before inspecting who currently happens to be discussing the event, and it must be independent of the user's preferences.**

Examples:

- an internal expense-system change -> the directly relevant employees of that organization;
- a city transit change -> the relevant local commuters / city public;
- a niche competitive-game rule change -> the active community of that game;
- a semiconductor process result -> the relevant semiconductor research/industry community;
- an AI-safety technical development -> the relevant AI-safety research/industry community;
- a broad mass-cultural event -> the broad social public.

Critical anti-gaming invariant:

$$
\boxed{
\mathcal G_E\text{ must be selected from event semantics, not chosen after observing attention in order to maximize penetration.}
}
$$

A small group of people who happen to be discussing an event is not automatically the correct denominator.

---

## 3. Reference-scale normalization

Absolute attention volume is not P.

A theoretical attention-penetration quantity can be written as:

$$
\boxed{
R_E(t)
=
\frac{1}{|\mathcal G_E|}
\sum_{i\in\mathcal G_E} a_i(E,t)
}
$$

where `a_i(E,t)` represents the genuine attention contributed by constituency member `i` to event `E` at time `t`.

This is a conceptual model, not a requirement that RAOS literally observe every individual or calculate an exact population fraction.

Core interpretation:

> **Attention is judged relative to the event's correct reference constituency, not by brute-force normalization against the total population.**

Therefore:

$$
\boxed{AbsoluteAttention\neq P}
$$

and:

$$
\boxed{SmallConstituency\neq LowP}
$$

A niche field may have high P when most of the relevant field is attending, even if the general public is unaware. Conversely, a larger absolute number of observers can still imply low P if it represents weak penetration into the correct constituency.

---

## 4. Genuine attention is not exposure or synthetic activity

The numerator in the conceptual model is genuine attention, not raw information-system activity.

Calibration supports the following invariants:

$$
\boxed{Exposure\neq Attention}
$$

$$
\boxed{ViewCount\neq Attention}
$$

$$
\boxed{SyntheticActivity\neq Attention}
$$

Examples of weak evidence by themselves:

- purchased impressions;
- forced or passive exposure;
- very short autoplay views;
- bot-generated or highly duplicated posting volume.

Examples of stronger genuine-attention evidence:

- sustained reading/viewing;
- active search;
- comments / replies / discussion;
- saves / shares / voluntary propagation;
- independent professional follow-up;
- multiple major institutions or domain communities reallocating discussion toward the event.

These are evidence forms, not mandatory gates and not a fixed weighted formula.

---

## 5. Current OR emerging salience

P is not an attention-growth variable.

A topic can be P=1 while attention is stable at a high level:

$$
\frac{dA}{dt}\approx0
\not\Rightarrow
P=0
$$

A topic can also become P=1 before absolute attention is large when the evidence clearly indicates that collective attention is rapidly forming.

Therefore:

$$
\boxed{
P=CurrentSalience\ \lor\ EmergingSalience
}
$$

Baseline deviation and velocity may be useful estimator evidence for **entry**, but neither is the definition of P.

Consequently:

$$
\boxed{BaselineDeviation\neq Necessary(P)}
$$

$$
\boxed{PositiveAttentionVelocity\neq Necessary(P)}
$$

---

## 6. Temporal inertia

P is a latent attention state, not a direct copy of a noisy short-window measurement.

Conceptually:

$$
\boxed{
P(E,t)
=
LatentSalience(R_E(\le t))
}
$$

Short-term attention decline does not by itself imply that the collective-attention state has disappeared.

Calibration supports:

$$
\boxed{
ShortTermNegativeDerivative\neq AttentionLoss
}
$$

A previously salient event may remain salient through temporary declines. Exit from P=1 requires evidence of real state decay, such as sustained reduction toward ordinary baseline and disappearance from the relevant constituency's active attention space.

A future engineering approximation may use smoothing, state memory, or hysteresis, e.g. conceptually:

$$
\theta_{on}>\theta_{off}
$$

but no specific dynamic equation or threshold is part of the frozen semantic contract.

---

## 7. P is Collective Attention, not narrow public opinion

The term "public attention" is too narrow if interpreted as attention by the entire general population.

P includes genuine collective attention inside the event's correct objective constituency, which may be:

- broad public;
- geographic public;
- professional / scientific field;
- industry community;
- product / game / cultural community;
- an organization-internal audience, when that internal audience is genuinely the event's semantic constituency.

P does **not** require:

- nationwide awareness;
- mass-media coverage;
- majority social penetration;
- positive or negative sentiment;
- agreement;
- controversy;
- intrinsic importance.

Accordingly:

$$
\boxed{Sentiment\neq P}
$$

$$
\boxed{Stance\neq P}
$$

$$
\boxed{IntrinsicSignificance\neq P}
$$

---

## 8. Orthogonality with D and S

The three AWARE variables have different reference frames.

### D — Standing Attention Jurisdiction

$$
\boxed{D=D(E,u)}
$$

Reference frame: **the user's standing attention jurisdiction**.

Question:

> Is this event part of a world the user wants RAOS to monitor on a standing basis?

### S — Material Consequence

$$
\boxed{S=S(E)}
$$

Reference frame: **consequential shared world systems**.

Question:

> Does the event itself materially disturb a consequential shared system?

### P — Collective Attention Salience

$$
\boxed{P=P(E,t)}
$$

Reference frame: **the event's objective attention constituency**.

Question:

> Has genuine collective attention formed, or is it clearly forming, within the event's natural reference audience/community?

The normalization references are intentionally different:

$$
\boxed{
D:\ user
\qquad
S:\ consequential\ shared\ systems
\qquad
P:\ objective\ attention\ constituency
}
$$

Legal combinations include:

- `S=0, P=1`: a trivial/private/local event can dominate the attention of its natural audience without material shared-system consequence;
- `S=1, P=0`: a materially important event can exist before its relevant community notices;
- `D=0, P=1`: an event outside the user's standing radar can still have strong collective attention in its own objective constituency;
- `D=1, P=0`: an event can belong to the user's standing radar before it attracts collective attention.

---

## 9. Human calibration evidence

Two rounds of human calibration were used to identify the latent boundaries before semantic freeze.

### Round 1 — PC1–PC12

Human labels:

```text
PC1   SALIENT
PC2   SALIENT
PC3   SALIENT
PC4   SALIENT
PC5   NOT_SALIENT
PC6   SALIENT
PC7   SALIENT
PC8   NOT_SALIENT
PC9   SALIENT
PC10  SALIENT
PC11  NOT_SALIENT
PC12  SALIENT
```

Key falsifications / findings:

- stable high attention can remain salient without growth;
- a single large source can still generate real collective attention if many humans genuinely attend;
- purchased exposure is not attention;
- bot activity is not attention;
- domain-community salience can be P=1 without broad-public salience;
- a small author/lab cluster is not the correct constituency for a field-facing paper;
- flash attention can be salient;
- early emerging attention can be salient.

### Round 2 — PC13–PC24

Human labels:

```text
PC13  SALIENT
PC14  NOT_SALIENT
PC15  SALIENT
PC16  SALIENT
PC17  SALIENT
PC18  NOT_SALIENT
PC19  SALIENT
PC20  NOT_SALIENT
PC21  NOT_SALIENT
PC22  SALIENT
PC23  SALIENT
PC24  SALIENT
```

Key findings:

- the same absolute number of attentive people can imply opposite P labels under different constituency scales;
- a legitimately small constituency can have P=1;
- organization-internal constituencies are valid when the event itself is truly internal to that audience;
- short-term decline does not erase an established attention state;
- sustained decay can end salience;
- passive high-volume views can remain NOT_SALIENT;
- lower-volume but active, sustained, voluntary attention can be SALIENT;
- geographic reference constituencies are valid;
- humans can infer high penetration from structural evidence even without exact audience counts.

---

## 10. Rejected models

The following models are rejected as definitions of P:

### 10.1 Raw-volume model

$$
P=\mathbf1[Volume>\theta]
$$

Rejected because raw posting, view, impression, or discussion counts do not normalize to the correct constituency and can be synthetic or passive.

### 10.2 Total-population normalization

$$
P\propto \frac{Attention}{TotalPopulation}
$$

Rejected because professional, geographic, niche, and internal constituencies can legitimately be the correct reference scale.

### 10.3 Baseline-deviation-only model

$$
P=\mathbf1[A/Baseline>\theta]
$$

Rejected because stable high salience can remain P=1 without an abnormal increase.

### 10.4 Growth-only model

$$
P=\mathbf1[dA/dt>\theta]
$$

Rejected because current salience does not require growth, and short-term decline does not imply loss of salience.

### 10.5 Multi-source propagation as a mandatory gate

Rejected because one large source can already concentrate genuine attention from a large portion of the correct constituency.

### 10.6 General-public-only model

Rejected because field/domain/local/internal collective attention can be the correct P reference state.

---

## 11. Theory vs engineering

The theoretical P variable may not be directly measurable from RAOS's currently available data.

This does **not** alter the semantic definition.

The distinction is:

$$
\boxed{
Theory:\quad
P(E,t)=LatentSalience(R_E(\le t))
}
$$

versus:

$$
\boxed{
Engineering:\quad
\hat P
=
Estimator(
Sem(E),
ConstituencyPrior,
ObservableAttentionEvidence,
History
)
}
$$

The production estimator is an approximation to the frozen theoretical variable.

Future large-scale RAOS deployment may provide richer telemetry and improve the approximation without changing the P semantics.

---

## 12. Frozen research decision

```text
P variable name                       Collective Attention Salience
P semantic definition                 CLOSED / FROZEN
Objective Attention Constituency      FROZEN CONCEPT
Reference-scale normalization         FROZEN PRINCIPLE
Genuine attention vs exposure         FROZEN PRINCIPLE
Current OR emerging salience          FROZEN PRINCIPLE
Temporal inertia                      FROZEN PRINCIPLE
Exact constituency-size estimator     OPEN IMPLEMENTATION QUESTION
Exact attention numerator             OPEN IMPLEMENTATION QUESTION
Estimator architecture                NEXT
Fresh P Human Gold                    NOT YET CREATED
First scored P measurement            NOT RUN
```

Do not modify the semantic contract merely because current data cannot directly observe the theoretical numerator or denominator.

Do not introduce a large fixed ontology of constituencies solely to make implementation convenient.

Do not collapse P back into public-opinion sentiment, raw trend score, or total discussion volume.

---

## 13. Next research step

Move from semantic calibration to estimator modeling:

```text
P semantic contract FROZEN
        ↓
Design Objective Attention Constituency estimator / prior
        ↓
Design observable attention-evidence representation
        ↓
Design temporal-state / inertia approximation
        ↓
Freeze P estimator v1
        ↓
Create fresh P validation set
        ↓
Elicit and freeze fresh Human Gold
        ↓
Run first scored measurement exactly once
        ↓
Residual attribution
```
