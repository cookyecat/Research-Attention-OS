# RAOS Canonical Architecture — HEAD Contract

Status: **AUTHORITATIVE LIVING DOCUMENT**

This file describes the architecture that the current repository HEAD is intended to execute.
It is not a historical result log. Numbered research documents explain *why* the architecture changed; this file states *what the architecture is now*.

## Maintenance rule

Any commit that changes a RAOS module, responsibility boundary, main data flow, Attention decision path, or research/online semantic contract **must update this file in the same commit**.

If code and this document disagree, the mismatch is an architecture defect to be resolved explicitly; neither side silently wins.

## 1. System objective

RAOS maintains a changing model of the outside information world and allocates scarce human attention relative to a changing cognitive state.

### 1.1 Product operating doctrine

RAOS should observe the world as broadly as practical, understand genuinely new arrivals automatically, and disturb the human as little as possible.

The product promise is stronger than "better recommendations": the user should not have to scan the world personally. RAOS should already have observed and judged the incoming world, so the user can understand within seconds **why these items surfaced, why the rest did not, and whether anything requires action now**.

A canonical product formulation is:

> **RAOS maintains the dynamic state of world events and interrupts the human only when that state crosses a cognitive or attention boundary.**

中文：

> **RAOS 维护世界事件的动态状态，并只在状态跨过认知/注意力边界时打扰人。**

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.

用户不必自己扫描世界。
RAOS 已经替他看过、判断过；
用户只需要迅速知道：为什么是这些、为什么不是那些、现在到底要不要做什么。
```

Canonical product loop:

```text
External World
→ Acquisition
→ Automatic Canonical Cognition for genuine new arrivals
→ Attention allocation
→ User only when warranted
```

The objective is not to reduce how much information RAOS sees. The objective is to increase what the system can observe and process while reducing what must enter human attention. In shorthand:

```text
RAOS should see more than the user,
understand more than the user must read,
and surface only the small residue that deserves human attention.

中文就是：
RAOS 应该比人看到更多，替人理解更多，但只把极少数真正值得的东西交还给人。
```

This implies three distinct product layers:

```text
Inbox      = what RAOS has observed / preserved
Attention  = what RAOS currently judges deserves some attention state
Today      = what should enter the user's consciousness now
```

Acquisition volume and LLM spending are therefore separable engineering quantities, but this separation must never redefine the normal cognitive contract: after baseline establishment, a genuinely new arrival should normally be routed automatically through the canonical cognition path. Manual `Analyze with RAOS` is a recovery/explicit-action mechanism, not the ordinary operating model. Merely opening or reading a Source must never be an implicit cognition trigger.

Historical backlog is different from a genuine new arrival. When a SourceDefinition is first attached, backlog may be persisted as a baseline without cognition so it does not masquerade as newly arrived information. After that baseline, subsequent arrivals enter automatic cognition unless an explicit failure/defer policy says otherwise.

```text
External World W_t
      ↓
Acquisition
      ↓
Observable Information I_t
      ↓
Information / Evidence Representation
      ↓
Cognition relative to K_t
      ↓
Attention / Authorized Action
      ↓
K_{t+1} when explicitly authorized
```



## 2. Canonical HEAD dataflow

```text
Sources / Feeds / APIs / Manual Input
        ↓
──────────────── Acquisition Plane ────────────────
Source Registry → independent Source Poller → Adapter
                                     ├─ RSS / Atom
                                     ├─ WEIBO_PUBLIC / X_PUBLIC
                                     ├─ HACKERNEWS_SEARCH
                                     ├─ BILIBILI_SEARCH / BILIBILI_CREATOR
                                     ├─ SOGOU_SEARCH (blocked residual when public DOM unavailable)
                                     └─ ACTIVE_QUERY_BUNDLE ← WATCH observation intent
                                              ↓ query expansion
                                        child discovery adapters
                                              ↓ retrieval-scope guard
        ↓
SourceDefinition → Observation → Information Object → Snapshot
        ├─→ Attention Signal Ledger (public telemetry state segments)
        │      ↓ magnitude-free platform/context normalization
        │   Event-level P Evidence Packet
        ↓
RAOS Source / Raw Information Boundary
        ↓
──────────────────── Epistemic Plane ────────────────────
Semantic Sensor → Semantic Evidence Auditor
        ↓
Audited Evidence
        ↓
Representation Auditor
        ↓
