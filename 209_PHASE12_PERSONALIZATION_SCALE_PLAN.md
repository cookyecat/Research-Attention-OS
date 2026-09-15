# Phase 12 — Personalized Attention Control & Multi-Actor Calibration

Status: **REDESIGNED / 12A ACTIVE**
Date: 2026-09-15
Depends on: Phase 11 External Attention Infrastructure CLOSED.

> Phase 12 is not “learn what the user likes.” It asks how one canonical RAOS can preserve universal cognition/attention semantics while calibrating the cost of human attention for a particular person across changing runtime and agent-mediated contexts.

## 1. Why the old plan is insufficient

The original personalization proposal predates several now-canonical RAOS boundaries: mature D/S/P semantics, WATCH as delegated future-attention responsibility, event-level P evidence, Delivery Plane, and Agent Interface.

Therefore the old 30-case questionnaire is retained as historical exploratory evidence, not treated as current calibration Gold.

A modern personalization layer must not collapse distinct concepts back into a generic preference model.

```text
D                = standing attention jurisdiction
K_t              = current cognitive state
Runtime          = temporary task/capacity/interruption state
WATCH            = delegated future-attention responsibility
Delivery         = execution of an existing Attention decision
Agent Context    = invocation/delegation context, not Attention authority
Personalization  = calibration of human attention economics within these boundaries
```
## 2. Frozen personalization boundary

Phase 12 may calibrate **user-specific attention policy parameters and explicit standing user state**. It may not redefine universal semantic variables or create a second cognition path.

```math
A_t = \Pi(\Delta_t, D_t, S_t, P_t, R_t; \Theta_u)
```

where `Θ_u` is a calibrated user attention-economics profile and `R_t` is transient runtime state.

The following are explicitly **not** free personalization knobs:

- the meaning of `REINFORCE / CHALLENGE / OPEN_NEW / NONE`;
- the semantics of D, S, or P;
- the no-Delta gate `AWARE iff S AND (D OR P)`;
- Decision Cause / Kernel authorization rules;
- raw popularity → Attention shortcuts;
- Agent-created importance scores.

`UserCalibration != UniversalTheoryChange` remains a hard invariant.

## 3. Personal state taxonomy

Phase 12 separates durable and transient user-specific state instead of learning one opaque preference vector.

```text
Standing Jurisdiction   J_u / D-profile     what worlds RAOS should keep on the radar
Cognitive State         K_t                 what the user currently believes/models/questions
Attention Economics     Θ_u                 when human attention is worth spending now/later
Runtime State           R_t                 deadline, capacity, interruptibility, active-work overlap
Delivery Preferences    Λ_u                 channels, quiet hours, device preferences
Actor Context           C_a                 which Agent/task delegated the request
```
## 4. Phase decomposition

```text
12A  Personalization Boundary & Feedback Semantics
12B  Fresh Attention Calibration v2
12C  Real-Trajectory Residual Learning
12D  Multi-Actor / Agent Delegation
12E  Multi-user & Product Scale
```

### 12A — Personalization Boundary & Feedback Semantics
Freeze what may be personalized, define explicit feedback semantics, and prevent clicks/opens/dismissals from being misread as clean preference labels. Establish the data contract before learning anything.

### 12B — Fresh Attention Calibration v2
Create new controlled Human Gold against the current architecture. Cases must separately control cognitive branch, no-Delta D/S/P branch, WATCH/future-option value, runtime capacity, active-work overlap, and interruption cost. Do not reuse the old 30-case set as confirmatory Gold.

### 12C — Real-Trajectory Residual Learning
Use dogfood outcomes to refine `Θ_u`, but prefer explicit correction and outcome evidence over passive click inference. Learn residual calibration, not the entire policy from scratch.

### 12D — Multi-Actor / Agent Delegation
Study Human + Claude/Codex/Cursor/other agents sharing one RAOS. Agents may contribute task context, delegation provenance, and observation intent; they may not own independent Attention authority. Test cross-agent contention for one human attention budget.

### 12E — Multi-user & Product Scale
Evaluate whether the shared policy family generalizes across users, what must remain user-local, database/materialization needs, privacy boundaries, delivery preferences, and scalable calibration/update mechanisms.
## 5. Feedback semantics

Passive product behavior is not automatically Human Gold.

```text
Open / click        != ENGAGE label
No open             != DROP label
Dismiss             != low value
Acknowledge         != correct decision
Long dwell          != importance
Agent request       != human urgency
```

Preferred calibration evidence, strongest first:

1. explicit disposition correction (`should have been AWARE/WATCH/ENGAGE/DROP`);
2. explicit timing/runtime correction (`right item, wrong time`);
3. explicit WATCH outcome judgment (`good delegation`, `missed trigger`, `unnecessary watch`);
4. explicit delivery correction (`should/should not have interrupted`);
5. task outcome evidence when causally attributable;
6. passive behavior only as weak, confounded evidence.

Phase 12 should introduce a provenance-preserving feedback object rather than silently converting UI events into training labels.

## 6. Historical 30-case questionnaire

The 2026-09-05 30-case elicitation remains useful for hypothesis discovery. It already suggested future-option value, generative potential, runtime suppression, and active-work overlap.

However it predates the mature D/S/P and Phase 11 architecture. Its `Δ=NONE` cases lack the now-required D/S/P awareness evidence, and several runtime concepts were only prose. It is therefore **development evidence, not Phase 12 confirmatory Gold**.

The 2026-09-15 Oracle-Δ run is recorded as an exploratory instrument sanity check only. No production policy change may be justified from that run alone.
## 7. Research questions

- **RQ12.1:** Which user-specific variables improve Attention allocation without contaminating universal cognition/D/S/P semantics?
- **RQ12.2:** Can a small fresh calibration set locate a user inside a shared attention-policy family?
- **RQ12.3:** Can explicit real-world residuals improve calibration without overfitting noisy UI behavior?
- **RQ12.4:** Can multiple Agents delegate work through one RAOS while competing safely for one human attention budget?
- **RQ12.5:** What parts of personalization are globally shared, user-local, task-local, or device/delivery-local?

## 8. Success criterion

Phase 12 succeeds only if personalization reduces **policy error and unnecessary human interruption** while preserving canonical semantic authority.

A lower click rate or higher engagement rate is not, by itself, success.

The north-star remains:

```text
more observed information
→ more automatic machine cognition
→ fewer unnecessary human interruptions
→ low critical-miss rate
```

## 9. Immediate next step

Phase 12A freezes the personalization/feedback contract before any new model fitting. Only after 12A closes should fresh Human Gold v2 be collected under the current architecture.
