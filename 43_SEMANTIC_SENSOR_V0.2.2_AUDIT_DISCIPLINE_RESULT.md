# Semantic Sensor v0.2.2 — Audit Discipline Result

Status: **DEVELOPMENT RESULT — PARTIAL PASS / EVIDENCE SUFFICIENCY RESIDUAL OPEN**  
Date: 2026-09-07

## 1. Controlled change

v0.2.2 changed only prompt-level audit discipline over v0.2.1. The schema, temporal-anchor policy, Event/Epistemic representation, and D/S/P semantics were unchanged.

Targeted residuals:

1. evidence sufficiency rather than mere traceability;
2. bare URL / page-chrome filtering;
3. SOURCE_CLAIM vs extractor inference discipline;
4. Event / Epistemic payload deduplication.

Development source: RS02 only.

## 2. Run result

Artifact:

`eval/live/results/semantic_evidence_dev_v0_2_2/semantic_evidence_dev_v0_2_2_20260907T103010Z.json`

Measurement HEAD:

`694ef6fd99f0f18fe10663af28c7176b069b7fe4`

Observed:

```text
n_sources            1
n_scorable           1
n_first_pass_valid   1
repair_used          false
event_frames         1
non_event_units      12
model                deepseek-v4-flash
```

## 3. Clear improvements

### 3.1 Temporal-anchor regression remained fixed

The extractor preserved source-relative expressions such as previous/current month and explicitly left absolute dates unresolved because `source_published_at=unknown`.

Result: **PASS**.

### 3.2 Bare URL / locator filtering

The v0.2.1 non-event unit created from the naked X URL disappeared. No semantic claim such as “the linked video presumably contains...” was emitted.

Result: **PASS**.

### 3.3 Epistemic attribution

The prior unsupported `presumably` inference disappeared rather than being mislabeled as `SOURCE_CLAIM`.

Result: **PASS on the observed residual**.

### 3.4 Event / Epistemic deduplication

The standalone non-event restatement that Lauren now allows agents to auto-merge PRs disappeared. The automatic-merge fact remained inside the Event Frame.

Result: **PASS on the observed residual**.

### 3.5 Compression / granularity

The two v0.2.1 Event Frames were compressed into one broader Event Frame combining PR-volume activity and the transition to auto-merge. Non-event units reduced from 14 to 12.

This is plausible evidence-preserving compression, but event granularity is not yet Human-Gold adjudicated, so it is not scored as correctness.

## 4. Evidence sufficiency residual remains OPEN

The key targeted residual was not fully fixed.

The Event Frame emits:

```text
affected_system = Cursor codebase
```

but its support ids are:

```text
ev-rs02-001 -> PARA 0004
  PR counts / time period

ev-rs02-002 -> PARA 0011
  auto-merge into main / verification
```

Neither cited evidence contains the explicit source support from PARA 0005:

```text
“这不是 AI slop code，而是你每天都在使用的 Cursor 的代码。”
```

Therefore the affected-system statement is traceable to the event but not backed by the smallest sufficient evidence set.

Formal finding:

```text
Traceable Provenance != Sufficient Provenance
```

and more importantly:

```text
Structural Provenance Validation != Semantic Evidence Audit
```

The existing schema can verify that `support_ids` exist. It cannot verify semantic entailment/support between an evidence excerpt and the semantic object that cites it.

## 5. Test-design correction

The v0.2.2 regression fixture demonstrated that a correctly supported object (`Cursor codebase -> PARA 0005`) is accepted.

It did **not** demonstrate that an incorrectly supported object (`Cursor codebase -> PARA 0004/0011`) is rejected.

This distinction must be preserved. Passing the structural regression test must not be reported as semantic-evidence-sufficiency validation.

## 6. Interpretation

v0.2.2 shows that prompt-level discipline is effective for several generation-behavior residuals:

```text
locator filtering        improved
inference attribution    improved
cross-representation dedup improved
temporal honesty         preserved
```

but evidence sufficiency remains a semantic verification problem.

Do not continue indefinitely adding stronger prompt wording and then infer that provenance correctness is guaranteed.

## 7. Next recommended frontier

Introduce a separate **Semantic Evidence Audit** stage after extraction:

```text
Raw Source
   ↓
Semantic Sensor
   ↓
SemanticExtractionBatch
   ↓
Semantic Evidence Audit
   ↓
Audited Semantic Skeleton
```

For each semantic object, audit:

```text
object statement
+ cited evidence excerpt(s)
→ SUFFICIENT / INSUFFICIENT / UNCERTAIN
```

If insufficient, return which semantic object failed and what support is missing. Any repair should remain source-grounded and must not invent evidence.

This audit is an engineering verifier, not a new theoretical RAOS variable.

## 8. Current status

```text
Temporal Anchor                          CLOSED
First-pass structural validity           PASS on RS02
Bare URL / locator filtering             OBSERVED PASS
Epistemic attribution residual           OBSERVED PASS
Event/Epistemic duplicate residual       OBSERVED PASS
Evidence sufficiency                     OPEN
Semantic audit capability                NEXT FRONTIER
Fresh validation                         NONE
```

Core lesson:

> **A provenance graph is not trustworthy merely because every edge points somewhere. Each edge must point to evidence that actually supports the meaning carried by that edge.**