Probabilistic Epistemic World Representation  P(R | E<=t)
        │
        ├──────────── Topology Commitment Policy ────────────────┐
        │        expected-loss / versioned deterministic gate    │
        │        → MERGE / KEEP / DEFER                          │
        │        → authorized membership / lineage only when     │
        │          commitment policy and Phase13 permit          │
        │                                                        │
        └──────── Event Processor V1 / Event Continuity ─────────┤
                 one normal Source → one primary EventCandidate    │
                 candidate retrieval + SAME / DIFFERENT / UNCERTAIN
                 SAME_EVENT → update existing Event lifecycle      │
                 DIFFERENT_EVENT / UNCERTAIN → separate Event      │
                 cross-Source commitment only through explicit     │
                 Event Processor contract + Phase13 authority      │
                                                                  ↓
        ┌──────────────── Cognitive Transition Path ───────────────┐
        │                                                          │
        │  Locate(K_t) → Relation Mapping → Support Binding         │
        │  → Grounding / OPEN_NEW Jurisdiction → Authority          │
        │  → Cardinal-Free Effect Existence → Magnitude-Free        │
        │  → Pareto                                                  │
        │                                                          │
        └──────────────── No-Delta Awareness Path ─────────────────┤
                                                                   │
           Audited Event Projection → D / S / P                    │
           → AWARE iff S AND (D OR P)                               │
                                                                   ↓
────────────── Decision / Commitment Plane ───────────────
Event-scoped cognitive / no-Delta judgment
        ↓
DROP / AWARE / WATCH / ENGAGE
        ↓
AttentionPlan(candidate_type=EVENT, candidate_id=event_id)
        ├─→ Decision Cause → Public Update / WATCH / authorized KernelPatch
        ├─→ current Attention projection
        │      └─ historical Source plans remain audit history
        └─→ Delivery Envelope (execution only; no decision authority)
                 ↓
          representative Source reading path
                 ↓
          SUPPRESSED / PASSIVE / HELD / INTERRUPT
                 ↓
          in-app realtime / digest / configured external transports
                 ↓
          human acknowledgement / dismissal

──────────────── Agent / Control Plane ────────────────
Agent API / CLI / future MCP-A2A
        ├─ observe / explain / orchestrate
        ├─ invoke canonical cognition
        ├─ delegate WATCH responsibility
        └─ propose actions through existing canonical paths
        ✕ no independent epistemic truth
        ✕ no independent Attention authority
        ✕ no direct topology / Kernel / Delivery authority

──────────────── Integrity Plane ─────────────────────
Phase13 Execution Integrity
        └─ orthogonal gate on every canonical side effect:
           belief persistence (if ever introduced)
           topology mutation
           Attention mutation
           WATCH mutation
           Kernel mutation
           Delivery mutation
