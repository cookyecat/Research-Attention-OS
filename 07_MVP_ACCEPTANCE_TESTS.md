# Research Attention OS — MVP_ACCEPTANCE_TESTS.md

Version: RAOS v1.1

## 1. Test philosophy

These are product acceptance cases, not merely unit tests.

They verify that RAOS behaves like a cognitive operating system rather than:
- a summarizer;
- a bookmark tool;
- a recommendation feed.

LLM wording may vary semantically, but routing and epistemic distinctions must satisfy assertions.

## 2. Shared Kernel fixture

Seed a test user with:

```yaml
Goal G1:
  Build better embodied and multi-agent intelligence systems.

Project P1:
  Motor Intelligence

Bottleneck BT1:
  Lack of latency × energy × task-success evaluation for high-frequency embodied control.

Question Q1:
  Should high-frequency motor control depend on a large unified model?

Belief B1:
  proposition:
    "Large unified models may be unsuitable for the fastest embodied-control loop."
  scope:
    "high-frequency embodied control"
  confidence:
    0.68

Model M1:
  "Embodied intelligence contains partially separable cognitive intelligence and temporal motor intelligence."

Project P2:
  Collective Intelligence

Question Q2:
  "Can shared world models reduce explicit multi-agent communication?"

Belief B2:
  proposition:
    "True swarm-style collective intelligence requires meaningful decentralized local intelligence."
  scope:
    "large-scale multi-agent embodied systems"
  confidence:
    0.65

Decision D1:
  "Evaluate startup equity terms independently from employment obligations."
```

---

# 3. Case A — Galaxy General / WRC robot folding

## Input
Article claims:
- robot uses an agent brain;
- low-level brain produces stable, continuous motion.

Manual user observation:
- demo visibly shows repeated move → pause → move phases.

## Expected extraction

```text
Claim C1:
"The low-level system produces stable, continuous movement."

Observation O1:
"The demo contains repeated movement and pause phases."
```

Forbidden Observation:
```text
"The closed-loop bandwidth is low."
```
unless directly measured. That is an Inference.

## Expected EvidenceLink
```text
O1 WEAKENS C1
```

## Expected Kernel match
- P1
- BT1
- B1
- M1

## Expected scheduler
```text
disposition: ENGAGE
update.operation: REINFORCE | CHALLENGE
```

## Expected Model Delta
Potential distinction between:
- high-level cognitive/task intelligence;
- temporal motor performance.

## Forbidden
- claim fraud;
- infer scripting without evidence;
- silently commit Belief.

---

# 4. Case B — SpaceClaw / WorldDreamer-Orbit

## Input
Article claims:
- shared world model coordinates multiple robotic units;
- one world / one model / many bodies;
- OrbitBench will be released;
- first in-orbit validation is planned.

## Expected
Separate:
- current facts;
- future plans;
- technical claims;
- promotional framing.

## Kernel match
High:
- P2
- Q2
- B2

## Scheduler
```text
ENGAGE
```

## Watch suggestions
- WorldDreamer technical report;
- OrbitBench release;
- in-orbit results;
- independent replication.

## Forbidden
- treat planned OrbitBench as already released;
- treat marketing language as proof.

---

# 5. Case C — End-to-end humanoid startup

## Input
Founder:
> "End-to-end will eventually replace hierarchical architectures."

User:
> "High-frequency embodied control may face latency and energy costs if all signals traverse one large model."

## Expected extraction
Separate:
- Founder Claim;
- User Counter-Belief/provisional hypothesis;
- technical method claims;
- editorial praise.

## Kernel match
High:
- P1
- Q1
- B1

## Scheduler
```text
ENGAGE
```

## Model Delta
Raise a more precise question:
> At which temporal/control layers should end-to-end learning apply?

Do not reduce to binary end-to-end good/bad.

## Watch
If evidence is missing, suggest triggers:
- paper release;
- code release;
- latency results;
- energy results;
- independent replication.

---

# 6. Case D — celebrity investment / startup equity analogy

## Input
Source topic:
- celebrity investment in consumer brand;
- minority equity retained.

User decision:
- minority equity in robotics startup;
- future employment flexibility.

## Expected relevance
```text
Topic Relevance: LOW
Structural Relevance: HIGH
Decision Relevance: HIGH
```

## Kernel match
- D1

## Scheduler
Must not DROP solely because topic is not AI.

Likely:
```text
ENGAGE
```
or AWARE + DECISION_REVIEW depending on depth.

## Expected cognitive structure
```text
Equity Ownership
≠
Corporate Role
≠
Employment Relationship
≠
Contractual Restrictions
```

