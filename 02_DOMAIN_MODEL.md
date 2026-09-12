# Research Attention OS — DOMAIN_MODEL.md

Version: RAOS v1.2

## 1. General conventions

Persistent objects use UUID primary keys. Human-readable display IDs are optional.

Common metadata:
```yaml
id: UUID
created_at: datetime
updated_at: datetime
created_by: USER | SYSTEM | IMPORT
status: string
metadata: object
```

AI may create/propose Source metadata, Event, Claim, Observation candidates, Inference, EvidenceLink candidates, AttentionPlan, Watch, and KernelPatch.

AI may not directly commit Belief, Model, Hypothesis, or Decision.

# 2. Information Plane

## Source

Definition: provenance-bearing external information container.

```yaml
Source:
  id: UUID
  source_type: TEXT | URL | PDF | PAPER | VIDEO | REPO | POST | MANUAL_OBSERVATION
  title: string | null
  canonical_url: string | null
  content_text: string | null
  published_at: datetime | null
  ingested_at: datetime
  author_entities: [string]
  publisher: string | null
  language: string | null
  fingerprint: string
  content_hash: string | null
  ingestion_method: string
```

Optional: DOI, arXiv ID, file path, MIME type, abstract, raw metadata.

Raw source content is immutable after ingestion except parser-versioned reprocessing.

## Event

A real-world occurrence or publication event referenced by one or more Sources.

```yaml
Event:
  id: UUID
  title: string
  event_type: string
  occurred_at: datetime | null
  location: string | null
  summary: string
  confidence: float
  status: CANDIDATE | CONFIRMED | MERGED | ARCHIVED
```

## EventCluster

```yaml
EventCluster:
  id: UUID
  event_id: UUID
  source_ids: [UUID]
  canonical_source_id: UUID | null
  cluster_confidence: float
```

Automatic clustering may be deferred in MVP.

## Claim

An attributed assertion. Claim means "someone asserted X", not "X is true."

```yaml
Claim:
  id: UUID
  source_id: UUID
  event_id: UUID | null
  text: string
  normalized_text: string | null
  claim_type: FACTUAL | TECHNICAL | PREDICTIVE | OPINION | PROMOTIONAL
  attributed_to: string | null
  attribution_type: AUTHOR | FOUNDER | COMPANY | PAPER | RESEARCHER | USER | UNKNOWN
  scope: string | null
  confidence_extraction: float
  credibility_estimate: float | null
  temporal_policy_id: UUID | null
```

## Observation

A directly observed phenomenon or measurement.

```yaml
Observation:
  id: UUID
  source_id: UUID | null
  event_id: UUID | null
  observer_type: USER | PAPER | SYSTEM_EXTRACTED | INDEPENDENT_SOURCE
  text: string
  observation_type: DIRECT_VISUAL | MEASUREMENT | REPORTED_RESULT | USER_FIELD_NOTE | OTHER
  measured_values: object | null
  scope: string | null
  confidence: float
  temporal_policy_id: UUID | null
```

Interpretations such as "closed-loop bandwidth is low" are not Observations unless directly measured.

# 3. Epistemic Plane

## Inference

```yaml
Inference:
  id: UUID
  text: string
  source_object_ids: [UUID]
  author_type: AI | USER
  confidence: float
  scope: string | null
```

Inference always retains traceability.

## EvidenceLink

Evidence is a relation, not a content object.

```yaml
EvidenceLink:
  id: UUID
  source_object_type: CLAIM | OBSERVATION | INFERENCE
  source_object_id: UUID
  target_object_type: CLAIM | BELIEF | HYPOTHESIS | MODEL | QUESTION
  target_object_id: UUID
  stance: SUPPORTS | WEAKENS | REFUTES | NEUTRAL
  strength: WEAK | MODERATE | STRONG
  confidence: float
  scope: string | null
  proposed_by: AI | USER
  accepted_by_user: bool | null
```

## TemporalPolicy

```yaml
TemporalPolicy:
  id: UUID
  freshness_window_seconds: integer | null
  relevance_decay: RAPID | MODERATE | SLOW | PERSISTENT
  validity_review_seconds: integer | null
  review_triggers:
    - NEW_EVIDENCE
    - PROJECT_CHANGE
    - DECISION_CHANGE
    - MANUAL
```

