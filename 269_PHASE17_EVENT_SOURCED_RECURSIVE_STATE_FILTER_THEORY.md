# Phase 17 — Event-Sourced Recursive State Filter Theory V1.0

Status: **THEORY FROZEN / IMPLEMENTATION EVAL-FIRST**  
Date: 2026-09-21

## 1. Product statement

> **RAOS maintains the dynamic state of world events and interrupts the human only when that state crosses a cognitive or attention boundary.**

中文：

> **RAOS 维护世界事件的动态状态，并只在状态跨过认知/注意力边界时打扰人。**

RAOS is therefore not an article classifier. Source is evidence. Event is the evolving world representation. Decision is computed from current EventState relative to a Kernel/context. Attention is a stateful lifecycle over those decisions.

## 2. Four-layer separation

The canonical dynamic Event model is:

```text
Event Identity
+
Current EventState
+
Immutable History
+
Current EventDecision / Attention outside Event
```

More formally:

\[
E_t = (I,\;S_t,\;H_{\le t})
\]

where:

- \(I\): coarse Event identity descriptor;
- \(S_t\): current sufficient EventState;
- \(H_{\le t}\): append-only evidence/revision history.

Decision and Attention are external functions:

\[
D_t = F(S_t,K_t,C_t)
\]

\[
A_t = G(D_t,D_{t-1},A_{t-1},C_t)
\]

Permanent separation:

```text
History / Evidence
!= Current EventState
!= EventDecision
!= Attention
```

## 3. Event Sourcing correspondence

RAOS adopts the mature Event Sourcing separation:

```text
immutable event/evidence log
        ↓
recursive materialized state
```

In RAOS:

```text
EventHistory / EventRevision / Source evidence
        ↓
Current EventState
```

History exists for audit, explanation, replay and reconstruction.

Normal online cognition must not require replaying the full historical evidence bag on every Source arrival.

## 4. Recursive state-estimation correspondence

RAOS adopts the recursive filtering form used by mature state-estimation systems:

\[
\boxed{
S_{t+1}=U(S_t,e_{t+1})
}
\]

where \(e_{t+1}\) is newly admitted audited evidence.

The key property is sufficiency:

> the previous posterior/current state is the compact carrier of past evidence; new evidence updates that state instead of forcing full-history recomputation.

This is the conceptual bridge from Bayesian/recursive filtering to RAOS.

RAOS does not claim that EventState is Gaussian or that the Kalman equations themselves apply. The inherited principle is recursive sufficient-state estimation.

## 5. Minimal EventState

Phase17 freezes:

\[
\boxed{
S_t = (W_t,Q_t)
}
\]

### 5.1 WorldState \(W_t\)

What RAOS currently believes about the Event itself.

WorldState is deliberately smaller than Event Identity. Identity fields such as actors, coarse action/episode, object, time context and location remain on the Event identity layer and are not duplicated into dynamic State.

The target WorldState contains only a compact current projection:

```text
current synopsis
current status / phase
effective time
references to the audited semantic units that currently define the projection
```

The semantic-unit references are important: immutable history may keep an old claim and its later correction, while Current WorldState can point only to the currently active supported units. An unresolved contradiction may keep both sides active. This avoids creating permanent ontology fields named correction/supersession/contradiction.

### 5.2 EvidenceState \(Q_t\)

What RAOS currently knows about the structural support for WorldState:

```text
authorized member-source structure
independence / provenance dependence
secondary-report structure
support/provenance digest
```

EvidenceState is not equivalent to Source count.

A repost and an independent reproduction must not contribute identically.

Algorithm-internal recursive variables such as arrival momentum, decay parameters, last-applied observation identity, or hysteresis memory are **Filter/Controller state**, not WorldState or EvidenceState. They are versioned separately once selected by benchmark evidence.

## 6. Probabilistic identity remains outside EventState

Whether a new EventCandidate A is the same event as existing Event B is a relational hypothesis:

\[
P(H_{same}(A,B)=1\mid Evidence)
\]

This belongs to Representation / Event Resolver.

It is NOT:

- EventState;
- Event.confidence;
- Attention score.

The commitment path remains:

```text
epistemic SAME_EVENT belief
-> commitment policy
-> SAME_EVENT / DIFFERENT_EVENT / UNCERTAIN
-> topology update
```

## 7. Recursive Event State Filter

The implementation factorization is:

\[
\boxed{
\Delta_t=\Phi(S_t,e_{t+1})
}
\]

\[
\boxed{
S_{t+1}=R(S_t,\Delta_t)
}
\]

\[
\boxed{
D_{t+1}=F(S_{t+1},K_t,C_t)
}
\]

Interpretation:

