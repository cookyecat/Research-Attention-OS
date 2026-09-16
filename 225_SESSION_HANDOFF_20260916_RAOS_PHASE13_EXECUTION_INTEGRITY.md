# 225 — Session Hand-off: Phase 10E → Phase 12 Closure → Phase 13 Execution Integrity

Date: **2026-09-16**

## 0. Read this first

This is the shortest recovery point for the next session.

Read in this order:

```text
225_SESSION_HANDOFF_20260916_RAOS_PHASE13_EXECUTION_INTEGRITY.md
11_ROADMAP_AND_PROGRESS.md
RAOS_CANONICAL_ARCHITECTURE.md
224_PHASE13_EXECUTION_INTEGRITY_PREREGISTRATION.md
```

Important: the canonical architecture document has **not yet been updated for the Phase 13 WIP implementation**. Updating it is one of the first closure tasks in the next session.

Repo:

```text
https://github.com/cookyecat/Research-Attention-OS
/Users/liyang/Developer/Research-Attention-OS
branch: main
```

Committed functional HEAD before this hand-off documentation:

```text
88c351657295423edb6949ad35fdd678e8e2b23d
research: preregister phase13 execution integrity
```

Very important:

> **The running Phase 13 implementation is newer than committed HEAD and currently lives in the working tree. Do not hard reset, checkout away, clean, or blanket-stage the repository.**

---

## 1. Current global phase map

```text
Phase 9A   CLOSED — causal alignment supported
Phase 10E  CLOSED FOR FORWARD PROGRESS
Phase 11   CLOSED
Phase 12   CLOSED FOR CURRENT SINGLE-USER DOGFOOD
  12A      CLOSED — feedback attribution firewall
  12B      CLOSED — Theta_u = identity
  12C      DORMANT / CONDITIONALLY DEFERRED
  12D      CLOSED — multi-actor shared responsibility
  12E      CLOSED — ownership boundary frozen, tenantization deferred
Phase 13   ACTIVE — Execution Integrity V1.0 core implementation working
```

Do not resume old Phase 9A. `180_PHASE9A_KERNEL_CAUSAL_ALIGNMENT_RESULT.md` already closed it on 2026-09-13.

Do not reopen the Attention Core merely because one real article was wrong. The 2026-09-16 Google-language incident was first attributed to **runtime execution-identity drift into the legacy compatibility path**, not to a validated failure of the current Pareto Core.

---

