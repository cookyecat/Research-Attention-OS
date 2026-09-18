# RAOS Productization V1.0 — Private Paid Beta Target

**Status:** TARGET FROZEN / PRODUCTIZATION TRACK ACTIVE  
**Date:** 2026-09-17  
**Target:** Private Paid Beta, 50–200 users

## 1. Productization North Star

RAOS has crossed the boundary from a research prototype into a research-grade cognitive product kernel. The next primary objective is not to keep making the cognition stack more elaborate. It is to turn the existing cognitive system into software that unknown users can trust, understand, operate, and pay for.

> **RAOS is already close to “someone can pay to try it”; it is not yet at “anyone can safely pay and use it.” The gap is a full layer of product engineering.**

From this point forward, work is split into two explicit tracks:

```text
Cognitive Research Track
  → reacts to real, attributable dogfood residuals
  → does not invent new Core variables without evidence

Productization Track
  → identity / tenancy / cloud runtime / reliability
  → observability / cost / onboarding / trust / billing
```

The product goal is deliberately higher than a hand-held design-partner demo.
## 2. Frozen Launch Target — Private Paid Beta

RAOS should be ready for **50–200 real users** who can:

```text
register themselves
authenticate themselves
connect their own Sources
build or bootstrap their own Context / Kernel
receive automatic Attention judgments
manage WATCH responsibility
see why RAOS interrupted them
pay for the product themselves
operate without the founder repairing their database by hand
```

This is the minimum launch bar worth optimizing toward. A 5–20 user design-partner stage may be used internally on the way there, but it is not the productization destination.

The intended user journey is:

```text
10 minutes  → started
24 hours    → sees concrete value
7 days      → forms a usage habit / dependency
30 days     → willing to renew
```

> **The deep architecture may remain sophisticated; the surface experience must become simpler.**
## 3. Current Maturity Snapshot

The percentages below are directional maturity estimates, not benchmarks.

| Layer | Meaning | Current maturity |
| --- | --- | ---: |
| Cognitive Core | The reasoning/Attention decision machinery: Sensor → Auditor → Kernel localization → effects → Pareto / no-Delta awareness | 85–90% |
| Provenance / replay / causal audit | Ability to reconstruct what happened, rerun it, and identify which cause actually changed the decision | ~85% |
| Acquisition data model | Representation of external information, observations, versions, normalized Sources, and media | 75–80% |
| Single-user dogfood runtime | Ability for one real user to run RAOS continuously and use it day to day | ~80% |
| Reader / Attention UX | The human-facing reading, Attention, Today, explanation, and inspection surfaces | 65–70% |
| Runtime integrity | Ability to prove the running system has the intended semantic identity and authority | 75–80% |
| Production operations | Reliable cloud execution, durable jobs, retries, deployment, backup, monitoring, incident handling | 40–50% |
| Security / identity / tenancy | Authenticated users, ownership, authorization, isolation between users/workspaces | 25–35% |
| Billing / quota / metering | Measuring usage/cost, enforcing budgets, subscription/payment support | 10–20% |
| Self-serve onboarding | A stranger can start and reach a useful state without founder assistance | 25–35% |
| Public SaaS readiness | Overall readiness for unknown paying users on the public Internet | 35–45% |

The important shape is asymmetric: **the cognitive kernel is much more mature than the commercial software shell.**
## 4. Core Data-Model Vocabulary

These are different layers of one information lifecycle, not synonyms.

| Term | Position / role | Function |
| --- | --- | --- |
| `ExternalInformationItem` | External-world identity | Represents “the same thing in the world” across repeated observations or content revisions. |
| `AcquisitionObservation` | Observation provenance | Records that a configured acquisition source actually observed that external item. |
| `InformationSnapshot` | Versioned evidence | Freezes the content state seen at a particular time; later enrichment can create another snapshot without rewriting history. |
| `Source` | RAOS-normalized cognition input | The canonical readable object passed into the cognition pipeline. |
| `AnalysisRun` | One cognitive execution | Records the result and provenance of running the cognition pipeline on a Source. |
| `AttentionPlan` | Authorized attention decision | Stores what RAOS decided the human should do with the information: DROP/AWARE/WATCH/ENGAGE plus urgency/budget/reason. |
| `Watch` | Future-attention responsibility | Represents a continuing responsibility delegated to RAOS to observe a condition or target over time. |
| `Delivery` / `DeliveryEnvelope` | Output transport | Turns an already-authorized Attention decision into in-app/email/push delivery without changing the decision. |
| `Feedback` / `AttentionFeedback` | Human correction evidence | Records append-only user feedback and its causal attribution; it is not automatically treated as personalization preference. |

The intended principle is:

```text
one external thing
→ many observations
→ possibly many snapshots
→ normalized Source versions
→ AnalysisRuns
→ authorized Attention / Watch / Delivery
```

> **Preserve history; do not make later enrichment pretend the earlier observation never happened.**
## 5. Provenance / Replay / Causal-Audit Vocabulary

RAOS treats provenance as a first-class product property because an Attention system must be able to answer “why did you interrupt me?”

| Term | Meaning | Why it exists |
| --- | --- | --- |
| `Source provenance` | Where the information came from, when/how it was acquired, and which external item/snapshot it belongs to | Lets RAOS distinguish evidence origin, revisions, duplicates, and acquisition quality. |
| `AnalysisRun` | The immutable record of one cognition execution | Provides a unit that can be inspected, compared, replayed, or invalidated without rewriting history. |
| `provider / model` | The cognition provider family and actual model used | Proves which model generated the semantic result; prevents hidden model drift. |
| `strategy` | The decision strategy used after cognition, e.g. current Pareto multi-delta policy | Separates “what the model understood” from “how RAOS converted that understanding into Attention.” |
| `execution snapshot` | The relevant runtime/config/state captured for that run | Makes the execution reproducible and explains environment-dependent behavior. |
| `build identity` | Which code build / git SHA / dirty state executed the run | Answers “which implementation produced this result?” |
| `runtime profile` | Versioned declaration of the semantic system that is supposed to run | Answers “who should this RAOS instance be?” independently of local secrets. |
| `decision cause` | The actual load-bearing cognitive/awareness cause that justified the final disposition | Prevents popularity, topic overlap, or incidental features from being mistaken for the reason for Attention. |
| `replay` | Re-run a persisted decision under frozen inputs/configuration | Tests determinism, compatibility, regressions, and counterfactual strategies without repeating upstream web/model calls where possible. |
| `causal audit` | Remove/change candidate causes and see whether the decision changes | Distinguishes correlation/frequency from true decision causality. |

> **A probability, score, or explanation is not enough; RAOS needs reconstructible decision provenance.**
## 6. What “Do Not Prioritize New Cognition Features” Means

This does **not** mean freezing cognition forever. It means the default next step is no longer “make RAOS smarter by adding another cognitive variable, score, prompt stage, ranking heuristic, or policy layer.”

Examples of work that should **not** be invented without a real residual:

```text
new Attention dimensions (R/Q/Novelty/etc.)
new global ranking scores
new scheduler heuristics
new personalization policy
another black-box post-processor
a second independent Attention authority
```

Cognitive research reopens only when real dogfood produces evidence that is repeated, cross-context stable, causally clean, and unexplained by the current Core.

> **The current risk is no longer mainly that RAOS is not smart enough. The larger risk is that a sophisticated Core remains trapped inside software that strangers cannot safely use.**

This is a resource-allocation decision, not a claim that the cognition architecture is finished forever.
## 7. Productization Gap 1 — Identity / Tenant / Security

**Identity** answers “who is this user?” **Tenant/workspace** answers “which isolated ownership boundary does this data belong to?” **Security/authorization** answers “what is this identity allowed to read, mutate, delegate, or deliver?”

This is the multi-user operating-system layer. It must make ownership explicit for private Brain/Attention state:

```text
User / Workspace
  → Kernel
  → D profile / private Context
  → AnalysisRun
  → AttentionPlan / Feedback
  → Watch / WatchDelegation
  → Delivery preferences / credentials
  → private authenticated Sources
```

Public external-world observations may be shareable when provenance/access rules permit, but private cognitive state may not leak across tenants.

Phase 12E already froze the conceptual ownership split. Productization must now implement authenticated identity, authorization, isolation, deletion/export, credential boundaries, and tests that prove cross-user leakage is impossible.
## 8. Productization Gap 2 — Production Runtime

Production Runtime means the execution substrate that keeps RAOS correct and durable when it is no longer running as one developer’s local Mac process. It is **not** a request to rewrite the cognition architecture into microservices.

The preferred evolution is a modular monolith plus durable workers:

```text
Web / App
   ↓
Backend API
   ↓
PostgreSQL
   ↓
Durable Job Queue
   ├─ Acquisition worker
   ├─ Cognition worker
   └─ Delivery worker

Object Storage / Media Cache
```

The important missing properties are durability and recoverability: jobs have IDs, attempts, leases, timeouts, retry/backoff, idempotency keys, dead-letter state, and explicit failure reasons.

A worker crash or machine reboot must not cause lost observations, duplicate cognition, duplicate delivery, or ambiguous half-finished state.

> **Productization should harden the current logical architecture, not replace it with Kubernetes or premature microservices.**
## 9. Productization Gap 3 — Observability

