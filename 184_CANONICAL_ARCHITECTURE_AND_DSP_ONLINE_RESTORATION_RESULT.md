# RAOS Canonical Architecture + D/S/P Online Restoration Result

Date: 2026-09-13
Status: **CLOSED / DOGFOOD ARCHITECTURE RESTORED**

## 1. Why this work was necessary

Dogfood review found that the validated no-Delta D/S/P awareness branch was absent from the active online pipeline. No later module had replaced it.

The omission arose after Phase 8C split cognitive multi-Delta research from the orthogonal no-Delta awareness branch. The cognitive branch continued through Pareto, Grounding, Authority, Phase 9A, and research==production promotion; the D/S/P branch was never merged back into the online pipeline.

Therefore the earlier `181` rollout is now interpreted precisely as **cognitive-transition-path alignment**, not complete whole-system Attention alignment.

## 2. Canonical HEAD architecture

`RAOS_CANONICAL_ARCHITECTURE.md` is now the authoritative living HEAD contract. Numbered research documents explain historical reasoning; the canonical file states what the repository is intended to execute now.

Any architectural commit must update the canonical document in the same commit when it changes module inventory, responsibility boundaries, main dataflow, Attention authority, execution identity, or research↔dogfood semantics.

The restored Attention split is:

```text
legal CognitiveEffect(s) -> Grounding / Authority -> Magnitude-Free / Pareto -> cognitive Attention
no legal CognitiveEffect  -> audited Event -> D / S / P -> DROP / AWARE
```

Frozen no-Delta gate:

```text
AWARE iff S AND (D OR P)
```

## 3. Online implementation

The Phase 8C.2 Sensor/Auditor bridge now exposes the same audited event projection previously used in Phase 6A, alongside the admitted semantic units used by cognition.

Online dogfood reuses the validated research components directly:

```text
D = standing-radar-fit-estimator-v4 / standing-radar-profile-v4
S = material-consequence-estimator-v1
P = collective-attention-estimator-v1
UNKNOWN composition = no-delta-awareness-integration-v1.1 semantics
```

D/S/P operates only on routable audited Event projections. It does not consume arbitrary whole-article text.

P is not inferred from article wording. Missing external attention evidence remains UNKNOWN. Explicitly labelled engineering estimates or simulations may be used for counterfactual/dogfood measurement, but remain provenance-distinct from observed attention evidence and do not redefine frozen P semantics.

## 4. The Verge article rerun

Source: `OpenAI’s rogue AI tried to hack another company in May`
RAOS Source: `cbaa3e6c-4b39-4421-b55a-2b5ab31f29c0`
New AnalysisRun: `695abb3f-55f5-49ce-8e94-11d5e340d21a`

Research-aligned cognition again produced:

```text
relation_count = 0
authorized_effect_count = 0
Decision Cause = NONE
```

The restored no-Delta branch then evaluated the audited event:

```text
D = IN
S = MATERIAL
P = UNKNOWN
```

Result:

```text
AWARE
```

Scheduler reason: `Δ=NONE with situational awareness: worth knowing, no cognitive write or watch obligation.`

D matched standing clauses for substantive AI-agent/OpenAI involvement and substantive cybersecurity events. S judged the RubyGems disruption MATERIAL because the incident changed the operation/control of a consequential shared package-registry and software-supply-chain system.

This changes the earlier incomplete online outcome:

```text
before DSP restoration: Δ=NONE -> DROP
with canonical DSP path: Δ=NONE, D=IN, S=MATERIAL, P=UNKNOWN -> AWARE
```

No cognitive write, Watch obligation, or KernelPatch was created.

## 5. P counterfactual sensitivity

The current frozen P contract is semantic (`SALIENT / NOT_SALIENT`), not an arbitrary numeric threshold. Therefore the clean counterfactual tests both semantic endpoints rather than inventing a new score law:

```text
D=IN, S=MATERIAL, P=UNKNOWN      -> AWARE
D=IN, S=MATERIAL, P=SALIENT      -> AWARE
D=IN, S=MATERIAL, P=NOT_SALIENT  -> AWARE
```

Thus this article is **P-insensitive**. Direct platform statistics are not needed to decide its final Attention because D and S already make the frozen Boolean gate invariant to P.

## 6. Authority and replay invariants

The restored branch remains subordinate to Cognitive Decision Cause authority:

- D/S/P is evaluated only when the decision strategy has no legal cognitive effect.
- D/S/P may only distinguish `DROP <-> AWARE`.
- D/S/P cannot create `WATCH`, `ENGAGE`, public cognitive update, or KernelPatch.
- UNKNOWN is not coerced to False; unresolved Boolean states fail closed rather than manufacture DROP.
- The DSP contract is included in AnalysisRun execution identity.
- Runtime reschedule reuses the frozen D/S/P trace rather than recomputing or discarding it.

Focused regression: `69 passed, 1 warning`.

Full backend regression:

```text
711 passed
63 skipped
1 failed
1 warning
```

The only failure remains historical Case K (`PREEMPT` expected, `PRIORITY` actual). Zero new regression failures were introduced.

## 7. Closure

The canonical dogfood architecture is now whole-system aligned rather than cognition-path-only aligned:

```text
Acquisition
→ Sensor / Auditor
→ {Cognitive Transition Path | No-Delta D/S/P Awareness Path}
→ Attention
→ exact authorized action
```

Future architectural work must use `RAOS_CANONICAL_ARCHITECTURE.md` as the HEAD comparison baseline so a temporarily isolated research branch cannot silently disappear from the running system again.