## 2. Product doctrine that remains frozen

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.
```

Equivalent desired scaling behavior:

```text
more observed information
→ more automatic machine cognition
→ proportionally less human-visible residue
```

User-space hierarchy:

```text
Inbox      = observed / preserved
Attention  = judged
Today      = deserves consciousness now
```

Permanent authority boundaries:

```text
Acquisition observes; it does not judge.
Reading/opening never triggers cognition by itself.
WATCH transfers future-attention responsibility to RAOS.
Raw popularity is P evidence only; it never directly owns Attention.
Agents may delegate observation/future responsibility; they may not assign Attention.
Kernel mutation remains human-authorized.
```

---

## 3. Phase 10E — why it mattered and final result

Phase 10E was a Core validity gate before personalization.

Main question:

> Is the current post-cognition Attention Core internally coherent and replayable enough that we should move forward rather than keep tuning it?

Historical Oracle-Delta clarification:

- Oracle-Delta predates the pluggable strategy seam.
- its bare `scheduler.route()` call later inherited `one-delta-v1` as compatibility default;
- therefore old Oracle-Delta/Oracle-Awareness policy-isolation measurements are historical with respect to the current strategy;
- this did **not** prove that the real modern production pipeline was secretly using legacy cognition at that time.

Current-strategy deterministic replay gate:

```text
eligible runs                       78
exact disposition                   78 / 78
exact strategy identity             78 / 78
exact Decision Cause                78 / 78
audit errors                         0
```

Three eligible runs contained non-empty effect sets; on those observed states, Pareto and the all-admitted-effects join counterfactual produced zero disposition and Decision-Cause differences.

Assistant-proxy Human-Gold Gate II was frozen with explicit proxy provenance and passed:

```text
10 / 10 exact
```

Final Phase 10E decision:

```text
Core             USE AS-IS
Pareto           KEEP + MEASURE
scheduler tuning DO NOT DO
new Core variable DO NOT ADD without real evidence
```

Key docs:

```text
212_PHASE10E_CURRENT_CORE_ATTENTION_RECONCILIATION_PREREGISTRATION.md
213_PHASE10E_PARETO_ORDER_COHERENCE_REVIEW.md
214_PHASE10E_DETERMINISTIC_INTEGRITY_INTERIM_RESULT.md
215_PHASE10E_PROXY_HUMAN_GOLD_PREREGISTRATION.md
216_PHASE10E_PROXY_GOLD_RESULT_AND_CLOSURE.md
```

---

## 4. Phase 12 — final architecture and status

### 4.1 Phase 12A — feedback attribution firewall

The key problem was to prevent Core/perception/runtime mistakes from being learned as “personal preference.”

Attribution scopes include:

```text
PERCEPTION_ERROR
COGNITION_ERROR
AWARENESS_ERROR
RUNTIME_CAPTURE_ERROR
CORE_POLICY_ERROR
USER_POLICY_RESIDUAL
DELIVERY_PREFERENCE
ACTOR_CONTEXT_ERROR
UNRESOLVED
```

Only:

```text
USER_POLICY_RESIDUAL
+ ATTENTION_POLICY_CORRECTION
+ HUMAN_EXPLICIT
+ disposition-only correction
```

is personalization-eligible.

Everything else fails closed.

Migration:

```text
0012_feedback_attribution
```

### 4.2 Phase 12B — personalization necessity

Measured state:

```text
AttentionFeedback rows              0
personalization-eligible rows       0
Phase-10E proxy Gold mismatch       0
```

Therefore:

```text
Theta_u = identity
```

This means “non-identity personalization is not justified now,” **not** “personalization can never exist.”

### 4.3 Phase 12C — important wording correction

12C should not be described as permanently skipped/deleted.

Correct state:

```text
DORMANT / CONDITIONALLY DEFERRED
```

Activation requires evidence that is all of:

```text
repeated
cross-context stable
causally clean
Core-unexplained
```

and attributed by 12A to explicit-human `USER_POLICY_RESIDUAL`.

If activated, begin with the smallest interpretable residual correction. Do not build a second black-box personal Attention policy by default.

### 4.4 Phase 12D — multi-actor responsibility

Architecture:

```text
Many Agents
→ many WatchDelegations
→ one canonical Watch
→ one canonical RAOS Attention authority
→ one human
```

`declared_actor_id` is caller-declared provenance, not authentication or authority.

Same target + same trigger semantics share one Watch. Same target + conflicting trigger semantics fail closed. Actor count is not importance/urgency.

Migration:

```text
0013_watch_delegations
```

Real two-agent localhost dogfood passed all 11 shared-responsibility checks.

No quota/fairness/priority weights were introduced because no real contention has yet been observed.

### 4.5 Phase 12E — multi-user scale boundary

Current dogfood has no authenticated user/tenant identity.

Frozen ownership split:

```text
potentially shareable External World:
  public Source content
  public Events
  public attention evidence
  transport/cache artifacts when access provenance permits

private Brain / Attention state:
  Kernel
  D profile
  Runtime
  user-conditioned AnalysisRun
  AttentionPlan / Feedback
  WATCH / WatchDelegation
  Delivery
  Kernel authorization

private authenticated-observation authority:
  credentials
  private/following feeds
  private observation scope
