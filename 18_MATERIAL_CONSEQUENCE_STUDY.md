# Research Attention OS — Material Consequence (S) Study

Status: **ACTIVE — SEMANTIC CALIBRATION**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Predecessor: `16_STANDING_ATTENTION_JURISDICTION.md`, `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`

---

## 1. Research question

S asks a different physical question from D and P:

> **Ignoring who the user is and ignoring how much public attention the event receives, does the underlying event itself have material consequence?**

Canonical intuitive definition:

$$
\boxed{S:\text{ 这件事本身有没有实质后果？}}
$$

Dependencies:

$$
\boxed{D=D(E,u)}
$$

$$
\boxed{S=S(E)}
$$

$$
\boxed{P=P(E,t)}
$$

The purpose of this study is to formalize and calibrate `S(E)` without leaking user interest (D) or public attention (P) into it.

---

## 2. Physical interpretation: counterfactual world-state difference

Let $E$ be the underlying event occurring around time $t$.

Conceptually compare two trajectories:

- $W^{E}_{t+\tau}$: the world state after the event;
- $W^{\neg E}_{t+\tau}$: the counterfactual world state if the event had not occurred.

Define the event-induced world-state difference:

$$
\boxed{
\Delta W_E(\tau)
=
Diff\left(W^{E}_{t+\tau},W^{\neg E}_{t+\tau}\right)
}
$$

Then the candidate semantic definition is:

$$
\boxed{
S(E)=1
\iff
\exists\tau\in H:\ Material\left(\Delta W_E(\tau)\right)=1
}
$$

where $H$ is a relevant consequence horizon.

Human-language interpretation:

> **If this event had not happened, would the resulting world be non-trivially different in a way that matters to the affected system, field, population, institution, market, knowledge state, or culture?**

This is a conceptual causal test, not a requirement to numerically simulate the world.

---

## 3. What counts as “world state”

`World state` is intentionally broader than physical objects. A material event may change, for example:

- technical capability or constraint;
- cost, resource availability, or economic incentives;
- risk or safety conditions;
- scientific knowledge or accepted evidence;
- institutional rules, legal constraints, or policy;
- operational behavior of a consequential system;
- social or cultural behavior/meaning;
- market structure or access.

These are examples of consequence types, not a new ontology and not separate S sub-variables.

---

## 4. Materiality is not prominence, novelty, quality, or popularity

Important invariants:

$$
\boxed{ActorProminence\neq S}
$$

A famous actor can produce a trivial event; an unknown actor can produce a material event.

$$
\boxed{TechnicalNovelty\neq S}
$$

Novelty matters only insofar as it creates a material consequence.

$$
\boxed{ArtifactQuality\neq S}
$$

A low-quality artifact can have large social/cultural consequence; a high-quality artifact can have little consequence.

$$
\boxed{PublicAttention\neq S}
$$

Public attention is P. S must be judged as if media volume, virality, and discussion level were hidden.

$$
\boxed{UserInterest\neq S}
$$

Standing interest is D. S must not ask whether the user personally cares.

---

## 5. Candidate explanatory lenses — NOT YET SCHEMA

Materiality may depend on properties such as:

- **Magnitude** — how large the causal change is;
- **Scope** — how broadly the consequences propagate;
- **Persistence** — how long / structurally the change remains.

These are candidate explanatory lenses only.

Do **not** yet implement:

$$
w_M M+w_S S+w_P P
$$

or any other weighted score.

Do not assume every material event must be large on all three lenses. A locally scoped event can still be material inside its affected system; a short event can be material if the immediate consequence is large.

The current Phase-II-B question is binary:

```text
MATERIAL
NOT_MATERIAL
```

Do not introduce LOW / MATERIAL / EXCEPTIONAL unless calibration evidence forces an ordinal representation.

---

## 6. Relation to the FJ4 D example

The OpenAI routine-administrative-reorganization example cleanly demonstrates why D and S must remain separate.

```text
OpenAI is the substantive event actor
    -> D = IN

routine non-strategic administrative reshuffle
    -> candidate S = NOT_MATERIAL
```

If $\Delta=\varnothing$ and P is also low, then:

$$
AWARE=S\land(D\lor P)=0
$$

so the final attention action can still be DROP even though D is IN.

This is expected behavior, not a contradiction.

---

## 7. Historical calibration evidence — DEVELOPMENT ONLY

Earlier S-only discussion already supports several boundary principles:

- actor prominence alone is neither necessary nor sufficient for S;
- a reproducible large reduction in inference cost can be MATERIAL even from an obscure actor;
- a tiny routine bugfix can be NOT_MATERIAL even from a major actor;
- a capability jump that changes the competitive/technical frontier can be MATERIAL;
- major generational model capability changes can be MATERIAL.

These examples are calibration/development evidence and must not later be reported as fresh S holdout performance.

---

## 8. Human calibration instrument

For each event, the human should answer only:

```text
MATERIAL
NOT_MATERIAL
```

using this question:

> **Erase the user's identity and erase public attention. If the event is true, does it create a non-trivial counterfactual difference in the affected world state?**

Do not ask:

- Do I care about it?
- Is the actor famous?
- Is it going viral?
- Is it novel or impressive?
- Would I click it?

Those questions belong to D, P, or downstream attention policy.

---

## 9. Calibration protocol

Execute in this order:

```text
Candidate S semantics
  -> controlled Human calibration
  -> inspect disagreements / latent rule
  -> freeze S semantic contract
  -> create fresh Human Gold after freeze
  -> implement S estimator
  -> first scored measurement
  -> residual attribution
```

Do not build the estimator before the semantic instrument is calibrated.

Initial controlled calibration template:

`eval/live/manifest.material_consequence_calibration.v1.yaml`

This set is development evidence only.

---

## 10. Current pointer

```text
D semantic research              CLOSED
D estimator residuals            PRESERVED AS DEBT
S intuitive definition           ESTABLISHED
S counterfactual formalization   CANDIDATE
S Human calibration              NOW
S estimator                      NOT STARTED
P study                          AFTER S
```