# 4. Cognitive Kernel — Intent State

## Goal

```yaml
Goal:
  id: UUID
  title: string
  description: string
  status: ACTIVE | PAUSED | COMPLETED | ABANDONED
  priority: integer | null
```

## Project

```yaml
Project:
  id: UUID
  title: string
  description: string
  status: ACTIVE | PAUSED | COMPLETED | ABANDONED
  goal_ids: [UUID]
  current_bottleneck_ids: [UUID]
```

## Bottleneck

```yaml
Bottleneck:
  id: UUID
  title: string
  description: string
  project_ids: [UUID]
  status: IDENTIFIED | ACTIVE | RESOLVING | RESOLVED | OBSOLETE
  severity: LOW | MEDIUM | HIGH | CRITICAL
```

# 5. Cognitive Kernel — Epistemic State

## Question

```yaml
Question:
  id: UUID
  text: string
  scope: string | null
  status: OPEN | WATCHING | ACTIVE | ANSWERED | ABANDONED
  project_ids: [UUID]
  related_model_ids: [UUID]
```

## Belief

Canonical form:
`Belief = Proposition + Scope + Confidence`

```yaml
Belief:
  id: UUID
  proposition: string
  scope: string
  confidence: float
  status: TENTATIVE | ACTIVE | CONTESTED | REVISED | DEPRECATED
  supporting_evidence_link_ids: [UUID]
  counter_evidence_link_ids: [UUID]
  last_reviewed_at: datetime | null
```

No AI direct commit.

## Hypothesis

```yaml
Hypothesis:
  id: UUID
  proposition: string
  scope: string
  project_ids: [UUID]
  status: PROPOSED | TESTING | SUPPORTED | REFUTED | INCONCLUSIVE
  experiment_ids: [UUID]
```

## Model

A structured explanatory representation; not equivalent to one Belief.

```yaml
Model:
  id: UUID
  title: string
  description: string
  model_type: CONCEPTUAL | CAUSAL | TAXONOMIC | PROCESS | ARCHITECTURAL | OTHER
  node_data: object
  edge_data: object
  status: PROPOSED | ACTIVE | CONTESTED | REVISED | DEPRECATED
```

# 6. Cognitive Kernel — Execution State

## Decision

```yaml
Decision:
  id: UUID
  title: string
  rationale: string
  project_ids: [UUID]
  status: PENDING | DECIDED | REVISIT_REQUIRED | SUPERSEDED
  decided_at: datetime | null
```

## Experiment

```yaml
Experiment:
  id: UUID
  title: string
  description: string
  project_ids: [UUID]
  hypothesis_ids: [UUID]
  status: PROPOSED | PLANNED | RUNNING | COMPLETED | FAILED | CANCELLED
  result_observation_ids: [UUID]
```

# 7. Scheduler objects

## RuntimeContext

```yaml
RuntimeContext:
  id: UUID
  current_task: string | null
  session_topic: string | null
  available_attention_minutes: integer | null
  interruptibility: LOW | MEDIUM | HIGH
  cognitive_capacity: LOW | NORMAL | HIGH
  deadline_at: datetime | null
  captured_at: datetime
```

## AttentionPlan

```yaml
AttentionPlan:
  id: UUID
  candidate_type: SOURCE | EVENT | CLAIM | OBSERVATION
  candidate_id: UUID
  disposition: DROP | AWARE | WATCH | ENGAGE
  update:
    operation: REINFORCE | CHALLENGE | OPEN_NEW | null
    target_node_id: UUID | snapshot-id | null
  delta_content: string
  urgency: BACKGROUND | NORMAL | PRIORITY | PREEMPT
  cognitive_budget_minutes: integer | null
  kernel_target_ids: [UUID]
  expected_output: NONE | SUMMARY | WATCH | KERNEL_PATCH | DECISION_REVIEW | EXPERIMENT_PROPOSAL
  reason: string
  watch_after_processing: bool
  scheduler_version: string
```

# 8. Watch objects

## Watch

```yaml
Watch:
  id: UUID
  target_type: ENTITY | COMPANY | RESEARCHER | PAPER | METHOD | MODEL | CLAIM | BENCHMARK | QUESTION | TREND
  target_ref: string
  status: ACTIVE | PROMOTED | EXPIRED | CANCELLED
  created_reason: string
  kernel_target_ids: [UUID]
```