- \(\Phi\): project newly audited evidence into a proposed state delta;
- \(R\): deterministic or tightly constrained reducer;
- \(F\): existing cognition/decision machinery.

This factorization is preferred to asking an LLM to rewrite an entire EventState from all historical prose on every update.

Algorithm-specific notions such as enrichment, correction, contradiction and supersession may be internal outputs of \(\Phi\), but they are not Event ontology fields.

## 8. Evidence accumulation

RAOS adopts evidence accumulation as an Attention-system principle:

> repeated observations contribute to a stateful evidence signal; Decision is not independently reclassified from scratch for every article.

But accumulation is over decision-relevant evidence structure, not raw Source count.

A generic bounded/decaying observation channel may use a first-order leaky integrator:

\[
\boxed{
M_{t+1}=\rho^{\Delta t}M_t+I_{t+1},
\qquad 0<\rho<1
}
\]

where:

- \(M_t\): current observational momentum;
- \(I_{t+1}\): newly admitted information/evidence innovation;
- \(\rho\): decay parameter.

This is an algorithmic primitive, not a claim that one specific \(\rho\) or innovation definition is already correct.

The purpose of leakage is to avoid monotonic unbounded accumulation.

## 9. Hysteretic Attention Controller

Attention is stateful.

RAOS adopts hysteresis as a robustness principle:

```text
up-transition threshold
>
down-transition threshold
```

so small signal fluctuations near a boundary do not cause:

```text
AWARE -> WATCH -> AWARE -> WATCH -> ...
```

A generic transition law is:

\[
\boxed{
A_{t+1}=\mathcal H(A_t,D_{t+1},C_t)
}
\]

where \(\mathcal H\) has memory through \(A_t\).

The exact scalarization/boundaries are not frozen here. They must be learned or selected through benchmark/ablation.

## 10. Three dynamic laws + one conservation principle

RAOS dynamic Event theory is intentionally compact.

### Law 1 — recursive world-state update

\[
\boxed{
S_{t+1}=U(S_t,e_{t+1})
}
\]

### Law 2 — cognition/decision

\[
\boxed{
D_{t+1}=F(S_{t+1},K_t,C_t)
}
\]

### Law 3 — hysteretic Attention lifecycle

\[
\boxed{
A_{t+1}=\mathcal H(A_t,D_{t+1},C_t)
}
\]

### Conservation principle

```text
History is append-only.
Current State is revisable.
```

These are architecture laws. Concrete update and threshold algorithms remain replaceable modules.

## 11. Implementation mapping

Reuse existing RAOS substrate:

```text
Event
-> stable Event identity + materialized read model

EventRevision
-> immutable revision/state history

EventMembershipAssertion / EventSource
-> evidence membership/topology

EventEvidenceFrame
-> audited semantic evidence

SourceGraph
-> provenance dependence / independence

AttentionPlan(EVENT)
-> historical EventDecision/Attention snapshots

current_attention_plans()
-> current Event Attention projection
```

No new EventDecision table is required.

Phase17 should first encode a versioned `event-state-v0.1` snapshot in EventRevision payloads rather than add algorithm-specific Event columns.

## 12. Jev Benchmark semantics

Jev benchmark has four distinct layers.

### World Trace

RAOS-observed acquisition trace:

```text
44 deduplicated ExternalInformationItems
2026-09-16 -> 2026-09-20
28 Weibo
15 Bilibili
1 Substack
daily arrivals: 3 -> 8 -> 15 -> 8 -> 10
```

This is an observed sample, not population-level global popularity ground truth.

### Event Gold

Fixed coarse identity:

```text
t0,t1,t2,t3 -> SAME_EVENT
```

Current real-model Event Processor V1 passes this gate.

### Human Gold

Profile-scoped subjective label:

```text
profile = user-primary-v0.1

AWARE
-> WATCH
-> WATCH
-> ENGAGE
```

This is not a universal normative Attention trajectory.

A different Kernel/user may legitimately produce a different trajectory from the same World Trace.

### Algorithm Output

Candidate U/F/H systems are evaluated against the same frozen World Trace, Event Gold and profile-scoped Human Gold.

The benchmark must not be rewritten to fit the chosen algorithm.

## 13. Phase17 research objective

The objective is not to invent a new state-estimation theory.

It is to instantiate mature principles in RAOS with the smallest correct contracts:

```text
Event Sourcing
+
Recursive State Estimation
+
Evidence Accumulation
+
Hysteretic Attention
```

Then ablate the replaceable implementation details against longitudinal benchmark cases.

The leading engineering form is:

```text
Event-sourced Recursive State Filter
+
Hysteretic Attention Controller
```

Production wiring remains gated on controlled and longitudinal benchmark evidence.
