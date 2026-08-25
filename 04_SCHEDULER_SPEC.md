# Research Attention OS — SCHEDULER_SPEC.md

Version: RAOS v1.1

## 1. Core contract

The scheduler is not an importance scorer.

```text
Scheduler(
    Candidate,
    KernelSnapshot,
    RuntimeContext,
    AttentionPolicy
) -> AttentionPlan
```

## 2. Candidate

May be Source, Event, Claim, or Observation.

```yaml
candidate:
  id:
  type:
  title_or_text:
  source_ids:
  extracted_claims:
  observations:
  freshness:
  credibility:
  novelty:
```

## 3. KernelSnapshot

Provide only active/relevant state:

```yaml
kernel_snapshot:
  active_goals:
  active_projects:
  active_bottlenecks:
  active_questions:
  active_beliefs:
  active_hypotheses:
  active_models:
  pending_decisions:
  active_experiments:
```

Use retrieval to build this snapshot; do not inject the whole lifetime Kernel.

## 4. RuntimeContext

```yaml
runtime_context:
  current_task:
  session_topic:
  available_attention_minutes:
  interruptibility:
  cognitive_capacity:
  deadline_at:
```

## 5. AttentionPolicy

MVP configuration:

```yaml
attention_policy:
  active_project_recall_bias: high
  general_news_precision_bias: high
  exploration_ratio: 0.15
  max_engage_items_per_day: 7
  preempt_threshold: high
```

## 6. Output: AttentionPlan

```yaml
AttentionPlan:
  attention_state: DROP | AWARE | WATCH | ENGAGE

  processing_modes:
    - SCAN
    - LEARN
    - VERIFY
    - DEEP_DIVE
    - SYNTHESIZE

  urgency: BACKGROUND | NORMAL | PRIORITY | PREEMPT

  cognitive_budget_minutes:

  kernel_targets:
    - kernel_node_id

  expected_output:
    NONE
    SUMMARY
    WATCH
    KERNEL_PATCH
    DECISION_REVIEW
    EXPERIMENT_PROPOSAL

  watch_after_processing: true | false

  reason: string
```

## 7. Attention states

### DROP
No human attention now. Typical reasons:
- duplicate;
- weak source;
- low relevance;
- expired low-value news;
- already incorporated.

Human attention cost = 0.

### AWARE
User only needs to know it happened.

Typical budget: 10–30 seconds.

Do not automatically create a KernelPatch.

### WATCH
Potential future value, insufficient current value/evidence.

Semantic:
> future attention responsibility is transferred to the system.

WATCH requires at least one promotion trigger.

### ENGAGE
Worth real human cognitive effort now.

Must include at least one processing mode.

## 8. Processing modes

### SCAN
Quick orientation.

### LEARN
Understand a concept, mechanism, architecture, or method.

### VERIFY
Test whether a strong Claim is actually supported.

Favor VERIFY when:
- marketing confidence is high;
- user disagreement is high;
- evidence maturity is low;
- attribution is unclear.

### DEEP_DIVE
Inspect paper details, code, appendix, benchmark, implementation.

### SYNTHESIZE
Compare with current Beliefs, Models, Questions, and prior evidence.

## 9. Urgency

```text
BACKGROUND
NORMAL
PRIORITY
PREEMPT
```

PREEMPT is rare and means worth interrupting current work.

Typical cases:
- competitor publishes nearly identical active work;
- new evidence invalidates a core assumption;
- a time-sensitive decision is materially affected.

Popularity alone never justifies PREEMPT.

## 10. Core features

Scheduler may estimate:

```text
R   Topic Relevance
SR  Structural Relevance
DR  Decision Relevance
N   Novelty
C   Credibility
KΔ  Potential Kernel Delta
B   Bottleneck Alignment
D   Disagreement
A   Actionability
T   Temporal Value
Cost Cognitive Cost
```

Do not collapse these into one authoritative weighted score.

## 11. Rule-based routing first

Reference rules:

```text
IF duplicate OR clearly redundant
  → DROP

IF low credibility AND low Kernel relevance
  → DROP

IF relevant but no likely Kernel delta
  → AWARE

IF strategic potential high AND evidence insufficient
  → WATCH

IF directly resolves active Bottleneck
  → ENGAGE

IF high relevance AND high disagreement with active Belief
  → ENGAGE + VERIFY

IF high relevance AND introduces a new mechanism
  → ENGAGE + LEARN

IF sources materially conflict
  → ENGAGE + VERIFY + SYNTHESIZE

IF active Decision may change
  → ENGAGE + SYNTHESIZE

IF active Decision may change AND time-sensitive
  → PRIORITY or PREEMPT
```

## 12. Error-cost policy

### Active Project / Bottleneck
Bias toward recall.

### General industry news
Bias toward precision.

The cost of missing a direct competitor paper may be much larger than showing one extra generic news item.

## 13. Disagreement handling

High relevance + conflict with active Belief should normally raise Verification Value.

The scheduler explanation should say this explicitly.

## 14. Structural relevance

Cross-domain analogical structure is first-class.

Example:
- source topic: celebrity consumer-brand investment;
- user problem: robotics-startup minority equity;
- shared structure: equity ownership vs employment obligations.

Possible output:
```text
Topic relevance: low
Structural relevance: high
Decision relevance: high
```

## 15. Runtime-aware routing

Same item can route differently under different RuntimeContext.

Important foundational paper + deadline in 2 hours:
- WATCH/BACKGROUND.

Nearly identical competitor work + deadline in 2 hours:
- PREEMPT + ENGAGE + VERIFY.

Importance != urgency.

## 16. Cognitive-budget suggestions

Reference budgets:

```text
AWARE: 0.25–0.5 min
SCAN: 1–3 min
LEARN: 5–20 min
VERIFY: 5–30 min
DEEP_DIVE: 20–120+ min
SYNTHESIZE: 10–30 min
```

## 17. Exploration

Default exploration ratio: 10–20%.

Candidates:
```text
low Kernel similarity
+ high novelty
+ high credibility
+ high potential impact
```

Exploration is not random noise.

## 18. Explanation requirements

Every non-DROP plan should explain:
1. why it matters;
2. which Kernel nodes it matches;
3. why the route was selected;
4. evidence maturity;
5. expected cognitive output.

## 19. LLM behavior

Prompt must enforce:
- popularity is not importance;
- disagreement is not disinterest;
- claims are not observations;
- missing evidence must not be invented;
- no direct Belief commit;
- prefer WATCH for promising but immature information;
- use RuntimeContext;
- consider structural relevance.

## 20. Deterministic validation

Application code validates:
- enums;
- budget >= 0;
- ENGAGE has a mode;
- WATCH has a trigger proposal;
- PREEMPT has explicit justification;
- Kernel targets exist.

Never persist raw unvalidated LLM JSON.

## 21. Scheduler versioning

Persist a version such as:
```text
raos-scheduler-0.1.0
```

Every AttentionPlan stores its scheduler version.

## 22. Feedback hooks

Collect:
- user override;
- opened/not opened;
- engaged time;
- KernelPatch generated;
- Patch accepted;
- Decision affected;
- Experiment affected.

Do this before attempting learned Personal Attention Policy.

## 23. Implementation phases

Phase A: rules + one strong LLM call.
Phase B: separate extraction and scheduling.
Phase C: feedback-calibrated heuristics.
Phase D: learned personal policy.

Do not jump directly to Phase D.
