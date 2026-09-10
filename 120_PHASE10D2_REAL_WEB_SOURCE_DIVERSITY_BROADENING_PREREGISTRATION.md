# Phase 10D.2 — Real-Web Source-Diversity Broadening Preregistration

Status: PREREGISTERED / NO RAOS OUTCOMES OBSERVED

## Question

Does the Static Probabilistic Cognitive Map remain useful after broadening beyond the four Phase 10D.1 real-web sources across publisher, source style, topic, and prior distance from the frozen Phase 6B Cognitive Kernel?

This phase is external-sample broadening, not theory promotion and not temporal persistence testing.

## Selection rule frozen before RAOS execution

Select six public real-web sources in three strata, two sources per stratum, with six distinct publishers where practical:

- `NEAR_KERNEL`: directly concerns embodied/robotic intelligence or multi-agent architecture/coordination.
- `BOUNDARY`: concerns agentic AI systems and workflows but is not directly about the current embodied-control / multi-agent kernel propositions.
- `FAR_CONTROL`: high-quality technical/scientific information with no intended direct relation to the current AI/robotics kernel.

Selection uses only publisher/source type and prior topic distance. No Sensor, Auditor, Locate, Relation Mapping, Decision-Causal Core, or Attention output may be inspected before the source list is frozen.
## Frozen Batch-2 sources

| Label | Stratum | Publisher | Source |
|---|---|---|---|
| N1 | NEAR_KERNEL | Google DeepMind | Gemini Robotics 2 brings whole body intelligence to robots |
| N2 | NEAR_KERNEL | Google Research | Towards a science of scaling agent systems: When and why agent systems work |
| B1 | BOUNDARY | Anthropic | Trustworthy agents in practice |
| B2 | BOUNDARY | OpenAI | Research acceleration: The view inside OpenAI |
| F1 | FAR_CONTROL | NIH | Scientists identify new role for tau protein in brain diseases |
| F2 | FAR_CONTROL | NASA | NASA's Webb Discovers Hidden Planet in Famous Star System |

URLs are frozen in `eval/live/manifest.phase10d2_real_web_broadening.v0.1.yaml`.

## Measurement protocol

For each source:

1. Acquire the URL once and record canonical URL, content hash, content length, parser metadata, and acquisition failure separately.
2. Run one fresh Sensor v0.2.6 + Auditor v0.1.1 perception pass and freeze the complete admitted semantic world including `unit_id` and `supports`.
3. Run Locate three times; use the modal target set/fixture for the repeated Relation experiment while preserving Locate stability diagnostics.
4. Run Relation Mapping with the frozen semantic world and frozen Locate under `Anchored OPEN_NEW + Magnitude-Free + Pareto`.
5. Start at `N=12`; expand to `N=24` only under the same Wilson precision gate used by Phase 10A / 10D.1.
6. Compute empirical `P(r in T)`, load-bearing `P(r in B_pi(T))`, Attention distribution, topology entropy, load-bearing entropy, and Wilson intervals.
## Frozen interpretation gates

- This batch tests external-sample feasibility, not population prevalence.
- No source may be removed because its Attention distribution is inconvenient or degenerate.
- Acquisition failures, parser anomalies, schema failures, and empty-effect controls remain in the record.
- A source-level URL acquisition failure does not authorize substitution: retain the failed preregistered source as an acquisition-failure row and continue the remaining preregistered sources.
- A source-level Sensor/Auditor technical or schema failure is likewise retained without substitution; the failed source is not retried inside the same batch merely to obtain a usable map.
- `Jaccard`/topology entropy remain representation-level measures; decision conclusions must use load-bearing and Attention distributions.
- `OPEN_NEW[UNRESOLVED]` remains unresolved rather than being merged by free-text semantic similarity.
- No thresholds, calibration bands, prompts, Kernel nodes, or downstream strategy may be tuned from Batch-2 outcomes.
- Production default remains `one-delta-v1`.

## Progression rule

After Batch-2, combine Phase 10A + 10D.1 + 10D.2 descriptively. Only after this broader sample is inspected may a new causal attribution be preregistered. Do not rewrite the probabilistic theory merely because one case is unusual.
