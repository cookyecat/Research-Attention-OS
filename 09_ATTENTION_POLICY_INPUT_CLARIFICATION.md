# Attention Policy Input Clarification

Status: **SPEC RECOMMENDATION** (not implemented)  
Date: 2026-09-05  
Baseline: Cognitive Transition Model v2.1 (`08_COGNITIVE_TRANSITION_MODEL_V2.1.md`)  
Production inspected: `backend/app/services/scheduler.py` `route()`, `_reschedule()` in `pipeline.py`  
This document does not authorize Scheduler behavior change.

Canonical question:

> Given frozen cognitive judgment $\Delta_t$, what information may legitimately influence $A_t$?

Invariant this recommendation must preserve:

- Cognitive Change ≠ Attention Disposition
- Location ≠ Update Target
- $\Delta_t$ remains the only Cognitive Transition truth
- Changing $R_t$ must not change frozen AnalysisRun judgment
- Attention Policy may decide whether / when / how much attention to spend
- Attention Policy must not re-decide what cognition changed

---

## 1. Current Attention Policy causal input graph

Production claims `Attention Policy consumes CognitiveImpactAssessment directly`. That is only half true. `route()` first normalizes $\Delta_t$ from the assessment + frozen Locate matches, then still branches on `SchedulerFeatures` and `RuntimeView`.

```text
I_t
  → Extract → E_t  (claims, observations, marketing_heavy, evidence_maturity, …)
  → Locate  → L_t  (matches: node_type, score, structural, relevance_type)
  → Impact  → Δ_t  (primary CognitiveEffect: operation, target, change, epi, importance)
              plus assessment.attention_cost, exploration_candidate
  → projection → SchedulerFeatures  (debug + live branches)
  → independence_report → is_duplicate / source counts
  → text/LLM probes → threatens_active_work, foundational_paper, high_quality_technical

R_t (RuntimeView)
  → deadline_minutes, interruptibility     [live branches]
  → current_task, session_topic,
    available_attention_minutes,
    cognitive_capacity                     [persisted on AttentionPlan; unused by route()]

route() order (first match wins)
  1. features.is_duplicate                         → DROP
  2. tight deadline ∧ LOW interrupt ∧ ¬threaten    → WATCH
  3. features.threatens_active_work                → ENGAGE / PREEMPT
  4. select_primary_effect(normalized Δ_t) is None
       explore                                     → AWARE
       high_quality_technical ∨ foundational_paper → AWARE
       topic_relevance ≥ 0.25 ∧ ¬marketing_heavy   → AWARE
       else                                        → DROP
  5. primary target type DECISION                  → ENGAGE
  6. targeted ∧ meaningful ∧ important             → ENGAGE
       (uses Δ_t change/epi/importance; features.sources_conflict,
        disagreement, evidence_maturity, foundational, high_quality)
  7. targeted ∧ structural match ∧ change ≥ 0.4    → ENGAGE
  8. targeted ∧ change ≥ MATERIAL                  → WATCH
  9. OPEN_NEW                                      → ENGAGE / WATCH / AWARE
 10. default                                       → AWARE

Reschedule path
  Reconstruct SchedulerFeatures from AnalysisRun.result_payload["features"]
  Reconstruct Δ_t from frozen score_debug (cognitive_impact + matches)
  Re-run route() with a new RuntimeView
  Do not re-Extract, re-Locate, or re-assess Impact
```

`cognitive_budget_minutes` is a disposition lookup (`DROP=0, AWARE=1, WATCH=2, ENGAGE=15`). It is not computed from `attention_cost`.

---

## 2. Does each real input change disposition?

