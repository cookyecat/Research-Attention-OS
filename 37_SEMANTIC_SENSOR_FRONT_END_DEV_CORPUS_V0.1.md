# Semantic Sensor Front-End — Development Corpus v0.1

Status: **ACTIVE DEVELOPMENT / NOT FRESH VALIDATION**  
Date: 2026-09-07  
Parent: `33_SEMANTIC_EVIDENCE_EXTRACTION_FRONT_END.md`  
Frame: `36_SEMANTIC_EVIDENCE_FRAME_V0.1.md`  
Mathematical registry: `35_RAOS_MATHEMATICAL_LANGUAGE_REGISTRY.md`  
Corpus manifest: `eval/live/manifest.semantic_evidence_dev_corpus.v0.1.yaml`

---

## 1. Purpose

Use real/raw information objects already present in `eval_samples/` to calibrate the
Semantic Evidence Extraction / Sensor Front-End before freezing a production or fresh
validation interface.

The corpus is development data. It may be inspected, prompt-tuned, manually adjudicated,
and repeatedly rerun. It must never later be reported as fresh extractor-generalization
evidence.

---

## 2. Corpus split

The repository currently contains 14 `eval_samples` items.

```text
RS01-RS12   DEVELOPMENT
RS13-RS14   RESERVED / NOT IN DEV CORPUS
```

The first 12 contain a useful mixture of:

```text
PDF research papers / technical papers
plain-text technical/tutorial material
interview / long-form compilation
community discussion / Markdown
AI/robotics news/features
```

The split is pinned by Git blob SHA in the manifest.

Do not consume RS13/RS14 merely to enlarge the development set.

---

## 3. First real-source finding: Source != Event

Development inspection immediately falsified the convenient assumption:

```text
one RawSource = one Event
```

Examples:

```text
RS02
  source summarizes Lauren Tan's AI-coding workflow,
  empirical productivity claims, methodology, and opinions.

RS05
  is a PyTorch profiler tutorial containing technical explanations
  and observations, not one natural news event.

RS06
  is a long Sam Altman interview containing multiple claims,
  predictions, company-strategy statements, and reported facts.

RS09
  is a LocalLLaMA discussion thread with many participant preferences,
  not a single canonical underlying event.
```

Therefore the sensor front-end must not force every source into exactly one event frame.

---

## 4. Revised source-level architecture

Reuse the already-frozen epistemic extraction concept rather than inventing a second
parallel document-understanding ontology.

Canonical cognitive path already has:

$$
E_t=Extract(I_t)
$$

with Claims / Observations / Inferences / Evidence.

The Sensor Front-End development architecture is now:

```text
RawSource I_t
    ↓
SemanticExtractionBatch
    ├── 0..N event-like / result-like units
    │       ↓
    │   SemanticEvidenceFrame(s)
    │       ↓
    │   D-hat / S-hat
    │   + constituency semantics for P
    │
    └── non-event epistemic units
            ↓
        cognitive path / E_t
```

The batch boundary is implemented in:

```text
eval/live/semantic_evidence_batch_v0_1.py
```

This is routing/representation, not a new physical variable.

---

## 5. Evidence boundary

Both event frames and non-event units must remain source-grounded.

For event frames:

```text
source -> evidence -> actor/change/affected-system
```

For non-event units:

```text
source_id + support_pointer + short support_excerpt
```

No source content may become D/S/P/A inside the sensor representation.

Invariant:

$$
\boxed{Evidence\neq StateEstimate\neq PolicyAction}
$$

---

## 6. D version clarification before E2

The mathematical D definition remains frozen:

$$
D(E,u)=\bigvee_i \rho_i(Sem(E),u)
$$

and:

$$
D(E,u)=\mathbf1[E\in\mathcal J_u]
$$

The user's concrete Standing Radar Clauses are parameters $\mathcal R_u$, not the
physical definition of D.

After integrated IA adjudication, `standing_radar_profile.v3.yaml` is no longer the
latest user profile. Future development uses:

```text
standing_radar_profile.v4.yaml
```

Key user-parameter clarifications include:

```text
pure energy/grid as such                    OUT by default
AI/data-center-compute-coupled power        may be IN via independent compute clause
trivial OpenAI/DeepMind internal admin      OUT
substantive AI/research/product/governance  IN
trivial family-affiliated facilities detail OUT
substantive institution-level affiliation   may be IN
```

These calibrate $\mathcal R_u$ and do not reopen D semantics.

---

## 7. Evaluation program

### E0 — source ingestion integrity

Before LLM semantic extraction:

```text
verify Git blob
extract text without silent truncation
preserve paragraph/page support markers
report source length/page count
```

Runner:

```text
eval/live/run_semantic_source_inventory_v0_1.py
```

### E1 — extraction fidelity

For development sources, inspect:

```text
source/event segmentation
major epistemic-unit recall
substantive actor/object fidelity
action/change fidelity
affected-system/scope fidelity
temporal-status fidelity
unsupported-inference rate
missingness honesty
provenance completeness
```

Do not collapse these into one master score yet.

### E2 — downstream invariance

Once a Human-adjudicated frame exists for the same raw source:

```text
Human semantic evidence -> D/S/P
LLM semantic evidence   -> D/S/P
```

Measure whether extraction alone changes downstream state estimates.

### E3 — end-to-end policy

Only after E1/E2 failure modes are understood:

```text
RawSource -> Sensor -> D/S/P -> Frozen Policy -> Attention Action
```

---

## 8. Initial development sequence

Do not begin by blindly running all 12 sources.

Recommended sequence:

```text
1. Inventory RS01-RS12 with no LLM call.
2. Run RS02 and RS09 first.
   - one workflow/claim-heavy source
   - one community-discussion source
3. Inspect whether event_frames vs non_event_units are represented naturally.
4. Run RS05 and RS06.
   - tutorial
   - multi-topic interview
5. Only then extend to research PDFs and the remaining news/features.
6. Revise candidate v0.1 representation only for attributable representation failures.
7. Freeze sensor interface only after the development corpus no longer forces semantic leakage or unnatural one-source-one-event assumptions.
```

---

## 9. Current state

```text
D semantic definition                    FROZEN / aligned
Latest user Standing Radar profile       v4 calibrated
S semantic / estimator                   stable controlled baseline
P semantic / estimator                   stable controlled baseline
No-Delta AWARE composition               frozen
SemanticEvidenceFrame v0.1               candidate
SemanticExtractionBatch v0.1             candidate
Real-source dev corpus RS01-RS12         pinned
RS13-RS14                                 reserved
Extractor v0.1                            implemented for development
Fresh extractor validation                NOT STARTED
```

Current question:

> Can RAOS recover a faithful, provenance-preserving semantic representation from messy raw sources without forcing non-event content into event-shaped boxes or leaking downstream D/S/P/A judgments into the sensor?