This case is mandatory to prove structural relevance.

---

# 7. Case E — generic AI news with low Kernel delta

Input:
Major company announces minor model version with no material relation to active projects.

Expected:
```text
AWARE
```
or DROP if trivial.

Must not ENGAGE merely because the company is famous.

---

# 8. Case F — duplicate media coverage

Input:
Five articles report same company announcement with overlapping wording.

Expected:
- preserve five Sources;
- infer one Event when possible;
- identify duplicate/repost relationships;
- do not show five high-priority items;
- do not count five reports as five independent confirmations.

---

# 9. Case G — paper references as Sources

Input:
PDF paper with 20 references.

Expected:
1. Paper becomes Source A.
2. References become ReferenceCandidates.
3. DOI/arXiv exact matches resolve.
4. Unknown references become Source stubs.
5. Create `Source A CITES Source B`.
6. Do not recursively fetch all depth-2 references.
7. Identify references relevant to active Kernel nodes.

---

# 10. Case H — Kernel mutation protection

Input:
ENGAGE item strongly conflicts with B1.

Expected:
```text
KernelPatch(status=PROPOSED)
```

B1 remains unchanged.

Only after explicit user ACCEPT:
- Belief updates;
- version increments;
- history appends.

This must be transactionally enforced.

---

# 11. Case I — disagreement must not be filtered

Input:
High-quality technical source argues opposite of B1.

Expected:
```text
ENGAGE
```

Must not DROP because of preference mismatch.

---

# 12. Case J — RuntimeContext changes route

Same high-value foundational paper.

### Context 1
- no deadline;
- high cognitive capacity.

Expected:
```text
ENGAGE
```

### Context 2
- camera-ready deadline in 2 hours;
- interruptibility LOW.

Expected:
```text
WATCH or BACKGROUND
```

unless paper directly threatens current submission.

---

# 13. Case K — PREEMPT

Input:
New paper highly overlaps user's active submission and may invalidate novelty.

Expected:
```text
disposition: ENGAGE
urgency: PREEMPT
```

Reason explicitly justifies interruption.

---

# 14. Case L — WATCH is not bookmark

Input:
Promising method, insufficient evidence.

Expected:
Create Watch with triggers:
- paper release;
- code release;
- independent replication;
- benchmark update.

UI meaning:
> You do not need to remember to come back.

When trigger fires:
- re-run scheduler;
- allow WATCH → ENGAGE promotion.

---

# 15. Case M — Claim vs Observation vs Inference

Input:
> "The founder says the robot generalizes zero-shot. In the video, it succeeds once. This probably means the system is robust."

Expected:
```text
Claim:
"robot generalizes zero-shot"

Observation:
"video shows one successful run"

Inference:
"system is robust"
```

Forbidden:
- store robustness as Observation;
- treat one success as proof of zero-shot generalization.

---

# 16. Case N — low-value promotional article

Input:
Marketing-heavy article with:
- no primary technical evidence;
- no relevant Kernel match;
- no structural relevance.

Expected:
```text
DROP
```

Source may still persist.

---

# 17. Case O — Kernel admission rule

Input:
> "Company X launches robot Y today."

Expected:
- Source/Event persists.
- No Kernel node auto-created.

Input:
> "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently."

Expected:
- may generate proposed Belief or Model KernelPatch.

---

# 18. API-level acceptance

Minimum capabilities:

```text
POST /sources
GET /sources/{id}

POST /analysis/extract
POST /scheduler/plan

GET /kernel
POST /kernel/patches
POST /kernel/patches/{id}/accept
POST /kernel/patches/{id}/modify
POST /kernel/patches/{id}/reject

POST /watches
GET /watches

GET /sources/{id}/references
```

Exact URL naming may differ if capability is equivalent.

---

# 19. End-to-end happy path

```text
Add Source
  ↓
Extract Claims / Observations
  ↓
Kernel Match
  ↓
AttentionPlan
  ↓
"What could this change?"
  ↓
KernelPatch
  ↓
Accept / Modify / Reject
  ↓
Kernel version update
```

This must work before large-scale ingestion automation.

---

# 20. MVP completion criteria

The MVP is complete when:
- Cases A–O pass at product-behavior level;
- Kernel mutation protection is enforced;
- Source provenance is inspectable;
- WATCH can be created;
- paper references create Source Graph edges;
- at least one real article produces a useful accepted KernelPatch;
- no critical epistemic invariant is violated.

A polished feed does not count as MVP completion.
