# Phase 9A — Post-10D.6L Instrument Amendment

**Status:** PREREGISTERED / NO PHASE 9A OUTCOME YET
**Date:** 2026-09-13

## Why v0.1 cannot be executed

The original Phase 9A scientific question remains unchanged: with evidence `E` frozen, does an accepted Kernel intervention `K0 -> K1` cause the expected change in `M(E,K)` beyond fixed-K stochastic variation?

The unfinished v0.1 runner predates 10D.6L/10D.6K and is no longer a valid instrument. It reintroduces legacy `legal_public_effects()`, uses the pre-cardinal-free strategy, preserves LLM cardinal fields, and lacks the now-frozen Support Binding / Grounding / Authority separation. No Phase 9A outcome has ever been sampled with it.

The old v0.1 files are retained as historical WIP and must not be interpreted as a valid measurement path.

## Frozen causal variable

Evidence is the exact frozen RS05 Auditor artifact SHA256 `aa594aab2b7b2f0e252dbf3ed8978865e03d9ddd1b905c8f38db0ae60ea5711f`. Locate is frozen to the same `CF-B-PERF` node identity in all arms. The production KernelPatch -> accepted KernelVersion path remains the only way to construct K1-S and K1-I.
## v0.2 cognition path

Only Relation Mapping is stochastic. It uses a Phase9A-specific cardinal-free relation schema: `operation`, `target_kernel_node_id`, `reason`. It may emit `REINFORCE`, `CHALLENGE`, or `OPEN_NEW`, but it cannot emit magnitude, epistemic strength, importance, support IDs, Attention, or priority.

Support Binding is deterministic for the preregistered target relation: any targeted relation on `CF-B-PERF` is bound to `RS05-U01`, the direct frozen evidence that GPU kernel time is <1% of CPU time and the workload is overhead-bound. Other RS05 units remain visible context to Relation Mapping but cannot independently authorize the target relation.

Grounding is deterministic and preregistered from the proposition/evidence pair:
- K0 and K1-I retain the original computation-dominates proposition: `CHALLENGE(CF-B-PERF)` is DIRECT; `REINFORCE(CF-B-PERF)` is rejected as opposite to the frozen evidence.
- K1-S contains the accepted overhead-dominates proposition: `REINFORCE(CF-B-PERF)` is DIRECT; `CHALLENGE(CF-B-PERF)` is rejected as opposite to the frozen evidence.

`OPEN_NEW` has no frozen jurisdiction anchor in this single-belief Locate experiment and is rejected by Anchored admission; it cannot become a competing causal path.
## Authority and downstream execution

For every retained targeted relation, Grounding assigns `SUFFICIENT` epistemic authority because `RS05-U01` is the preregistered direct audited support. Standing importance is never supplied by the Relation Mapper. It is resolved only from the materialized KernelVersion: K0/K1-S `importance=0.9 -> HIGH`; K1-I `importance=0.2 -> LOW`.

Retained effects enter `pareto-multidelta-cardinal-free-anchored-open-new`; raw `change_magnitude` has zero effect-existence or ranking authority. Magnitude-Free, Pareto, article Attention, and Decision-Causal Core are otherwise unchanged from the repaired 10D.6L/10D.6K path.

Expected mechanistic channels under a correct target relation are frozen before outcome:
- K0: `CHALLENGE + HIGH + SUFFICIENT -> ENGAGE`.
- K1-S: ordinary BELIEF `REINFORCE + HIGH + SUFFICIENT -> AWARE`.
- K1-I: `CHALLENGE + LOW + SUFFICIENT -> AWARE`.

The same final `AWARE` for K1-S and K1-I must not be interpreted as the same cognitive state: one is semantic assimilation (`CHALLENGE -> REINFORCE`), the other preserves challenge topology but changes standing importance.
## Sampling design — paired where causally appropriate

Initial target remains `N=12` semantic realizations. K0 and K1-S each receive 12 fresh Relation-Mapping calls with identical evidence, target identity, prompt template, model/configuration, and call settings; only the target proposition text differs. Call order alternates by ordinal to reduce provider-time drift.

K1-I does **not** receive an independent Relation-Mapping call. Its proposition is byte-identical to K0 and importance is intentionally hidden from Relation Mapping, so each K0 realization is replayed unchanged through K1-I authority/downstream policy. This produces an exact paired intervention and removes stochastic semantic variation from the importance-only test.

If the K0 vs K1-S semantic direction is consistent but the preregistered permutation gate is unresolved at N=12, expand K0 and K1-S to `N=24` each using the same alternating schedule. K1-I expands automatically by replaying the corresponding new K0 realizations. No arm may be expanded because the observed direction is inconvenient.