```

Current deployment contract:

```text
scope                       SINGLE_USER_DOGFOOD
authenticated_user_identity false
multi_user_isolation        false
state_ownership_boundary    DEFINED_NOT_TENANTIZED
```

Tenantization reopens only when a real second-user/external deployment requirement exists.

Key docs:

```text
210_PHASE12A_PERSONALIZATION_BOUNDARY_FEEDBACK_PREREGISTRATION.md
211_PHASE12_ARCHITECTURE_REVIEW.md
217_PHASE12A_FEEDBACK_ATTRIBUTION_RESULT.md
218_PHASE12B_RESIDUAL_NECESSITY_PREREGISTRATION.md
219_PHASE12B_RESIDUAL_NECESSITY_RESULT.md
220_PHASE12D_MULTI_ACTOR_ATTENTION_ARBITRATION_PREREGISTRATION.md
221_PHASE12D_MULTI_ACTOR_ATTENTION_ARBITRATION_RESULT.md
222_PHASE12E_MULTI_USER_SCALE_BOUNDARY_PREREGISTRATION.md
223_PHASE12E_MULTI_USER_SCALE_BOUNDARY_RESULT.md
```

---

## 5. Real flywheel incident that triggered Phase 13

After Phase 12 closed, runtime audit found that the Mac had rebooted at approximately:

```text
2026-09-16 01:19 local time
```

The Acquisition worker's previous poll was around 01:00. Because it was an ordinary unsupervised process, it did not restart automatically. It was later restarted manually.

This established one operational gap:

```text
theory correct + backend code healthy != continuous flywheel
```

The user then chose the product model:

```text
Normal / Manual installation
  → reboot requires user to start RAOS manually

Service installation
  → OS starts/restarts RAOS automatically
```

**Do not install Service mode automatically. It is an explicit user deployment choice. Current machine is Manual.**

The deeper incident came immediately after restart.

Real Source:

```text
Google: AI for everyone in every language
https://blog.google/innovation-and-ai/technology/ai/ai-for-every-language/
```

User read it and judged that `ENGAGE` was too strong; `AWARE` or `WATCH` felt more appropriate.

Full forensic audit proved the persisted `ENGAGE` came from the legacy runtime path, not the current research-aligned Pareto Core.

Frozen incident fixture:

```text
eval/incidents/20260916_google_language_false_engage/fixture.json
```

Key IDs:

```text
Source        b68c8180-de38-4749-842e-68851465fab3
AnalysisRun   ef5a1737-5055-4e16-ae22-c2871d126d0c
AttentionPlan ad5d6bdc-1ad1-40df-b463-8f4187582860
KernelPatch   94a1da92-4b41-4979-adab-e663c58ff492
Watch         57341b06-8e03-4e56-b992-5aad3be8b642
```

False primary target:

```text
BELIEF 4028fb49-da23-4a92-a26f-dcefb20dd95e
True swarm-style collective intelligence requires meaningful decentralized local intelligence.
```

Secondary false match:

```text
QUESTION f8ac3025-199f-4b67-bd1e-a46327c5bd70
Can shared world models reduce explicit multi-agent communication?
```

Persisted execution identity:

```text
provider_type     rule
decision_strategy one-delta-v1
stage providers   rule
```

---

## 6. Exact false-ENGAGE mechanism

The legacy path did approximately this:

```text
long Google language article
→ broad lexical matcher sees generic overlap:
   intelligence / large-scale / local / meaningful / requires / systems / true