| Input | Role in `route()` | Can change disposition? |
|---|---|---|
| $\Delta_t$ primary operation / target / change / epi / importance | Direct branch after the three pre-primary gates | Yes |
| `exploration_candidate` / OPEN_NEW on assessment | Fallback when primary is None; OPEN_NEW branch | Yes |
| `is_duplicate` | Gate 1, before $\Delta_t$ | Yes (forces DROP) |
| `threatens_active_work` | Gate 3, before $\Delta_t$; also blocks gate 2 | Yes (forces ENGAGE; can prevent deadline WATCH) |
| `deadline_minutes`, `interruptibility` | Gate 2 | Yes (WATCH vs continue) |
| `marketing_heavy` | Blocks topic→AWARE when $\Delta_t=\varnothing$; OPEN_NEW reason/confidence | Yes only in the $\Delta_t=\varnothing$ AWARE vs DROP choice |
| `high_quality_technical`, `foundational_paper` | $\Delta_t=\varnothing$ → AWARE instead of DROP; ENGAGE reason text | Yes only when $\Delta_t=\varnothing$ |
| `topic_relevance` | $\Delta_t=\varnothing$ AWARE vs DROP (if not marketing) | Yes only when $\Delta_t=\varnothing$ |
| Locate `node_type` / `structural` / `relevance_type` | DECISION ENGAGE; structural ENGAGE; BOTTLENECK urgency | Yes (allocation, not a new $\Delta_t$) |
| `sources_conflict`, `disagreement` | ENGAGE reason; OPEN_NEW ENGAGE vs WATCH | Yes on OPEN_NEW; usually not on targeted ENGAGE once already in that branch |
| `evidence_maturity` | ENGAGE expected_output / watch_after_processing | Rarely disposition; mostly output/watch |
| `attention_cost` / `cognitive_cost` | Unused by `route()` | **No (dead for $A_t$)** |
| `novelty`, `credibility`, `kernel_delta`, `actionability`, `temporal_value` | Unused by `route()` (projection / debug / Live Eval) | **No** |
| `decision_relevance`, `bottleneck_alignment` as scores | Cap for debug; bottleneck score only adds watch triggers | **No for disposition** (type/structural on the match is what matters) |
| `evidence_links_present`, skip flags, source counts | Not read by `route()` | **No** (already baked into epi / conflict) |
| `current_task`, `session_topic`, `available_attention_minutes`, `cognitive_capacity` | Snapshot only | **No** |

---

## 3. Semantic classification

Prefer existing v2.1 entities. No `AttentionContext`, `CognitiveState`, or `UserPreference`.

### A. $\Delta_t$ — cognitive change itself

- operation, target, `target_node_type` (from frozen Locate)
- `change_magnitude`, `epistemic_strength`, `target_importance`
- `exploration_candidate` when it is the OPEN_NEW / new-branch bit of $\Delta_t$

### B. $E_t$ / information-side epistemic properties

- claims / observations / inferences / evidence relations
- `evidence_maturity`, `sources_conflict` / independent source counts
- `marketing_heavy` (source framing)
- `is_duplicate` / secondary reprint (event identity, not Kernel identity)
- processing load of $I_t$ (length, density) — currently misnamed `attention_cost`

### C. $K_t$

- committed target existence and type (via frozen $L_t$, not live Kernel at reschedule)
- target importance (already inside $\Delta_t$ once estimated)
- active Decision / Bottleneck identity (via Locate, not via `decision_relevance` score)

### D. $R_t$

- `deadline_minutes`, `interruptibility`
- should also include `current_task`, `available_attention_minutes`, `cognitive_capacity` — captured but unused

### E. Derived at scheduling time

- disposition-based budget
- urgency (PREEMPT vs PRIORITY vs NORMAL) given $\Delta_t \times R_t$
- watch triggers
- expected_output

### F. Legacy / redundant / unjustified

- `novelty`, `credibility`, `kernel_delta`, `actionability`, `temporal_value` as live policy inputs
- `topic_relevance` / `structural_relevance` / `decision_relevance` / `bottleneck_alignment` as scores that re-state $L_t$
- `threatens_active_work` as a pre-$\Delta_t$ ENGAGE force
- `attention_cost` as currently implemented (heuristic match_score → 8 vs 2, then ignored)
- CASE_K-style raw-text probes inside `_compatibility_features`

---

## 4. Persistence / provenance ownership

| Input | Should freeze where | Production today |
|---|---|---|
| $\Delta_t$ + frozen matches | AnalysisRun (`cognitive_impact` + `score_debug.matches`) | AnalysisRun + copied onto every AttentionPlan `score_debug` |
| $E_t$ process properties used by $\pi$ (duplicate, marketing, maturity, conflict, processing cost) | AnalysisRun-frozen; replayable without live Extract | Mixed: some on `result_payload.features`, some inside impact |
| $L_t$ scores | AnalysisRun debug / Locate provenance | `score_debug.matches` |
| $R_t$ | AttentionPlan `runtime_snapshot` / `runtime_context_id` | Yes for snapshot; only deadline + interruptibility actually consumed |
| Derived allocation | AttentionPlan | Yes (`disposition`, budget, urgency, reason) |

