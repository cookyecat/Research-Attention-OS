# Semantic Sensor Front-End — E1 First Development Attribution

Status: **DEVELOPMENT RESULT / INTERFACE ATTRIBUTION**  
Date: 2026-09-07  
Artifact: `eval/live/results/semantic_evidence_dev_v0_1/semantic_evidence_dev_v0_1_20260907T075436Z.json`  
Sources: RS02, RS09

> This is development evidence, not fresh validation. The purpose is to attribute source-front-end failure modes before expanding the corpus.

## 1. Top-line result

```text
sources attempted                 2
first-pass schema success         0/2
success after one repair          1/2
final schema failure              RS02
semantic batch obtained           RS09
```

RS09 reports `schema_repaired=true`, so although it is finally scorable, the first model output failed structural validation and required a second model call. RS02 remained invalid after the one allowed repair.

Therefore the first conclusion is not `semantic extraction accuracy = 50%`. The first conclusion is:

```text
SemanticExtractionBatch v0.1 / prompt contract is structurally fragile for the model.
```

## 2. RS02 — attributable only to schema contract at this stage

Observed:

```text
failure_kind = schema_validation
error = SemanticExtractionBatchV0_1 invalid after repair
```

The development artifact did not preserve the underlying Pydantic validation errors or the repaired raw JSON, even though the lower-level `SchemaValidationError` carries those diagnostics. Therefore the exact RS02 field-level cause cannot be reconstructed from this artifact.

Decision:

```text
RS02 semantic quality             NOT SCORED
RS02 failure layer                OUTPUT CONTRACT / STRUCTURED EXTRACTION
field-level root cause            UNAVAILABLE DUE TO INSTRUMENTATION LOSS
```

Do not guess a semantic failure from this result.

## 3. RS09 — semantic decomposition is directionally correct

Observed final batch:

```text
event_frames       0
non_event_units    28
all epistemic      SOURCE_CLAIM
```

This is an important positive result. A LocalLLaMA preference/discussion thread was not forced into a fake world event. The extractor preserved it as non-event epistemic material, which supports the source-level split:

```text
RawSource
  -> 0..N EventFrames
  -> 0..N NonEventEpistemicUnits
```

rather than `RawSource = OneEvent`.

## 4. RS09 also exposes three interface residuals

### 4.1 Over-granular extraction

The prompt asks for a small set of high-value units and says normally `<=20` non-event units, but the executable schema allows up to 500. The result contains 28 units.

This is a contract mismatch:

```text
Prompt contract != Executable schema contract
```

### 4.2 Single-support non-event schema encourages one-comment-per-unit

`NonEventSemanticUnitV0_1` contains only one `support_pointer` / `support_excerpt`. It cannot naturally express one aggregate semantic unit supported by several discussion comments.

Therefore the schema itself encourages comment-by-comment transcription. A later interface should permit multiple source supports per non-event semantic unit.

### 4.3 Weak review provenance / undefined confidence semantics

In RS09:

```text
support_excerpt empty    28/28
confidence UNKNOWN       28/28
```

Pointers exist, so provenance is not absent, but reviewability is weaker than intended. Confidence also has little information value because the prompt does not clearly define whether it means source-truth confidence or extraction/support confidence.

Decision: define confidence as confidence in source-grounded extraction/attribution, not truth of the underlying claim.

## 5. Cost / repair amplification

RS09 reports approximately:

```text
latency_ms          39,743
prompt_tokens       41,693
completion_tokens    9,085
schema_repaired       true
```

These token counts are merged across the initial invalid call and the repair call. The repair path therefore materially amplifies cost/latency and should not be treated as normal success behavior.

## 6. v0.2 design decision

Do not consume more development sources under the known-fragile v0.1 interface.

Minimal v0.2 changes:

1. Provide the model an explicit compact JSON output contract on the first call rather than only naming the Pydantic class.
2. Make executable limits match prompt limits: `event_frames <= 8`, `non_event_units <= 20`.
3. Allow each non-event semantic unit to carry multiple source supports so discussion evidence can be aggregated.
4. Require short diagnostic support excerpts for non-event units.
5. Define `confidence` as extraction/support confidence, not claim truth.
6. Preserve schema errors, repaired raw output, repair usage, and model metadata on final schema failure.

No D/S/P semantics, Attention policy, or event ontology changes are justified by this run.

## 7. Current status

```text
E0 input integrity                  CLOSED for first dev pair
v0.1 first semantic run             COMPLETE
RS09 event/non-event discrimination SUPPORTED
v0.1 structured-output reliability  NOT ACCEPTABLE
v0.1 non-event support model        REVISE
next                                Semantic Sensor interface v0.2
additional corpus consumption       PAUSE until v0.2
```
