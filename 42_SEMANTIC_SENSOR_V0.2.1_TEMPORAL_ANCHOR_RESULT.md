# Semantic Sensor v0.2.1 — Temporal Anchor Controlled Result

Status: **TEMPORAL RESIDUAL CLOSED / NEW PROVENANCE RESIDUALS OPEN**  
Date: 2026-09-07

## 1. Motivation

RS02 v0.2 exposed a deictic-time error: the source said `上个月 / 这个月才过去12天`, while source publication time was unknown, but the extractor described those expressions as relative to the RAOS measurement date.

That violated:

```text
measurement time != source time != event time
```

v0.2.1 changed only temporal-anchor plumbing/prompt policy. The SemanticEvidenceFrame schema, Event/Epistemic split, D/S/P, and batch contract remained unchanged.

## 2. Controlled result

RS02, same raw source, same model family:

```text
n_scorable           1/1
n_first_pass_valid   1/1
repair_used          false
event_frames         2
non_event_units      14
source_published_at  unknown
```

The key corrected output is now:

```text
Previous month and first 12 days of current month,
relative to the source;
absolute dates unresolved because source publication date is unknown.
```

and explicitly:

```text
Source-relative time is preserved;
no absolute calendar dates are inferred.
```

Therefore the original error:

```text
relative to measurement date
```

is no longer present.

## 3. Decision

```text
Deictic temporal-anchor residual: CLOSED for the observed failure mode.
```

The engineering contract is:

```text
If source published/captured time is available:
    use it as the anchor for source-relative expressions.

If source time is unavailable:
    preserve relative expressions and mark absolute dates unknown.

Never substitute measurement as_of for source time.
```

## 4. New residual: traceable provenance is not sufficient provenance

The v0.2.1 run exposed a more precise audit requirement.

Event 1 contains:

```text
affected_system = Cursor codebase
reference_scope = The merged PRs are described as Cursor's code.
```

This meaning is supported by the source, but the event's only evidence record points to the paragraph containing PR counts. The more direct support for `Cursor code` is in the following paragraph.

So the provenance graph is structurally valid but semantically under-bound.

New principle:

```text
Traceable Provenance != Sufficient Provenance
```

A semantic object should not merely reference an existing evidence id from the same event. The cited evidence must actually support that specific semantic object.

This is particularly important for auditability.

## 5. New residual: non-semantic raw artifacts should not become Epistemic Units

The extractor emitted a non-event unit for the bare X/Twitter video URL and added:

```text
presumably contains Lauren Tan's full explanation
```

The URL itself is source metadata / locator-like material, not a substantive Epistemic Unit. `presumably` is also an unsupported extractor inference while the item is labeled `SOURCE_CLAIM` with HIGH confidence.

Therefore:

```text
Raw locator / URL != Epistemic Unit
Unsupported inference != SOURCE_CLAIM
```

## 6. Mild overlap residual

The extractor also represented `Lauren now allows agents to auto-merge PRs` both inside Event 2 context and as a separate non-event unit.

This is not catastrophic, but it suggests a representation discipline:

```text
Do not duplicate the same semantic payload across EventFrame and EpistemicUnit
unless the non-event representation adds a genuinely distinct methodological/belief-level meaning.
```

## 7. Current status

```text
Temporal anchor plumbing/prompt       PASS / observed residual CLOSED
First-pass structural validity        PASS
Event/Epistemic core split             PRESERVED
Provenance traceability                PASS
Provenance support sufficiency         RESIDUAL OPEN
Raw URL filtering                      RESIDUAL OPEN
Event/Epistemic duplicate suppression  MINOR RESIDUAL OPEN
```

## 8. Next recommended change

Do not reopen temporal semantics.

Before expanding E1 corpus, make one small Sensor prompt/interface-discipline revision that says:

1. every semantic object must be supported by evidence whose actual span is sufficient for that object;
2. add another evidence record when a different paragraph is needed;
3. bare URLs/locators/navigation artifacts are metadata, not Epistemic Units unless the source makes a substantive claim about them;
4. never use `SOURCE_CLAIM` for an extractor-added inference;
5. avoid semantic duplication between an EventFrame and EpistemicUnit.

Then rerun RS02 once more as development regression before moving to RS11/RS05/RS06/RS04.