The Relation-Mapping prompt must be arm-blind: it receives evidence and the materialized Kernel proposition but never the labels `K0`, `K1-S`, `K1-I`, expected polarity, expected Attention, or any Grounding answer.
## Primary measurements and causal gates

For Relation Mapping, collapse the targeted `CF-B-PERF` output of each realization into one preregistered polarity state: `CHALLENGE_ONLY`, `REINFORCE_ONLY`, `BOTH`, or `NONE`. Unknown target identifiers or schema-invalid outputs are retained as invalid outcomes and are never silently resampled.

**Primary K0 vs K1-S semantic endpoint:** the target-polarity distribution must move from CHALLENGE-dominant under K0 toward REINFORCE-dominant under K1-S. Report target-operation frequencies and JSD over the four polarity states. Support requires the existing 5000-permutation gate: observed JSD above null p95 and tail probability <= 0.05, together with the preregistered directional modal change.

Full relation topology, authorized topology after Grounding, load-bearing topology, and article Attention are secondary maps. They diagnose how much of the semantic shift survives downstream; they cannot substitute for failure of the raw target-polarity endpoint.

**Primary K0 vs K1-I allocation endpoint:** because each K1-I sample reuses the exact K0 relation realization, targeted topology must be identical by construction. For every pair whose targeted CHALLENGE is retained, K0 must resolve HIGH importance and K1-I LOW importance, with the expected mechanistic Attention transition `ENGAGE -> AWARE`. Any semantic-topology difference in this paired replay is an instrumentation failure, not an experimental result.

Marginal Attention JSD may be reported descriptively for K0 vs K1-I, but independent-sample permutation significance is not appropriate for this paired arm. Report paired transition counts and exact invariant violations instead.
## Interpretation matrix

A clean positive result requires the two interventions to separate mechanistically:
- **Semantic assimilation (K1-S):** raw target polarity moves `CHALLENGE -> REINFORCE`; authorized relation follows that direction; any Attention reduction is interpreted as a consequence of semantic assimilation, not reduced importance.
- **Importance downshift (K1-I):** raw/authorized target relation is replay-identical to K0; only the authoritative importance band changes; Attention decreases without semantic topology change.

If K1-S changes authorized topology only because deterministic Grounding rejected an opposite raw relation, but raw Relation Mapping itself does not show the preregistered directional shift, semantic causal alignment is **not** supported. Grounding is a safety gate, not evidence for the primary relation-reversal claim.

If K1-I fails to change Attention despite the same retained CHALLENGE and verified HIGH->LOW importance change, the failure belongs downstream of Relation Mapping and should be attributed to Authority/Magnitude-Free/Attention policy rather than semantic cognition.

If K0 itself fails to produce a concentrated CHALLENGE baseline under the new relation-only instrument, record measurement-interface drift relative to historical Phase 10; do not tune the prompt after outcome.
## Supersession and guardrails

This amendment supersedes the sentence in `131_PHASE9A_INSTRUMENT_AUDIT_AND_PREREGISTRATION_AMENDMENT.md` that called that document the only pre-measurement correction. The supersession is justified solely by architecture/instrument changes established in 10D.6L/10D.6K **before any Phase 9A outcome was sampled**. Historical preregistrations are retained unchanged for provenance.

Guardrails:
1. Freeze the RS05 Auditor artifact, target node identity, K0/K1 propositions, importance values, support unit `RS05-U01`, relation schema, Grounding rule, strategy ID, sample size, expansion rule, and statistical gates before measurement.
2. Do not expose arm labels, expected relation, expected Attention, support choice, or strong Grounding rule to Relation Mapping.
3. Do not rerun Sensor, Auditor, Locate, Support Binding, or evaluator-capacity experiments inside Phase 9A v0.2.
4. Do not use legacy `legal_public_effects()` or any positive fake `change_magnitude` to admit effects.
5. Do not mutate the live Kernel or production database; K1 arms must be materialized through the accepted production patch/version path in an isolated database.
6. Do not claim correctness from stability alone; Phase 9A tests causal alignment to an explicit, human-authorized Kernel intervention.
7. Do not let the benchmark-paper narrative change the experiment after outcome. The benchmark may consume Phase 9A results; Phase 9A may not be tuned to support the benchmark thesis.

**Freeze status:** once this document and the v0.2 measurement contract are committed, implementation may repair only deterministic plumbing/invariant failures. Any semantic change to prompt, intervention, support, Grounding, sample selection, or gates requires a new explicit pre-outcome amendment.