→ matches swarm-intelligence BELIEF at 0.5833
→ article contains unrelated phrase "region-anchored rather than language-anchored"
→ legacy contrastive heuristic treats "rather than" as target-specific challenge evidence
→ false CHALLENGE
→ change_magnitude forced to 0.7
→ BELIEF importance 0.75
→ one-delta chooses false CHALLENGE
→ targeted + meaningful + important
→ ENGAGE
```

A second heuristic error also occurred:

```text
article contains phrase "Rigorous foundational research"
→ legacy feature sees word "foundational"
→ foundational_paper = true
```

So the explanation text incorrectly claimed foundational/high-quality technical treatment.

The run itself already contained warning signs:

```text
topic_relevance       0.22
decision_relevance    0
bottleneck_alignment  0
credibility           0.35
epistemic_strength    0.25
evidence_maturity     0.10
marketing_heavy       true
independent_sources   1
```

but legacy one-delta still allowed the false targeted CHALLENGE to dominate.

It also created:

```text
PROPOSED KernelPatch → mark the swarm BELIEF CONTESTED
ACTIVE Watch          → PAPER_RELEASE / CODE_RELEASE / INDEPENDENT_REPLICATION
```

The Kernel itself was not changed because the human authorization boundary held.

---

## 7. Why the live worker became legacy

The earlier canonical Mac dogfood configuration had explicitly used:

```text
RAOS_COGNITIVE_PROVIDER=model
RAOS_COGNITIVE_CONTRACT=research-aligned-v1
RAOS_DECISION_STRATEGY_ID=pareto-multidelta-cardinal-free-effect-anchored-open-new
```

At incident time, the local `.env` contained only Delivery/SMTP-style configuration keys; the cognition identity keys were absent.

Therefore after process restart the repository compatibility defaults materialized:

```text
cognitive_provider = rule
cognitive_contract = legacy
decision_strategy  = one-delta
```

Important precision:

> **The Mac reboot did not itself delete `.env` entries. It exposed an already-existing configuration drift because the old in-memory process died and the new process reconstructed settings from disk.**

This incident establishes:

```text
Alive but semantically wrong > ordinary crash risk
```

and the new engineering principle:

```text
Observability is part of correctness.
```

---

## 8. Phase 13 — frozen top-level design

Preregistration:

```text
224_PHASE13_EXECUTION_INTEGRITY_PREREGISTRATION.md
```

Prereg commit:

```text
88c3516 research: preregister phase13 execution integrity
```

Phase 13 is deliberately not a new AI Auditor framework. It is deterministic **Execution Integrity**.

Core questions:

```text
Who should I be?
Who am I actually?
What am I currently authorized to do?
```

Execution context conceptually includes:

```text
Purpose
DesiredIdentity
ResolvedIdentity
BuildIdentity
CapabilityState
Attestation
```

Frozen invariants:

### I1 — Explicit execution identity

Every authoritative cognitive decision carries explicit desired and resolved execution identity.

### I2 — Authority by attestation

Authority is derived from:

```text
execution purpose
+ deterministic attestation
+ required capability readiness
```

It is not an arbitrary writable truth flag.

### I3 — Graceful degradation

Failure removes only the invalidated capability. It never silently selects a different semantic contract.

### I4 — Recoverability

Temporary loss of cognition authority must not become permanent information loss. Observation time remains the original observation time even if cognition happens later.

---

## 9. Important Phase 13 architecture refinements

### 9.1 Identity integrity != dependency availability

Examples:

```text
profile says research-aligned, strategy correct
but DeepSeek temporarily unavailable
→ identity still valid
→ cognition capability unavailable

profile says research-aligned
but actual loaded strategy = one-delta
→ identity attestation failure
```

Do not conflate these.

### 9.2 Authority is a graph, not one global READY bit

Conceptually:

```text
Observation
    ↓
Cognition
    ↓
Attention
  ┌─┼────────────┐
  ↓ ↓            ↓
WATCH Patch    Delivery
                ├ In-app
                ├ Email
                └ Push
```

A missing SMTP server should not revoke Observation/Cognition. A missing LLM credential may leave Observation READY while Cognition/Attention are BLOCKED.

### 9.3 Gate location

The important gate is before canonical `AttentionPlan` persistence:

```text
cognition result / candidate draft
→ Execution Authority Gate
    ├─ NO  → preserve AnalysisRun forensic result only
    └─ YES → persist AttentionPlan → WATCH / Patch / Delivery