## WatchTrigger

```yaml
WatchTrigger:
  id: UUID
  watch_id: UUID
  trigger_type: PAPER_RELEASE | CODE_RELEASE | BENCHMARK_UPDATE | INDEPENDENT_REPLICATION | NEW_EVIDENCE | FUNDING_EVENT | ADOPTION_EVENT | USER_DEFINED
  trigger_config: object
  last_checked_at: datetime | null
```

# 9. KernelPatch

The only AI-originated mechanism that may propose a committed Kernel mutation.

```yaml
KernelPatch:
  id: UUID
  target_object_type: GOAL | PROJECT | BOTTLENECK | QUESTION | BELIEF | HYPOTHESIS | MODEL | DECISION | EXPERIMENT
  target_object_id: UUID | null
  change_type: CREATE | REVISE | DEPRECATE | REOPEN | SUPERSEDE
  current_state: object | null
  proposed_state: object
  evidence_link_ids: [UUID]
  reasoning: string
  suggested_confidence_change: object | null
  status: PROPOSED | ACCEPTED | MODIFIED | REJECTED
  proposed_by: AI | USER
  reviewed_by_user_at: datetime | null
```

Only ACCEPTED or MODIFIED patches may mutate committed Kernel state.

# 10. Kernel admission rule

A candidate Kernel object must satisfy at least one:
1. changes current Researcher State;
2. has sustained relevance to an active Goal, Project, Question, or Decision;
3. affects a future research Decision;
4. represents a stable Belief, Model, Hypothesis, or Bottleneck.

Raw news facts should almost never enter Kernel.

# 11. Allowed relationship vocabulary

Initial set:
```text
SUPPORTS
WEAKENS
REFUTES
RELATES_TO
MOTIVATES
ANSWERS
TESTS
BLOCKS
DEPENDS_ON
SUPERSEDES
DERIVED_FROM
```

Do not expand casually in MVP.

# 12. Versioning

Committed Kernel objects are versioned:
- append immutable snapshot;
- retain prior versions;
- expose diff;
- record causing KernelPatch;
- record user action and timestamp.

Event sourcing is preferred over destructive overwrite.


# 13. Cognitive processing pipeline glossary

The operational cognition path is one mostly top-down pipeline. For reasoning about architecture, group it into four stages rather than treating every box as an independent subsystem:

```text
1. Build the external world: Sensor / Auditor -> Audited Semantic World
2. Relate world to cognition: Locate -> Relation Mapping -> Grounding / Authority
3. Allocate attention: Anchored OPEN_NEW -> Magnitude-Free -> Pareto -> Attention
4. Execute and preserve causality: Decision Cause -> Public Update / KernelPatch / WATCH -> Replay / Cache / Reschedule
```

Design principle: each stage owns one responsibility. Upstream semantic stages must not pre-empt downstream decision policy.

## Relation Mapping

A semantic relation-classification task: connect audited external evidence to relevant Cognitive Kernel nodes. It is deliberately similar to a constrained matching / "connect-the-lines" NLP task.

Input: audited semantic evidence plus Kernel locations / eligible targets.
Output: zero or more semantic relations: `REINFORCE(existing node)`, `CHALLENGE(existing node)`, or `OPEN_NEW`.

A `targeted effect` is simply a Relation Mapping output with an existing Kernel target (`REINFORCE` or `CHALLENGE`). `OPEN_NEW` has no existing target.

The LLM system prompt for this task is called **Relation Mapping Prompt** in architecture documentation and new code (`RELATION_MAPPING_SYSTEM_PROMPT`). Historical `IMPACT_SYSTEM` remains only as a compatibility alias.

Relation Mapping must not choose DROP/AWARE/WATCH/ENGAGE, rank effects into a single winner, or manufacture decision authority from compatibility scores.

## Grounding

Grounding asks whether a proposed semantic relation is actually licensed by the evidence and Kernel state.

Input: a relation, its exact support evidence, target/jurisdiction, and Kernel propositions.
Output: legal/illegal relation plus categorical support/scope assessment.

Grounding owns **relation-support fit**: whether the frozen evidence licenses the proposed operation at the exact target/branch scope. It does not own OPEN_NEW jurisdiction admission. That responsibility belongs to Anchored OPEN_NEW.