Required boundary:

```text
AnalysisRun  = Cognitive Judgment
               (E_t, L_t, Δ_t, and any E_t-derived process facts π is allowed to see)

AttentionPlan = AnalysisRun × RuntimeContext × AttentionPolicy × SchedulerVersion
```

Reschedule must only change runtime-conditioned allocation. It already avoids re-running Extract/Locate/Impact. It currently **reuses frozen `SchedulerFeatures`**, including `threatens_active_work`, so a later $R_t$ cannot retract a stale PREEMPT.

---

## 5. Is the current formula sufficient?

$$
A_t = \pi(\Delta_t, K_t, R_t)
$$

is the right **cognitive** equation. It is not a complete description of production $\pi$, which also consumes $E_t$-side process facts and, illegally, a hidden cognitive bypass (`threatens_active_work`).

Option A is therefore incomplete as a production contract unless those extra facts are classified as derived quantities of $I_t/E_t/K_t/R_t$ and stripped of cognitive-transition power.

Option B $A_t = \pi(\Delta_t, E_t, K_t, R_t)$ is more honest about “papers still worth AWARE when $\Delta_t=\varnothing$”, but it invites the Scheduler to re-read $E_t$ and re-judge “what changed”. That must be forbidden.

---

## 6. Recommended minimal canonical formula

**Keep Option A as the public equation.** Adopt Option C as the implementation contract:

$$
A_t = \pi(\Delta_t, K_t, R_t;\ p(E_t,K_t))
$$

where $p(E_t,K_t)$ is a **frozen, non-cognitive process bundle** on AnalysisRun, not a new ontology. $\pi$ may use $p$ only to decide whether/when/how much attention to spend. $\pi$ may not invent or revise $\Delta_t$.

$p$ is allowed to contain:

- duplicate / secondary-reprint identity
- processing requirement (cost-to-absorb $I_t$)
- source-framing flags already used to cap epistemic strength (must not be counted twice)
- evidence maturity / conflict **as processing caution**, not as a second transition engine

$p$ is **not** allowed to contain:

- a second estimate of what cognition changed
- Locate scores as a substitute for $\Delta_t$
- `threatens_active_work` as an ENGAGE override when $\Delta_t=\varnothing$

$K_t$ in $\pi$ means frozen committed cognition at AnalysisRun time (target type/importance already inside $\Delta_t$), plus the identity of active work **only as runtime overlap against $R_t$**, not as a hidden CHALLENGE.

---

## 7. Legitimate policy inputs

Given frozen $\Delta_t$:

1. $\Delta_t$ itself (operation, target type, change, epi, importance, OPEN_NEW)
2. $R_t$: deadline, interruptibility, available attention, cognitive capacity, current task
3. Frozen $p$: duplicate identity, processing requirement
4. Frozen evidence caution: maturity / conflict, only to choose WATCH vs ENGAGE **after** $\Delta_t$ is known, or to keep AWARE instead of DROP when $\Delta_t=\varnothing$ **without claiming a cognitive update**

ENGAGE that implies Kernel work requires a legal $\Delta_t \in \{\mathrm{REINFORCE}, \mathrm{CHALLENGE}, \mathrm{OPEN\_NEW}\}$.

---

## 8. Redundant / double-counted inputs

| Input | Already represented by | Keep as live $\pi$ input? |
|---|---|---|
| `epistemic_strength` on $\Delta_t$ and `marketing_heavy` DROP/AWARE gate | marketing already caps epi in Impact | No second DROP rule; framing may only affect $\Delta_t=\varnothing$ AWARE vs DROP |
| `topic_relevance` | $L_t$ scores | Debug / Locate only |
| `structural_relevance` score | match.structural / STRUCTURAL | Use frozen match flag, not the score |
| `decision_relevance` / `bottleneck_alignment` scores | Locate node_type | Debug only |
| `kernel_delta`, `novelty`, `credibility`, `actionability`, `temporal_value` | $\Delta_t$ or unused | Debug / Live Eval only |
| `high_quality_technical` ∧ `foundational_paper` ∧ topic AWARE | overlapping $\Delta_t=\varnothing$ rescue paths | Collapse to one “non-cognitive keep-in-view” rule, if any |
| `attention_cost` vs `_budget(disposition)` | budget is disposition-constant | Cost may scale budget later; it must not pick disposition |

---

## 9. Hidden cognitive bypass