```

Do not write invalid canonical AttentionPlan rows and then merely tag them false if avoidable.

### 9.4 Manual / Service is orthogonal to semantic identity

```text
InstallMode  answers: who starts RAOS?
RuntimeProfile answers: which RAOS is being started?
```

Service installer must not invent semantic configuration.

---

## 10. Phase 13 implementation currently in the working tree

These files are part of the active WIP and must be reviewed before any cleanup:

```text
M  .gitignore
M  backend/app/acquisition_worker.py
M  backend/app/api/agent.py
M  backend/app/api/kernel.py
M  backend/app/config.py
M  backend/app/delivery_worker.py
M  backend/app/main.py
M  backend/app/services/acquisition.py
M  backend/app/services/analysis_runs.py
M  backend/app/services/pipeline.py
M  backend/tests/test_acquisition_plane.py
?? backend/app/cognition_reconciler.py
?? backend/app/execution_integrity.py
?? backend/tests/test_phase13_execution_integrity.py
?? config/runtime/research-dogfood-v1.yaml
?? scripts/install-raos.sh
?? scripts/raos-service-macos.sh
?? scripts/raosctl
```

### 10.1 Versioned canonical runtime profile

File:

```text
config/runtime/research-dogfood-v1.yaml
```

It freezes authority-bearing identity outside `.env`, including current research-aligned cognition and the current Pareto strategy.

Authority-bearing configuration is version-controlled; secrets remain local.

### 10.2 Deterministic execution integrity

File:

```text
backend/app/execution_integrity.py
```

Implemented concepts include:

```text
desired identity
resolved identity
build identity
semantic profile hash
attestation
capability readiness
derived Attention/side-effect authority
health contract
```

### 10.3 Pre-Attention authority gate

`backend/app/services/pipeline.py` now constructs the candidate cognitive result before `AttentionPlan` persistence and checks execution authority.

Tested behavior for intentional mismatch:

```text
expected = research-aligned + current Pareto
actual   = rule + one-delta

