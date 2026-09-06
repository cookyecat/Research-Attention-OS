# Research Attention OS — Standing Attention Jurisdiction

Status: **D SEMANTIC DEFINITION — FROZEN / CLOSED BASELINE**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Related: `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`, `12_STANDING_RADAR_FIT_ESTIMATOR_STUDY.md`, `14_STANDING_RADAR_FIT_V2_SEMANTIC_REPAIR.md`, `15_STANDING_RADAR_ANCHOR_GENERALIZATION.md`, `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`

---

## 1. Canonical meaning of D

The intuitive definition remains unchanged:

> **D asks: Is this event part of a world the user wants RAOS to monitor on a standing basis?**

The formal interpretation is **Standing Attention Jurisdiction**.

Let:

- $E$ be an event;
- $u$ be the user;
- $Sem(E)$ be the semantic representation of the stated event;
- $\mathcal R_u=\{\rho_1,\rho_2,\ldots,\rho_n\}$ be the user's stable Standing Radar Clauses.

Define the user's standing-attention jurisdiction:

$$
\boxed{
\mathcal J_u
=
\left\{
E\mid
\exists\rho_i\in\mathcal R_u,\;
\rho_i(Sem(E),u)=1
\right\}
}
$$

Then:

$$
\boxed{
D(E,u)=\mathbf 1[E\in\mathcal J_u]
}
$$

Human-language contract:

> **Ignoring how important or popular this particular event is, does it satisfy at least one stable semantic condition that makes it part of the user's standing attention jurisdiction?**

`Standing Attention Jurisdiction` is the theoretical/formal interpretation. `Standing Radar Fit` remains the engineering variable name. They are not separate variables.

---

## 2. Standing Radar Clauses

A Standing Radar Clause $\rho_i$ is a stable applicability condition:

$$
\rho_i(Sem(E),u)\in\{0,1\}
$$

It need not be a domain label. A clause may match a substantive:

- topic or technical field;
- actor / organization / person;
- work / product / content object;
- place or governance scope;
- stable personal affiliation or relationship.

These are examples of semantic anchors, not required ontology classes.

The important abstraction is the **clause**, not the object type.

Examples in abstract form:

```text
- robotics is itself a substantive event topic/object;
- a standing-monitored AI organization is a substantive actor;
- a monitored film work/creator is substantively involved;
- a stable hometown/local-governance scope is substantively involved;
- an institution with a stable direct-family affiliation is substantively involved.
```

Do not introduce separate D1/D2/D3 variables for these cases.

---

## 3. Substantive involvement

A standing anchor must be substantively involved in the event.

Incidental mention is insufficient:

$$
\boxed{Mention(anchor)\neq SubstantiveMatch(anchor)}
$$

The earlier invariant remains:

$$
\boxed{Using\ AI\ method\neq Being\ an\ AI\ event}
$$

An event may have multiple substantive anchors/facets. Do not collapse it to one dominant domain.

A useful semantic representation is:

$$
\boxed{
Sem(E)\rightarrow A_s(E)=\{\text{substantive radar anchors in }E\}
}
$$

and:

$$
\boxed{
D(E,u)=1
\iff
\exists a\in A_s(E): Match(a,\mathcal R_u)
}
$$

This is an implementation view of the jurisdiction definition, not a new variable.

Important qualification from the final v3 measurement: the anchor representation is a useful diagnostic view, but it must not become a stronger gate than the clause itself. The canonical model remains direct clause applicability over $Sem(E),u$. A stable affiliation, for example, may be a relation used by a clause even when the relation is not naturally represented as a standalone event object.

---

## 4. Exclusions

Standing exclusions are **scope guards**, not negative votes and not vetoes.

They prevent over-broad inherited matches such as:

```text
"commercial space" -> automatically treating every space event as monitored
"biomedicine"      -> automatically treating every medical event as monitored
"film production"  -> automatically treating every workflow update as a monitored film event
```

They must not erase an independently valid substantive standing clause.

$$
\boxed{
Exclusion=ScopeGuard,\quad Exclusion\neq Veto
}
$$

---

## 5. Standing vs temporary relevance

D is a **standing** signal.

A stable topic/entity/place/affiliation can belong to the jurisdiction. A short-lived project, trip, transient curiosity, or one-off task does not automatically become D.

$$
\boxed{StandingRadar\neq CurrentProjectContext}
$$

Temporary relevance belongs elsewhere in runtime/project context unless later promoted through explicit user calibration.

---

## 6. D / S / P separation

The three variables have distinct physical dependencies:

$$
\boxed{D=D(E,u)}
$$

> Is this event inside the user's standing attention jurisdiction?

$$
\boxed{S=S(E)}
$$

> Does the underlying event itself have material consequence?

$$
\boxed{P=P(E,t)}
$$

> At time $t$, has the event entered or clearly begun entering public / industry attention?

For the no-cognitive-change AWARE gap:

$$
\boxed{
AWARE(E,u,t)
=
S(E)\land\bigl(D(E,u)\lor P(E,t)\bigr)
}
$$

Human-language contract:

> **For information with no cognitive update, surface AWARE only when the event itself has real substance and it either belongs to the user's standing world or has entered the public-attention radar.**

---

## 7. Implementation policy for Phase II-B

Preferred implementation family:

$$
\boxed{
NaturalLanguageStandingRadarClauses
+
SemanticMatching
}
$$

Do not introduce:

- numeric domain weights;
- a large domain taxonomy;
- a person/company/place relationship ontology;
- extra D sub-variables;
- case-specific rules copied from prior holdouts.

The final v3 fresh measurement did not certify the current LLM estimator: it scored 0.70 exact with two clear clause-application failures and one likely human-policy boundary. The result is recorded in `17_STANDING_RADAR_FIT_V3_FINAL_VALIDATION.md`.

That estimator result does **not** invalidate the semantic model. The failures are attributable to imperfect application of explicit clauses, not evidence that D requires a different variable decomposition.

Therefore the semantic research question is closed for Phase II-B. Do not create another synthetic D benchmark now. Revisit estimator implementation only when integrated dogfooding exposes a repeated real-world failure pattern.

---

## 8. Frozen conclusion

$$
\boxed{
D(E,u)=\mathbf 1[E\in\mathcal J_u]
}
$$

with:

$$
\boxed{
\mathcal J_u
=
\{E\mid\exists\rho_i\in\mathcal R_u,\rho_i(Sem(E),u)=1\}
}
$$

is the Phase II-B semantic baseline for D.

Current project pointer:

```text
D semantic model       CLOSED / FROZEN
D estimator v3         NOT CERTIFIED; attributable residuals preserved
Next research variable S = Material Consequence
```