```

The two Attention branches are orthogonal. D/S/P is not a substitute for cognitive effects, and cognitive relevance is not a substitute for situational awareness.

For ordinary URL Sources, Acquisition also preserves a structured article view. `content_text` remains the canonical cognition input, while cleaned `article_blocks` preserve headings, paragraphs, semantic lists, quotations, semantic tables and substantive body media for Reader. Publisher chrome (newsletter/share/related/byline/navigation/access-wall furniture) is excluded from Reader structure. Explicit publisher article-body containers are a stronger extraction boundary than an outer page/article shell. Presentation-only hydration may update historical rendering when canonical historical `content_text` is unchanged. If a newly recovered body proves the historical canonical text was incomplete or polluted, RAOS appends a corrected Source/Snapshot and routes it through canonical reconciliation rather than rewriting historical cognition; an explicitly labelled presentation correction may still repair the old Reader link.

Phase 11C realizes the P sensor boundary without changing P semantics. Raw views/likes/comments/ranks are append/extend sensor facts, not P. P remains event-level and is estimated only after event projection; magnitude-free percentiles are diagnostic evidence and remain `UNKNOWN` when reference support is insufficient. Historical signal truth is retained even if future serving layers add current-state/materialized projections for scale.

Phase 11D adds the Delivery Plane as an execution boundary downstream of Attention. Every new persisted `AttentionPlan` owns at most one durable `DeliveryEnvelope`. Delivery policy maps the existing disposition to execution behavior but may never create, promote, downgrade, or reinterpret Attention. WATCH remains delegated future-attention responsibility: only a later canonical WATCH recheck may produce a new AWARE/ENGAGE plan that becomes deliverable. External transport availability/failure cannot mutate the source AttentionPlan.

Phase 11E establishes the Agent / Control Plane. External agents use `/agent/v1`, the `raos` CLI, or `skills/raos/SKILL.md` to invoke existing RAOS capabilities; these surfaces are orchestration/presentation only. Read-only calls never trigger cognition, `analyze` enters the ordinary canonical pipeline, `watch` delegates responsibility into the same durable WATCH model used by RAOS, and `why` explains stored decisions without reanalysis. Agent-originated canonical writes are Phase13-gated. No Agent surface may instantiate `AttentionPlan`, run an independent importance/relevance model, manufacture epistemic truth, or mutate topology/Kernel/Delivery state outside existing authorization paths. MCP/A2A may later wrap this API but must preserve the same Epistemic / Commitment / Integrity boundaries.

## 3. Attention authority split



### 3.1 Cognitive-effect branch

When one or more legal cognitive effects survive the research-aligned cognition contract, D/S/P has no authority over that decision.

```text
REINFORCE / CHALLENGE / OPEN_NEW
→ Grounding / Authority
→ Magnitude-Free / Pareto
→ cognitive Attention
```

This branch may produce AWARE, WATCH, or ENGAGE according to the selected semantic effect and frozen policy. It may authorize public cognitive update, WATCH responsibility, or KernelPatch only from the exact Decision Cause.

### 3.2 No-Delta branch

When no legal cognitive effect survives:

```text
Δ = NONE
→ evaluate audited event(s)
→ D / S / P
→ DROP or AWARE
```

Frozen semantic gate:

```text
AWARE iff S AND (D OR P)
```

D = Standing Attention Jurisdiction / Standing Radar Fit.
S = Material Consequence to a consequential shared reference system.
P = Collective Attention Salience inside the event's objective constituency.

P must come from external attention evidence. Article wording, topic similarity, fame, and model prior must not manufacture current P.
When direct platform statistics are unavailable, an engineering estimator or explicitly labelled simulation may approximate P for dogfood/counterfactual analysis, but it must remain provenance-distinct from observed attention evidence and must not redefine the frozen P semantics.
UNKNOWN is not False. If missing components prevent the Boolean result from being logically determined, the no-Delta decision is unresolved rather than silently coerced to DROP.

## 4. Current contract versions

```text
Acquisition Plane              acquisition-plane-v0.3 / Phase 11A–11B active acquisition
URL article presentation       url-html-v9-publisher-adapters / structured-blocks-v3-tables
Semantic Sensor                semantic-evidence-extractor-v0.2.6
Semantic Evidence Auditor      semantic-evidence-auditor-v0.1.1
World Representation           world-representation-v0.1 / decision-representation-v0.1
Representation Auditor          representation-auditor-frame-pair-v0.7
Probabilistic belief view       representation-belief-view-v0.1 / read-only derived materialization
Representation↔Cognition mix    representation-cognition-marginalization-v0.1 / eval-only algebra
Topology Commitment             representation-authority-shadow-v0.2 / E1 shadow only
Event membership authority      source-local-event-membership-v0.1 / cross-source E2 still closed
Event Attention candidate       event-attention-candidate-v0.1 / AttentionPlan(EVENT)
Current Attention projection    event-centric-current-attention-v0.1 / representative Source path
Event evidence frame            event-evidence-frame-v0.3 / persisted audited semantic units
Frame-conditioned cognition     frame-conditioned-cognition-input-v0.1 / validated eval input / production multi-plan deferred
Agent / Control Plane           agent-interface-v0.4 / event-centric Attention projection / orchestration-only / Phase13-gated writes
Explicit reference provenance  explicit-cites-v0.1 / append-only-parser-hydration
Cognition                      research-aligned-cognition-v1
Relation Mapping               Phase 9A v0.2 frozen contract
Support Binding                Phase 10D.6L.3 frozen contract
Grounding                      Phase 10D.6L.4 frozen contract
OPEN_NEW Jurisdiction          Phase 10D.6L.4J frozen contract
Effect existence               semantic-cardinal-free
Effect calibration             magnitude-free-v0.1
Decision strategy              pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2
D                              standing-radar-fit-estimator-v4 / profile-v4
S                              material-consequence-estimator-v1
P                              collective-attention-estimator-v1
No-Delta gate                  aware-iff-s-and-d-or-p-v1
Unknown composition            no-delta-awareness-integration-v1.1 semantics
Feedback attribution           phase12a-feedback-attribution-v0.1
Multi-actor delegation         watch-delegation-v0.1
Deployment scope               deployment-scope-v0.1 / SINGLE_USER_DOGFOOD
Execution Integrity            execution-integrity-v0.2 / explicit-identity-fail-closed
```



## 5. Core invariants

1. Acquisition observes; it does not judge cognitive relevance or importance.
2. Sensor/Auditor is the shared evidence boundary for both cognition and no-Delta awareness.
3. D/S/P operates on audited event semantics, not arbitrary whole-article topic text.
4. P is a latent collective-attention state estimated from attention evidence, not article prose.
5. D/S/P has authority only when no legal cognitive Decision Cause exists.
6. Attention Policy must not manufacture cognitive change.
7. Decision Cause = Public Update Cause = Authorized Side-Effect Cause.
8. UNKNOWN / unavailable evidence is not negative evidence.
9. Historical snapshots and execution identity are immutable; replay must preserve the frozen contract.
10. Research and active developer dogfood should execute the same validated semantic contract unless an explicit versioned experiment says otherwise.
11. A newly registered Acquisition Source establishes a present-time baseline before cognitive analysis; historical feed backlog must not masquerade as newly arrived information.
12. Failure of one Acquisition Source must not terminate polling of independent Sources; failure of one discovered item must not terminate sibling items in that Source.
13. Acquisition transport and cognition are orthogonal: a Source may be persisted and read without an AnalysisRun; acquisition volume must not imply cognition spending volume.
14. Genuine post-baseline new arrivals should normally enter automatic canonical cognition; baseline backlog, explicit defer policy, or technical failure are exceptions, not the normal product path.
15. Reading/opening a Source is never an implicit cognition trigger. Manual `Analyze with RAOS` is recovery/explicit action, not ordinary scheduling.
16. The system should maximize observable-world coverage while minimizing human interruption: high acquisition/cognition throughput is compatible with a quiet Attention surface.
17. Anonymous public-social adapters may consume only publicly observable material. Authenticated account/following access is a separate explicitly authorized transport layer.
18. Discovery adapters may preserve raw engagement/rank/platform telemetry, but raw popularity is evidence only; it has no D/S/P or Attention authority.
19. Platform-native content with materially incomplete semantics may be persisted under an explicit cognition-defer policy rather than analyzed as if the full content had been observed.
20. Query-bearing Source locators in Phase 11A are fixed observation scope; automatic Query Expansion is a separate Phase 11B capability and may not become cognition authority.
21. Query Expansion and Retrieval Scope Guard are Acquisition-side observation machinery only; neither may assign D/S/P, Delta, or Attention.
22. A WATCH may activate external search only when it projects to a self-contained observation intent; generic trigger labels without sufficient origin context must fail closed rather than broaden silently.
23. Multiple query/adaptor hits for the same canonical ref merge provenance into one external information identity rather than multiplying facts.
24. Human feedback is append-only attribution evidence; it never rewrites the frozen AnalysisRun or historical AttentionPlan.
25. A disagreement is not automatically personalization evidence. Only explicit `HUMAN_EXPLICIT` disposition-only feedback causally attributed to `USER_POLICY_RESIDUAL` is eligible for future `Theta_u`; unresolved, cognitive, runtime, passive, Agent-context, and delivery evidence fail closed outside personalization.
26. Agent delegation provenance is not Attention authority. Multiple Agents may share one canonical Watch through `WatchDelegation`; actor count must not alter D/S/P, Delta, urgency, disposition, or Delivery severity.
27. Cancelling an Agent delegation is actor-local. An agent-only Watch is released only after the last active delegation disappears; core-owned Watch responsibility is preserved.
28. External-world artifacts may be shared only when their access provenance permits it; Kernel-, Runtime-, AnalysisRun-, Attention-, WATCH-, Delivery-, and authorization-dependent state is user/workspace-private by default.
29. Current developer dogfood has no authenticated user identity and no multi-user isolation. No deployment surface may imply multi-user readiness until identity-scoped persistence and authorization are explicitly implemented and validated.
30. Structured presentation is compositional: `article_blocks` may represent cleaned text structure and inline still images, while `media_assets` may carry supplemental video, trusted embeds, or other live media. Enabling structured Reader rendering must never silently suppress preserved substantive media. Presentation composition must not alter canonical `content_text` or cognition history.
31. Presentation fidelity and cognition fidelity are separate contracts. Reader may recompose preserved structure and media for legibility, but presentation metadata may not silently alter canonical Source text, Sensor input, historical AnalysisRun semantics, or Attention authority.
32. Explicit semantic article-body containers outrank outer page/article chrome for URL extraction. Compatibility banners, access walls, navigation, recirculation and recommendation furniture must not become canonical cognition input merely because they are descendants of an outer `<article>` or `<main>`.
33. Semantic tables are first-class article structure. When a publisher exposes a real table, Acquisition should preserve its row/column semantics for Reader instead of flattening it into an undifferentiated paragraph stream.
34. A public-social preview carrying an explicit long-text truncation signal such as “... 全文” is not a complete semantic observation. Acquisition must attempt detail hydration (with stable public identifiers where available) or fail/defer explicitly; it must not silently treat the preview as full content.
35. Presentation-only backfill may upgrade `article_blocks`, `article_structure_version`, `media_assets`, cached presentation media, and an explicit `presentation_hydration` audit record only when canonical `content_text` is unchanged. It must preserve the historical canonical parser/acquisition identity rather than relabel an old Source as if it had originally been acquired under the newer parser.
36. Execution identity absence fails closed just like identity mismatch. A process with no runtime profile and no explicit forensic purpose has no cognition or Attention side-effect authority.
37. `REPLAY`, `FORENSIC`, and explicit compatibility execution may compute forensic cognition, but may not persist canonical AttentionPlan, WATCH, KernelPatch, or Delivery side effects.
38. Existing-run rescheduling is authority-bearing and must pass the same Execution Authority Gate as a fresh cognition run; cached/completed cognition is not a side-effect capability token.
39. Delivery is defense-in-depth: the delivery worker must itself have side-effect authority, and an envelope may reach a human only when its AttentionPlan is backed by an authoritative stored AnalysisRun.
40. Degraded acquisition is recoverable, not terminal. A persisted RSS/discovery fallback remains a valid historical observation, but later polls should retry the publisher URL and append a new full-body Snapshot when the source becomes available; failure to recover must preserve the fallback and record the retry error rather than corrupt or delete history.
41. Media completeness is part of acquisition provenance. When a publisher fallback can recover text structure but cannot verify client-hydrated media, RAOS must record that limitation explicitly and must not present the saved Reader view as media-complete.
42. An explicit article hyperlink authorizes only the literal `CITES` relation. It must not silently imply `SAME_EVENT`, `DERIVED_FROM`, `INDEPENDENT_REPORT`, or `ORIGINAL_SOURCE`; stronger relations require Representation-level adjudication.
43. Historical reference hydration is append-only. New reference extraction may add a new ParserRun and SourceGraph facts, but it may not rewrite the historical parser run or canonical Source text; real historical hydration must fail closed if the freshly extracted canonical text differs.
44. Under `decision-representation-v0.1`, `CITES` is graph/audit context only: it changes `graph_digest` but not `decision_representation_digest`. Transport-only redirect/self-links must not become provenance facts.
45. `content_hash` equality is an identity sensor over observed content, not semantic duplicate authority. `METADATA_ONLY`, stub, empty, or placeholder content may retain a literal hash but may not authorize `REPOSTS`, duplicate suppression, independence reduction, or same-Event fallback.
46. Topology commitment authority is deterministic and versioned. A grounded RepresentationAuditRun may enter probabilistic epistemic World Representation without being certified true; merge, duplicate suppression, independence collapse, or Event-membership replacement require a separate versioned commitment policy plus valid execution authority. Directional provenance (`REPOST` / `DERIVED_FROM`) requires an explicit direction.
47. Execution Authority and Epistemic Belief are orthogonal. Phase13 determines who may mutate canonical state; it does not certify world truth.
48. Auditor response frequency is an observable stochastic response spectrum, not a calibrated probability of objective world truth. Any engineering probability proxy must state this limitation explicitly.
49. Uncertainty is first-class. A grounded uncertain hypothesis may be represented without being coerced to False and without forcing materialized Event topology to collapse.
50. Topology commitment is a decision-under-risk problem. The current `representation-belief-view-v0.1` is read-only and has no merge/suppression/Attention authority.
51. The Agent / Control Plane is orchestration-only. It may observe, explain, invoke canonical cognition, delegate WATCH responsibility, and propose actions, but it may not manufacture epistemic truth, Attention authority, topology authority, Kernel authority, or Delivery authority.
52. Every direct WATCH canonical write, including Agent delegation mutation and active-acquisition activation, must pass Phase13 side-effect authority; read-only Agent/WATCH surfaces remain read-only.
53. Representation uncertainty composition belongs outside the frozen Phase10 conditional cognition kernel. Phase10 continues to estimate `P(T,A | R,K,Theta)` for fixed `R`; any future marginalization over `P(R | E)` must be an explicit outer composition layer.
54. `representation-cognition-marginalization-v0.1` is eval-only algebra. Under `OPERATIONAL_PROXY` weights its information decomposition is diagnostic and has no production Attention or commitment authority.
55. Phase13 gates authority-bearing canonical side effects, not append-only observation/evidence persistence. Source/Snapshot acquisition, parser CITES, Claim/Observation evidence and forensic AnalysisRun artifacts must not be globally blocked merely because cognition side-effect authority is absent.
56. REPLAY/FORENSIC cognition may persist analysis evidence but may not materialize Event/EventSource working topology. Forensic computation must not silently change a later canonical `graph_digest`.
57. Epistemic uncertainty is not automatically decision relevance. A probabilistic hypothesis may remain canonical epistemic context while having zero current decision authority.
58. Under `decision-representation-v0.1`, probabilistic SAME_EVENT belief and candidate Event hypotheses are not direct decision inputs. Resolve or spend additional compute on them only when a future decision contract makes them decision-bearing.
59. Equal Auditor response spectra do not imply equal epistemic evidence strength. `representation-belief-view-v0.1` is a response-spectrum/ignorance proxy; stronger corroboration may leave the proxy unchanged after categorical response saturation.
60. A hypothesis having zero direct influence under the current decision projection does not prove intrinsic decision irrelevance. `not projected into the current decision contract` must be reported separately from `counterfactually decision-invariant`.
61. Controlled evidence evolution is a core Representation-path validation, distinct from natural longitudinal dogfood. Synthetic controlled epochs may test directional update behavior, but they may not be presented as an empirically learned stochastic-process law.
62. Event Continuity is a routing semantic, not a direct Attention score. It answers whether new audited Source evidence updates an existing coarse Event lifecycle or starts a new Event before downstream cognition decides whether Attention should change.
63. Event V1 uses a **coarse editorial episode/story granularity**, not atomic Claim count or atomic state-transition count. One launch episode may include preparation, execution and immediate result; one paper Event may include its method, benchmark results, conclusions and later discussion. The operational test is whether a competent editor would continue one evolving story/case/research story or open a genuinely separate one.
64. V1 defaults one normal Source to one primary `EventCandidate`. Claims, Observations, benchmark values, quotations, attributes and semantic units may enrich that Event but do not create Event multiplicity. Multi-news digest Sources and general `1 Source -> 0..N decision Events` remain a V2/cardinality-contract problem.
65. `extra_source in an AnalysisRun` never implies Event membership. Cognition evidence aggregation has no authority to attach extra Sources to the primary Source's Event; cross-Source membership requires an explicit Event identity resolution/commitment.
66. Event Processor V1 is the only normal canonical path that creates, joins or updates Event topology for a newly analyzed Source. Sensor/Semantic Auditor owns evidence extraction; Event Processor consumes that audited evidence and must not re-audit truth merely to decide Event identity.
67. Canonical Event resolution is `SAME_EVENT / DIFFERENT_EVENT / UNCERTAIN`. `SAME_EVENT` may authorize a new Source to join an existing Event; `DIFFERENT_EVENT` creates a new Event; `UNCERTAIN` must fail safe by preserving a separate Event hypothesis and never performing a hidden merge.
68. Cross-Source Event membership is now enabled only through the explicit coarse Event Processor commitment contract (`llm-coarse-event-resolver-v1` plus Phase13 side-effect authority). Title similarity, actor overlap, raw `EventSource`, or `representation-belief-view-v0.1` response frequency alone still has no topology authority.
69. `AUTHORIZED_SOURCE_LOCAL` remains the initial one-Source Event membership status and does not certify objective world truth. A later explicit SAME_EVENT Event Processor decision may add an `AUTHORIZED` cross-Source membership without rewriting the historical source-local assertion.
70. Event identity is stable while RAOS knowledge is revisable. The materialized Event row is the current representation; append-only `EventRevision` records CREATE/UPDATE knowledge history. Later evidence may fill missing actors/time/location/state or revise the current description without changing Event identity merely because more claims became known.
71. Production current Attention is Event-centric. Canonical new decisions persist `AttentionPlan(candidate_type=EVENT, candidate_id=event_id)`. Multiple historical plans for the same Event remain immutable audit history, while canonical current projection exposes only the latest authoritative decision for that Event. The representative Source is a reading/provenance path, not Attention identity.
72. Policy-generated WATCH responsibility is Event-keyed. Repeated WATCH decisions for the same Event reuse one active Event WATCH and advance its owning/current AttentionPlan; Kernel target ids remain explanatory cognition targets rather than lifecycle identity.
73. Historical ambiguous multi-member legacy topology is preserved for audit but is not automatically trusted. Explicit Event Processor V1 resolution, not legacy graph shape, determines new cross-Source commitment.
74. Canonical identity/schema migrations must quiesce old writers. Rollout order is `stop canonical writers -> migrate -> start one canonical runtime`; mixed manual/service writers or tail writes from deprecated code are invalid operating states.
75. Frame-conditioned cognition may consume only audited semantic units persisted with the EventEvidenceFrame, including explicit evidence supports. Event summary/rendered text alone is not a legal substitute for Support Binding / Grounding evidence. Frame schema version alone is not readiness proof; missing audited units must fail closed.
76. Phase16B multi-frame evidence remains valid research input, but Event V1 intentionally does not emit 0..N production Event plans from one Source. General multi-event digest support requires a separately versioned public/feedback/WATCH/reschedule/Delivery cardinality contract and must not be smuggled into V1 through Claim splitting.
77. Canonical database schema authority belongs to Alembic migrations. Historical migrations must be frozen explicit schema transitions and may not derive schema from current `app.models` / `Base.metadata`; canonical runtime must not use `create_all()` to repair schema drift.
78. Canonical startup must fail closed when the database Alembic revision differs from repository head. A fresh empty database must be able to replay the full migration chain to head and structurally match current ORM metadata with zero drift.
79. SQLite database identity must be cwd-independent. Relative SQLite URLs are normalized to the backend-root absolute path so backend, Alembic, scripts and launchd cannot silently operate on different same-named database files.
80. Canonical service mode is single-owner. Repo-owned orphan manual backend/acquisition/delivery/frontend processes must not coexist with the launchd canonical service set; health checks from an old process are not proof that the newly deployed runtime is healthy.
81. Dynamic Event representation follows Event Sourcing: immutable History / evidence is append-only, while Current EventState is a revisable materialized projection. History and Current State are not interchangeable cognition inputs.
82. Phase17 freezes `EventState = (WorldState, EvidenceState)`. WorldState describes the current episode; EvidenceState describes the current support/provenance structure. EventDecision and Attention remain outside EventState.
83. Dynamic Event evolution is recursive: `S_(t+1) = U(S_t, e_(t+1))`. Normal online cognition should consume a sufficient current EventState rather than replay the entire historical evidence bag on every Source arrival.
84. Evidence accumulation may be stateful and decaying, but EvidenceState is not raw Source count. Reposts/derived reports, independent corroboration, first-party evidence, and technical evidence may carry different informational roles.
85. Attention is stateful and may use hysteresis: upward and downward transition boundaries need not be identical. This permits inertia near boundaries and prevents `AWARE <-> WATCH` or `WATCH <-> ENGAGE` chatter from small fluctuations.
86. `P(SAME_EVENT)` is a relational Representation belief between hypotheses; it is not `Event.confidence`, not WorldState, not EvidenceState, and not Attention score.
87. Longitudinal benchmark Attention labels are profile-scoped Human Gold. A fixed World Trace and Event identity may legitimately yield different Attention trajectories for different Kernels/users; no single personal trajectory is a universal normative label.




## 6. Architecture-change checklist

Before merging an architectural change, check this document against:

```text
module inventory
main dataflow
branching / authority boundaries
versioned contracts
execution identity
online wiring
research ↔ dogfood parity
```

A module that exists only in research code but is required by this diagram is an explicit wiring gap, not an implicit future feature.

---



## 附录: Raw Answer



我真正想要的设计哲学不是“抓很多文章，但都不分析，让用户自己点 Analyze”。那样 RAOS 就退化成了一个 RSS 阅读器，确实违背“注意力操作系统”的核心。

真正应该是下面这套。

External World→Acquisition→Automatic Cognition→Attention→User\boxed{ \text{External World} \rightarrow \text{Acquisition} \rightarrow \text{Automatic Cognition} \rightarrow \text{Attention} \rightarrow \text{User} } 

### 1. Acquisition 的职责：尽可能广地“看见世界”

Acquisition 只回答：

> **外界发生了什么？**

所以它可以大胆抓：

- The Verge
- OpenAI
- DeepMind
- arXiv
- 微博
- X
- 以后更多 RSS、论坛、论文、公众号……

这一层不应该因为 DeepSeek 贵就少抓。

所以我说：

Acquisition volume≠LLM spending\boxed{\text{Acquisition volume} \neq \text{LLM spending}}

更准确的意思是：

> **把一条信息保存进 RAOS，不等于必须立刻花一次完整 LLM cognition 的钱。**

但这句话绝对不等于：

> “RAOS 不自动分析信息。”

---

### 2. 新到的信息，RAOS 应该后台自动判断

这才是 RAOS 的核心。

例如明天上午突然来了 100 条新信息：

```text
微博            25
X               20
新闻/RSS        30
arXiv            20
其他              5
```

理想情况下你根本不应该去 Inbox 一篇篇点：

> Analyze with RAOS

而应该后台自动：

```text
100 new Sources
       ↓