A capable evaluator may physically return multiple structured judgments in one model call, or research/high-risk execution may split them across reviewers. The architecture freezes authority ownership and output fields; it does **not** prescribe RPC count. Logical separation is not the same as physical-call separation.

Grounding checks identifier legality, target eligibility, scope alignment, operation direction, and relation-to-support fit. It is the deterministic/semantic firewall between "the LLM proposed a relation" and "the system may reason from that relation."

## Authority

Authority answers which state is allowed to influence downstream decisions. It is separate from Relation Mapping.

Examples: target importance comes from Kernel/user state; epistemic authority comes from evidence provenance/support quality; active-role status comes from Kernel/Locate state. LLM compatibility scores are not authoritative merely because they are numeric.

Authority produces decision-bearing bands/flags consumed by Magnitude-Free policy; it does not itself select the final Attention disposition.

## Anchored OPEN_NEW

`OPEN_NEW` means the evidence opens a useful new cognitive branch but no existing epistemic Kernel node is the correct update target. Such a branch must still belong to a cognitive jurisdiction.

A jurisdiction is a responsibility area in the Kernel, analogous to assigning a new research proposal to an appropriate discipline/division even when it is not an update to an existing project. Current production may use an explicitly labelled Locate-derived approximation; the research contract can carry exact `jurisdiction_anchor_ids` per effect.

Anchored admission answers only whether an `OPEN_NEW` branch has legitimate Kernel jurisdiction. Its semantic jurisdiction check must receive the full anchor meaning (node type/title/proposition or equivalent), not opaque IDs/codes alone. It does not rank the branch or determine Attention.

## Pareto selection

Pareto preserves multiple effects that are incomparable on the discrete decision-bearing dimensions. An effect is removed only when another effect dominates it on all relevant dimensions and is strictly better on at least one.

This prevents a scalar rule such as `change_magnitude * target_importance` from collapsing multiple legitimate cognitive effects into one winner. After the frontier is formed, each frontier effect receives a Magnitude-Free channel plan and article-level Attention is joined from those plans.

## Decision Cause

Decision Cause is the strategy-selected effect that causally explains the article-level Attention decision and authorizes downstream side effects. It is provenance, not a new semantic relation.

Invariant for built-in strategies: `Decision Cause = Public Update Cause = Authorized Side-Effect Cause` unless a versioned compatibility projection explicitly states otherwise.

## Public Update and KernelPatch

Public Update is the user-facing compatibility projection of what the system says changed or matters cognitively. It must project the actual Decision Cause rather than independently selecting another effect.

KernelPatch is an AI-proposed mutation to committed Cognitive Kernel state. It is only a proposal; user acceptance/modification is required before committed Kernel mutation. A patch must be authorized by the same Decision Cause that justified the Attention action.

`WATCH` is future-attention responsibility: preserve a causal target/jurisdiction and define triggers for new evidence rather than mutating cognition immediately.

## Replay / Cache / Reschedule

Replay re-executes a declared stage against frozen inputs for attribution or reproducibility. It must not silently execute a different policy stage or redefine legality.

Cache reuses a completed `AnalysisRun` only when frozen execution identity matches the relevant provider/prompt/strategy contract.

Reschedule keeps frozen cognition but recomputes runtime-dependent attention/artifacts when runtime context changes. Explicit provider and decision strategy must be preserved across reschedule paths.

## Research contract

A research contract is a versioned experimental interface/semantic contract used to test a proposed architecture before production promotion. It is not automatically the production contract. For example, effect-level `support_unit_ids` and `jurisdiction_anchor_ids` are currently validated research-contract fields even when production core still uses a compatibility representation.

## Evaluator-capacity bracketing

Model errors and architecture errors must be separated. During research, evaluate the same frozen task at multiple evaluator strengths when possible:

- weaker model: robustness lower bound / stress test;
- strongest available model or strong-model manual adjudication: capability upper bound / architecture ceiling.

A single weak-model error is not sufficient evidence that the RAOS architecture is wrong. Architecture changes require evidence that the failure persists under a stronger evaluator or follows from a deterministic contract/invariant violation. Conversely, a design that remains reliable under a weak model is especially valuable because it demonstrates architectural robustness rather than merely model capability.