Observability means the system can explain its own operational state from the outside without requiring manual database forensics. It is broader than logs.

Three complementary surfaces are required:

```text
Metrics       → what is happening at scale?
Structured logs → what happened in one execution?
Tracing       → where did one request/job spend time or fail across stages?
```

RAOS-specific operational metrics should include at least:

```text
acquisition success/failure and freshness lag
cognition queue lag and failure rate
LLM latency / token usage / cost
Attention creation rate by disposition
delivery success / duplicate suppression
attestation failures / identity mismatches
reconciliation backlog
connector health and completeness
```

The key invariant alarm is conceptually:

```text
authoritative Attention produced without valid attestation = 0
```

> **Observability is part of correctness: an autonomous system that cannot reveal which capability is broken, delayed, or semantically unauthorized is not production-correct.**
## 10. Productization Gap 4 — Cost / Metering / Quota / Billing

RAOS is not zero-marginal-cost software. It performs background acquisition, embedding, model cognition, and delivery even when the user is not actively looking at the app.

The system therefore needs two separate budgets:

```text
Human attention budget
≠
Machine compute budget
```

**Metering** records consumption: model calls, tokens, embeddings, fetches, storage, media, and delivery. **Quota** limits how much a plan/user may consume. **Cost governance** chooses when to batch, cache, deduplicate, downgrade, delay, or stop work. **Billing** turns plan/usage into payment and subscription state.

Required product controls include per-user/per-workspace compute budgets, per-source polling cadence, daily cognition limits, model routing, deduplication/cache accounting, hard/soft quota behavior, and a visible usage/cost surface.

The product must know the approximate gross cost of serving a user before it can price that user rationally.
## 11. Productization Gap 5 — Cold Start / Zero → Useful Kernel

Cold Start is the first-use problem: the creator’s RAOS is useful because it already knows the creator’s projects, standing interests, Kernel, bottlenecks, and Sources. A stranger begins with none of that.

The product must solve:

```math
Zero \rightarrow Useful\ Kernel
```

without requiring two hours of manual configuration.

A plausible onboarding path is:

```text
connect existing context sources
(GitHub / Drive / Notion / bookmarks / RSS / calendar / etc.)
          ↓
RAOS constructs candidate Context + Kernel + D profile
          ↓
“This is what I think you work on / care about.”
          ↓
user confirms/corrects a small number of items
          ↓
Kernel V0 + initial Sources + initial Watches
```

The target is that a new user reaches a meaningfully personalized first state in roughly 10–20 minutes, and sees concrete value within 24 hours.

> **Cold Start is not onboarding decoration; it is the bridge from a founder-specific intelligence system to a sellable product.**
## 12. Productization Gap 6 — Trust UX

Trust UX is the user-facing explanation layer that makes RAOS understandable without exposing the full research machinery by default. The current design contract and implementation are recorded in `227_RAOS_TRUST_UX_V4_CALM_COMMAND_CENTER_RESULT.md`.

The trust model is:

```text
Trust = Legibility + Causality + Agency
      = I understand it + I can predict it + I can correct it
```

The intended hierarchy is:

```text
Level 1 — Why am I seeing this?
  one short human explanation

Level 2 — What evidence mattered?
  relevant source spans / causal target

Level 3 — Inspector
  full cognition trace, D/S/P, Kernel mapping,
  strategy, provenance, execution identity
```

Normal users should not need to understand Relation Mapping, Pareto frontiers, or Support Binding to use the product safely. Researchers and operators should still be able to inspect them.

Typical user-facing language should look like:

> “This directly challenges your current assumption X.”

or:

> “This does not change your current model, but it materially affects project Y.”

> **The deeper RAOS becomes internally, the less cognitive load its default surface should impose on the user.**

Trust UX also needs temporal continuity. “Today” should be relative to the user's prior visit, not midnight. Single-user dogfood may keep visit-session continuity locally, but Private Paid Beta requires authenticated user/workspace visit state so `Since your last visit` works across devices and sessions.

The corresponding interaction contract is:

```text
user leaves
→ RAOS keeps observing
→ user returns
→ summarize what changed since that prior visit
→ You're caught up
```

## 13. Productization Gap 7 — Dogfood Evidence and Product Metrics

The core product risk is not generic model accuracy. It is attention calibration over time.

Two failure modes kill retention:

```text
over-interruption
→ too many AWARE / ENGAGE events
→ user learns to ignore or disable RAOS

under-interruption
→ important events are missed
→ user stops trusting RAOS
```

The primary product metrics should therefore be:

| Metric | Meaning |
| --- | --- |
| Human-visible residue/day | How much of the observed world survives automatic filtering into user-visible attention |
| Useful interruption rate | Fraction of interruptions the user later considers worth the interruption |
| False interruption rate | Interruptions that should have remained background/noise |
| Missed important item rate | Important items later discovered that RAOS failed to surface appropriately |
| Watch hit usefulness | Whether WATCH actually catches future events the user values |
| Time saved | Estimated manual scanning/research time displaced by RAOS |
| User correction frequency | How often the user must correct Attention, Watch, or understanding |

> **The product truth is “sparse but dependable interruption,” not a high offline accuracy number.**
## 14. Productization Gap 8 — Acquisition Reliability / Legality

Acquisition is RAOS's sensory boundary with the external world. Connector failure therefore degrades what the system can know, even if the cognition Core remains correct.

Each connector should expose operational provenance such as:

```text
connector version
last successful poll
last failure / error class
freshness lag
text completeness
media completeness
authentication state
rate-limit/degraded state
```

Public launch also requires explicit handling of platform Terms of Service, private/authenticated content, credential storage, robots/rate limits where relevant, copyrighted media caching/retention, and user deletion/export requirements.

The desired principle is:

> **Acquire as completely as permitted, represent incompleteness explicitly, and never let a partial acquisition silently masquerade as complete evidence.**
## 15. Launch Gates — the Only Seven Questions That Matter

When asking “Can RAOS start charging real users?”, do not use Phase count as the answer. Use these gates:

1. **Identity** — every user and private object has an explicit owner and authorization boundary.
2. **Reliability** — worker crash/reboot does not lose observations or duplicate cognition/delivery.
3. **Authority** — every canonical Attention decision comes from an ATTESTED authorized runtime.
4. **Cost** — per-user background compute cost is measurable, governable, and bounded by plan/quota.
5. **Trust** — users can quickly understand why RAOS surfaced or interrupted with an item.
6. **Cold Start** — a stranger can reach a useful Kernel/Context/Source configuration in roughly 10–20 minutes.
7. **Dogfood Evidence** — weeks of real use show that RAOS interrupts sparsely without systematically missing important items.

The first six are engineering/productization gates. The seventh is the product truth.

> **A system may be architecturally elegant and still not deserve payment until users repeatedly experience “it caught what mattered and left the rest alone.”**
## 16. Productization Workstreams

The Private Paid Beta target is best treated as a parallel product track, not as another cognition-research Phase.

```text
P0  Multi-user foundation
    Auth / User / Workspace / ownership / tenant isolation / secrets

P1  Durable production runtime
    PostgreSQL / durable jobs / retries / idempotency / object storage / backup

P2  Observability + operations
    metrics / tracing / structured logs / admin health / incident visibility

P3  Cost + plan controls
    metering / quotas / compute governor / subscription / payment

P4  Cold Start + self-serve onboarding
    Context/Kernel/D bootstrap / Source connection / first-value flow

P5  Trust UX
    user explanation hierarchy / feedback / privacy controls / simple surfaces

P6  Connector hardening
    health/completeness contracts / auth sources / rate limits / legal review

P7  Beta evidence
    50–200 user operation / retention / attention-quality product metrics
```
## 17. Definition of Ready — Private Paid Beta

RAOS is ready for the target beta only when a new user can complete the following without founder intervention:

```text
1. create an account and workspace
2. authenticate and connect one or more supported Sources
3. bootstrap a useful Context / Kernel / D profile
4. allow unattended Acquisition and cognition to run for days
5. receive Attention / Today / WATCH outputs with understandable reasons
6. correct mistakes without corrupting personalization evidence
7. see usage/cost/quota state
8. pay for a plan and continue/stop service cleanly
9. export/delete their private data
10. survive worker/process/deployment failures without data loss or duplicate interruption
```

Operationally, the system must support 50–200 users without routine manual database repair, per-user shell intervention, or hidden semantic fallback.

The launch target is intentionally not “perfect enterprise SaaS.” It is a robust, understandable, self-serve paid beta with bounded operational risk.
## 18. Frozen Productization Principles

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.
```

```text
more observed information
→ more automatic machine cognition
→ proportionally less human-visible residue
```

```text
Acquisition = as complete as permitted
Storage     = preserve evidence and provenance
Reader      = progressive disclosure
Attention   = sparse and causally justified
```

> **RAOS should not become easier to operate by making its internal cognition shallower; it should become easier to operate by hiding complexity behind trustworthy defaults and inspectable explanations.**

> **Do not optimize for “more AI output.” Optimize for less human attention spent without losing important reality.**

> **The next milestone is not “RAOS is smarter.” It is “a stranger can safely depend on RAOS without the creator standing beside them.”**

This document is the productization reference until the Private Paid Beta target is reached or explicit evidence justifies revising the target.