RAOS cognition
       ↓
DROP      72
AWARE     19
WATCH      7
ENGAGE     2
```

最后你打开 Today，只看到：

```text
2 件需要你认真看
7 件 RAOS 替你盯着
19 件知道一下即可
72 件根本不用管
```

这才是：

当外界信息大量涌入时， Attention 仍然保持安静\boxed{ \text{当外界信息大量涌入时， Attention 仍然保持安静} }

这里“安静”不是：

> 什么都不分析，所以什么都不显示。

而是：

> **系统看了很多，但只把极少数东西推到你面前。**

这其实就是 RAOS 最核心的价值。

---

### 3. 那为什么刚才微博 5 条 baseline 没有调用 DeepSeek？

因为那 5 条不是“新发生的东西”，而是我们**刚注册一个新 Source 时，为了建立当前位置而抓回来的历史存量**。

这叫 baseline。

比如我们晚上 9 点第一次接入“斌叔OKmath”。

微博 API 一上来返回最近 5 条：

```text
20:47
20:42
20:41
20:37
20:36
```

这五条其实在 RAOS 开始监控以前就已经存在。

如果一注册一个源，就把：

```text
最近 20 条
最近 100 条
最近 7 天
```

全部当成“刚刚发生的新事件”丢给 cognition，那么每添加一个源都会瞬间制造一场假的信息爆炸。

所以 baseline 的规则是：

Historical backlog→建立当前状态→不伪装成新到信息\boxed{ \text{Historical backlog} \rightarrow \text{建立当前状态} \rightarrow \text{不伪装成新到信息} }

但从 baseline **之后**开始，比如斌叔 21:05 又发了一条：

```text
21:05 NEW POST
```

这才是真正的：

new arrival\boxed{\text{new arrival}}

它应该自动进入 RAOS cognition。

所以：

```text
第一次接源
最近 5 条旧微博
→ library baseline
→ 默认不自动分析
```

而：

```text
接源之后新发的微博
→ new observation
→ 自动 cognition
→ DROP / AWARE / WATCH / ENGAGE
```

这两个必须区别开。

---

### 4. “Reading a Source ≠ Running cognition” 又是什么意思？

这个是另外一件事。

之前我们的 UI 有个很怪的行为：

> 用户点击一篇文章 → 前端发现没有 AnalysisRun → 自动调用 DeepSeek。

这不合理。

因为：

阅读≠分析触发器\boxed{ \text{阅读} \neq \text{分析触发器} }

你只是想打开一篇文章看看，为什么这个鼠标点击动作就应该偷偷烧一次模型？

正确关系应该是：

```text
后台系统决定什么时候 cognition
```

而不是：

```text
用户什么时候点开文章
决定什么时候 cognition
```

所以正常情况应该是：

```text
新信息到达
      ↓