forensic cognition allowed
AttentionPlan created  0
WATCH created          0
KernelPatch created    0
Delivery created       0
```

### 10.4 Graceful Acquisition degradation

Acquisition now preserves Snapshot first. If cognition cannot run authoritatively, the observation survives and may be marked reconciliation-eligible.

Desired behavior:

```text
new genuine arrival
→ persist Snapshot
→ attempt canonical cognition
→ technical failure
→ keep Snapshot
→ cognition_deferred = true
→ cognition_reconcile_eligible = true
```

Baseline history and explicit metadata-only deferrals remain non-reconciliation work.

### 10.5 Cognition Reconciler

File:

```text
backend/app/cognition_reconciler.py
```

It is intended to find genuine post-baseline deferred arrivals that still lack a successful authoritative canonical AnalysisRun and process them once canonical cognition becomes READY.

It must preserve original observation/capture time; late cognition is not a new world event.

### 10.6 Runtime operations

Files:

```text
scripts/install-raos.sh
scripts/raosctl
scripts/raos-service-macos.sh
```

Current product semantics:

```text
manual  → user starts RAOS after reboot
service → launchd starts/restarts RAOS automatically
```

Both paths select the same canonical profile.

`raosctl doctor` currently reports process status plus execution-integrity health.

### 10.7 Delivery worker environment consistency

`delivery_worker.py` was changed so `--env-file` is loaded before runtime configuration imports, matching Acquisition's startup discipline.

Do not expose `.env` content in chat or docs; it may contain private SMTP credentials.

---

## 11. Current test evidence for the WIP

Focused Phase 13 tests:

```text
4 passed
```

Phase 13 + Acquisition/degraded operation set:

```text
15 passed
```

Broader related regression covering Phase 13, Acquisition, Analysis provenance, production extraction bridge, Delivery, Agent Interface, and multi-actor behavior:

```text
61 passed
1 existing Starlette/httpx warning
0 new failures
```

**Full backend regression has NOT yet been run for this Phase 13 WIP.**

Do not call Phase 13 closed before that.

---

## 12. Current real runtime at hand-off

Measured near hand-off time with:

```text
scripts/raosctl doctor
```

Current install mode:

```text
manual
```

Current process observations:

```text
backend      PID 16580   port 8000
acquisition  PID 16602
delivery     PID 16614
frontend     PID 16626   port 3000
```

PIDs are transient observations only.

Current Execution Integrity state:

```text
profile       research-dogfood-v1
purpose       CANONICAL
attestation   ATTESTED
mismatches    []
Observation   READY
Cognition     BLOCKED
Attention     BLOCKED
Delivery      READY
overall        DEGRADED
missing        llm_api_key
```

This state is intentional and safer than legacy fallback.

Current Acquisition behavior should therefore be:

```text
continue observing/persisting
do not create canonical cognition/Attention while model capability is unavailable
mark genuine deferred arrivals for later reconciliation
```

Do not fabricate or guess the missing model credential. Do not commit secrets.

One stale unmanaged process object is still visible:

```text
PID 64640
old uvicorn command
```

It is **not listening on port 8000**; current listener is PID 16580. Clean this stale process/session residue early next session, but do not kill the current managed Manual runtime by mistake.

---

## 13. Database state / important persistence facts

Active dogfood DB remains:

```text
backend/raos.db
```

Do not accidentally use a repository-root `raos.db` because the relative SQLite URL depends on working directory.

Current applied migration baseline includes:

```text
0012_feedback_attribution
0013_watch_delegations
```

The Google false-engage historical AnalysisRun/AttentionPlan/Patch/Watch must be preserved for forensic history.

Desired future remediation is append-only invalidation/finding semantics, not history deletion or pretending the event never happened.

Proposed concept from design review:

```text
ExecutionIntegrityFinding
```

with something like:

```text
finding_type = ACCIDENTAL_NONCANONICAL_EXECUTION
analysis_run_id = ...
affected artifacts = ...
reason = desired research-aligned / resolved legacy one-delta
```

This is not implemented yet.

---

## 14. Google incident acceptance target

When the correct model credential is restored, rerun the frozen Google Source through the canonical current Core.

Do **not** preregister an arbitrary exact final label such as “must be AWARE.” The user said AWARE or WATCH both feel plausible.

The regression target is mechanism-level:

```text
broad lexical overlap alone
  must not create target update authority

unrelated "rather than"
  must not become target-specific CHALLENGE

phrase "foundational research"
  must not mean foundational_paper

these artifacts alone
  must not produce ENGAGE