`threatens_active_work` is the only production bypass that can force **ENGAGE / PREEMPT before $\Delta_t$ is read**, including when primary is NONE.

Raw-text probes in `_compatibility_features` (`invalidates novelty`, `overlaps the active submission`, …) plus LLM `threatens_active_work` treat a cognitive claim as an attention interrupt.

That violates: Attention Policy must not re-decide what cognition changed.

`is_duplicate` forcing DROP **before** $\Delta_t$ is a milder bypass: it can hide a real REINFORCE/CHALLENGE from attention. Legitimate only if duplicate means “this $I_t$ is the same event already absorbed”, i.e. process identity, not “Kernel already contains this idea”. The latter belongs in $\Delta_t=\varnothing$.

---

## 10. `threatens_active_work` — final judgment

**Historical bypass, not a legitimate independent cognitive transition, and not a clean $R_t$ signal.**

- It is not genuine $\Delta_t$: a novelty collision with an active paper **is** a CHALLENGE (or at least a targeted effect) on that cognition. If Impact did not emit it, Attention must not invent ENGAGE.
- It is not a derived $E_t \times K_t \times R_t$ scheduling relation today: it is frozen at AnalysisRun time from source text / LLM, then reused on every reschedule even if `current_task` changed.
- It is not a legitimate live urgency bit: $R_t$ never recomputes it.

Recommendation:

- Remove the pre-$\Delta_t$ ENGAGE force.
- If the information really threatens active work, that must appear in $\Delta_t$.
- If $\Delta_t$ is already a material targeted/OPEN_NEW effect **and** $R_t.current\_task$ overlaps that target, $\pi$ may raise urgency to PREEMPT. That is allocation, not a new transition.
- Do not keep the CASE_K string probes as production policy.

---

## 11. `attention_cost` — final judgment

**Not cognitive direction. Currently dead for $A_t$.**

Production sets it from Locate `match_score` (8 vs 2) or LLM “effort to process”, stores it on AnalysisRun / features, then ignores it in `route()`. Budget is a constant of disposition.

Recommended meaning:

- Estimate of processing requirements of $I_t$ (length, technical density, evidence work), derived from $I_t/E_t$.
- Freeze on AnalysisRun as part of $p$.
- At schedule time, $\pi$ may compare frozen cost with $R_t.available\_attention\_minutes$ / `cognitive_capacity` to choose WATCH vs ENGAGE or to size budget.
- It must not create ENGAGE when $\Delta_t=\varnothing$, and must not rewrite $\Delta_t$.

It is not primarily runtime-dependent (the document’s absorb-cost does not change because the user is busy). Runtime only supplies the capacity to pay that cost.

---

## 12. Duplicate / marketing / foundational / relevance — final judgment

### duplicate

If duplicate already implies $\Delta_t=\varnothing$, a second DROP is double-counting. Production does **not** force $\Delta_t=\varnothing$ for duplicates; Impact can still emit REINFORCE while `is_duplicate` DROPs.

Independent Attention value exists only as: “this is a secondary reprint of an already-covered **event**; do not spend attention even if a residual effect was estimated.” That is $p$, frozen on AnalysisRun. It must not be a second cognitive engine.

If the reprint still contains a real CHALLENGE, DROP is the wrong allocation. Duplicate detection should be conservative.

### marketing_heavy

Already acts inside Impact via `MARKETING_EPISTEMIC_CAP`. Using it again to deny AWARE when $\Delta_t=\varnothing$ is a **mild double-count** of source quality: once in $\Delta_t.epi$, once as an Attention veto on topic rescue.

Keep at most one non-cognitive use: when $\Delta_t=\varnothing$, promotional framing is not a reason to AWARE. Do not add a marketing DROP in front of a legal $\Delta_t$.

### foundational_paper / high_quality_technical

These are **source-property shortcuts**, not epistemic priors that survived grounding, and not cognitive-value proxies once $\Delta_t$ exists.

When $\Delta_t=\varnothing$, they currently buy AWARE. That is the only plausible legal use: “no Kernel change, but the object is a paper/survey worth parking in awareness.” It is $p(E_t)$, not $\Delta_t$. It must never ENGAGE, never emit KernelPatch, never fill `update`.

If that AWARE path stays, collapse the two flags and topic_relevance into one frozen “keep-in-view” predicate. Prefer document-type / evidence structure over keyword `foundational`.