后台已经自动分析
      ↓
用户以后打开文章
      ↓
直接读 + 看已有 RAOS 判断
```

而 `Not analyzed yet` 主要用于几类特殊情况：

- baseline 历史信息；
- 某次 cognition 失败；
- 手工保存但尚未处理的 Source；
- 用户明确要求暂不分析的内容。

所以按钮：

> Analyze with RAOS

应该是一个**补救/主动操作入口**，而不是 RAOS 正常工作流。

---

## 5. 所以整个产品应该有三层，而不是两层

我现在会把它理解成：

World Intake→Cognitive Filtering→Human Attention\boxed{ \textbf{World Intake} \rightarrow \textbf{Cognitive Filtering} \rightarrow \textbf{Human Attention} }

具体就是：

```text
                  外部世界
                     │
     ┌───────────────┼────────────────┐
     │               │                │
   RSS             微博               X
 arXiv            News              APIs
     │               │                │
     └──────────── Acquisition ────────┘
                     │
              大量原始信息
                     │
                     ▼
              RAOS Cognition
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      DROP         AWARE         WATCH / ENGAGE
      70%           20%             10%
       │             │               │
   不打扰你       Brief 中出现       真正进入你的注意力
```

所以 RAOS 的目标不是：

> 少抓信息。

恰恰相反，是：

抓得越广，用户看到得越少。\boxed{\text{抓得越广，用户看到得越少。}}

这句话其实最接近我真正的设计理念。

---

## 6. 那“LLM spending”怎么办？

这里以后还有一层工程优化，但不能污染理论。

理论模型应该始终是：

每一个新信息都应有机会被 RAOS 判断\boxed{ \text{每一个新信息都应有机会被 RAOS 判断} }

工程上，为了省钱，可以以后增加一个 cheap gate：

```text
1000 new items
      ↓