```

Test the failure mechanism, not one arbitrary final disposition.

---

## 15. Roadmap status after this hand-off

`11_ROADMAP_AND_PROGRESS.md` was updated in this session to fix stale living-state summaries:

```text
Phase 9A CLOSED
Phase 10E CLOSED FOR FORWARD PROGRESS
Phase 11 CLOSED
Phase 12 CLOSED for current single-user dogfood
Phase 12C DORMANT / CONDITIONALLY DEFERRED
Phase 13 ACTIVE
```

It also updates:

- P from “estimator modeling active” to the Phase-11C operational baseline;
- Immediate Next Steps to Phase 13;
- the old Phase-IV/Phase-V planning text so it does not contradict Phase 9A / Phase 12;
- Phase 13 incident, current WIP, runtime state, and closure checklist.

---

## 16. Working-tree safety — critical

The repository still contains a large amount of pre-existing unrelated noise that must not be accidentally staged, reverted, or deleted.

Examples:

```text
many tracked deletions under eval/live/results/...
untracked old Phase9A v0.1 files
backend/uv.lock
untracked docs/
old exploratory eval/live/results/20260915T082849Z/
many untracked Phase10 result directories
```

Known old Phase9A WIP examples that are unrelated to Phase 13:

```text
backend/tests/eval/test_phase9a_kernel_causal_alignment_v0_1.py
eval/live/phase9a_kernel_causal_alignment_v0_1.py
eval/live/run_phase9a_kernel_causal_alignment_v0_1.py
```

Use exact-stage discipline only:

```text
git status --short
git add -- <exact files>
git diff --cached --name-status
git diff --cached --check
git fetch origin main
compare local / remote
commit
push
```

Never stage `.env`.
Never `git add -A` in this repository state.
Never `git reset --hard` or `git clean` around the current WIP.

---

## 17. Next-session first actions — recommended exact order

1. Read this hand-off, `11_ROADMAP_AND_PROGRESS.md`, `RAOS_CANONICAL_ARCHITECTURE.md`, and `224`.
2. Run `git status --short`; confirm Phase 13 WIP files are still present.
3. Run `scripts/raosctl doctor` and verify the expected current degraded state.
4. Clean only the stale old unmanaged PID/session residue; do not disturb current Manual runtime.
5. Review the Phase 13 WIP diff before editing further.
6. Run the **full backend regression**; attribute any failures before changing the design.
7. Update `RAOS_CANONICAL_ARCHITECTURE.md` to include Execution Context / Attestation / Authority Gate / degraded reconciliation / Manual-Service separation.
8. Commit and push the Phase 13 core implementation checkpoint with exact-stage hygiene.
9. Implement append-only execution-integrity finding/remediation semantics for the historical Google artifacts.
10. Restore the canonical model credential securely if/when available; never guess it and never print secrets.
11. Re-run the frozen Google incident under the canonical Core and verify the forbidden causal mechanism is absent.
12. Run Cognition Reconciliation over genuine deferred arrivals.
13. Re-check Delivery and Today/Attention after reconciliation.
14. Only then decide whether Phase 13 meets closure gates.
15. Resume normal real dogfood; let the next actual residual choose the next work.

Do not invent Phase 14 yet.

---

## 18. User decisions / preferences relevant to continuation

The user explicitly prefers:

```text
real dogfood over speculative architecture expansion
causal attribution before tuning
preregistration before measurement claims
exact provenance
minimal correction / Occam
no overfitting rare corner cases
no fake success
```

For Human Gold, the user authorized assistant first-pass proxy labels when needed, but provenance must remain explicit (`assistant_proxy_for_user`) and proxy Gold must never be represented as direct human labeling or used alone to authorize personalized learning/Core redesign.

For deployment, the user explicitly chose a two-mode product:

```text
Normal install  → manual start after reboot
Service install → automatic start after reboot
```

The system must let the user choose. Do not silently install the launchd Service path.

---

## 19. Core theoretical/engineering memory

Keep these principles visible:

```text
Theory defines invariant.
Engineering estimates enough state to preserve invariant.
Flywheel reveals where approximation fails.
```

```text
Approximate state estimation is allowed;
semantic shortcutting is not.
```

```text
Observed problem → solve.
Imagined scale problem → wait for flywheel evidence.
```

New Phase 13 memory:

```text
process alive != semantically authoritative RAOS
```

```text
Failure should remove only the authority it invalidates.
```

```text
Stopped/degraded is safer than silently becoming another cognition system.
```

```text
RAOS must know not only what it knows,
but under which valid execution identity it knows it.
```

---

## 20. Final hand-off state

The session should be understood as ending at this point:

```text
Phase 10E validated and closed
Phase 12 closed with identity personalization default and conditional 12C
real Google false-ENGAGE incident forensically attributed
Phase 13 Execution Integrity preregistered and incident frozen
Phase 13 core implementation working in local WIP
canonical Manual runtime running in safe DEGRADED state
Observation continues
Cognition / Attention authority blocked because model credential is unavailable
full regression + architecture doc + implementation commit + incident remediation remain next
```

The next session should continue **Phase 13**, not reopen already-closed theory and not erase the forensic evidence that motivated the phase.