When $\Delta_t \neq \varnothing$, they should be debug/reason text only.

### topic / structural relevance scores

Locate is already $L_t$. Scores must not be independent $\pi$ inputs.

- Topic score → debug / Live Eval.
- Structural **match flag** / node_type on the frozen primary target may still modulate expected_output and urgency **after** $\Delta_t$ is chosen. That is reading $L_t$ provenance of the chosen target, not re-scoring relevance.

The $\Delta_t=\varnothing$ `topic_relevance ≥ 0.25` AWARE rule is a leftover “relevant therefore attend” path. It treats Location as Attention. v2.1 forbids treating relevance as cognitive change; it should also stop treating relevance as ENGAGE. AWARE-from-topic is the remaining gray zone — recommend retire unless $p$ has an explicit keep-in-view predicate that is not a Locate score.

---

## 13. AnalysisRun vs AttentionPlan boundary

```text
AnalysisRun-frozen
  E_t, L_t, Δ_t
  p = {duplicate, processing cost, marketing, maturity, conflict, keep-in-view?}
  never current_task / deadline / interruptibility

Runtime / AttentionPlan
  R_t snapshot
  disposition, urgency, budget, expected_output, watch triggers
  scheduler_version, attention_policy_version

Derived at scheduling time
  π(Δ_t, K_t_frozen_in_Δ_t, R_t; p)
```

Changing $R_t$ must not require re-running the Cognitive Engine. Production reschedule already satisfies that mechanically. It fails semantically when frozen `threatens_active_work` still forces ENGAGE independently of the new $R_t$ and independently of $\Delta_t$.

Do not recompute information-side cognition with current runtime. Do not let runtime data enter AnalysisRun identity.

---

## 14. Minimal implementation change plan

Not implemented in this round. Suggested order if later approved:

1. **Kill the pre-$\Delta_t$ threaten ENGAGE.** If overlap with active work matters, encode it as $\Delta_t$ or as PREEMPT urgency **after** a legal $\Delta_t$.
2. **Move duplicate after $\Delta_t$ is known**, or keep it first only as event-identity DROP with an explicit recorded $\Delta_t$ (so DROP + REINFORCE is a visible Attention override, not a silent NONE).
3. **Stop using Locate scores as $\pi$ inputs.** Keep match type/structural of the primary target.
4. **Retire dead features from `route()`** (`novelty`, `kernel_delta`, `actionability`, `temporal_value`, `credibility` as branches). Leave them in `score_debug`.
5. **Define `attention_cost` as frozen processing requirement** and optionally compare it with $R_t$ capacity; do not keep the match_score heuristic as policy.
6. **Collapse $\Delta_t=\varnothing$ AWARE rescues** (foundational / high_quality / topic) into one keep-in-view rule, or delete them and let $\Delta_t=\varnothing$ DROP unless OPEN_NEW/explore.
7. **Use the rest of $R_t$** (`available_attention_minutes`, `cognitive_capacity`, `current_task`) or stop persisting them as if they were causal.
8. **Reschedule contract test:** mutating only RuntimeView changes allocation, never `result_payload.cognitive_impact` / public $\Delta_t$.

No Gold / Pilot-12 / prompt / Impact accuracy work in that plan.

---

## 15. Explicit non-goals

- Do not add AttentionContext, CognitiveState, UserPreference, or other ontology.
- Do not merge Human Feedback with KernelPatch authorization.
- Do not let $\pi$ re-read live Kernel or live $E_t$ to re-estimate $\Delta_t$.
- Do not tune Pilot-12, Impact prompts, or Gold to make threaten/duplicate look better.
- Do not treat WATCH as a cognitive update.
- Do not treat relevance as cognitive change.
- Do not implement this document until review.

---

## Decision

Recommended public equation remains:

$$
A_t = \pi(\Delta_t, K_t, R_t)
$$

with a frozen, non-cognitive process bundle $p(E_t,K_t)$ on AnalysisRun as the only extra input, never as a second transition engine.

`threatens_active_work` is a hidden cognitive bypass and should leave $\pi$.  
`attention_cost` is a processing estimate, AnalysisRun-frozen, currently unused, not a disposition driver.  
Duplicate / marketing / foundational / relevance may affect Attention only as $p$, never by inventing ENGAGE when $\Delta_t=\varnothing$.

**Attention Policy Input Clarification: SPEC RECOMMENDATION**

Do not implement. Wait for review.