cheap deterministic / embedding / metadata triage
      ↓
200 plausible candidates
      ↓
full Semantic Sensor + Auditor + cognition
      ↓
Attention
```

但这里要非常小心。

cheap gate 只能回答：

> **“这个东西值得花更贵的 cognition 去看吗？”**

不能提前替代 RAOS 做：

> DROP / WATCH / ENGAGE

否则又会出现第二套认知系统。

所以未来更合理的是：

Acquisition→cheap admission control→canonical cognition→Attention\boxed{ \text{Acquisition} \rightarrow \text{cheap admission control} \rightarrow \text{canonical cognition} \rightarrow \text{Attention} }

但目前你还剩 5 元 DeepSeek，而且实测很便宜，我反而不急着做这层。现在更有研究价值的是：

> **先让所有真正的新 arrival 都跑 canonical cognition。**

看看真实信息流量下，RAOS 到底能不能压住噪声。

---

所以把我前面那些话重新压缩成一句：

RAOS 应该尽可能多地观察世界， 尽可能自动地理解世界， 但尽可能少地打扰人。\boxed{ \text{RAOS 应该尽可能多地观察世界， 尽可能自动地理解世界， 但尽可能少地打扰人。} }

这才是我的核心设计理念。

而 Inbox、Attention、Today 三个页面其实也应该对应这三个层级：

```text
Inbox
= RAOS 看见了什么

Attention
= RAOS 判断什么值得占用你的认知

Today
= 此刻真正需要进入你意识的是什么
```

这样一来，整个产品结构就顺了。



RAOS 不是因为外界信息更多而让用户看到更多，\boxed{ \text{RAOS 不是因为外界信息更多而让用户看到更多，} }

而恰恰应该：

系统越忙，人越安静。\boxed{ \text{系统越忙，人越安静。} }

我觉得这句话其实非常接近 RAOS 的产品灵魂。

---

