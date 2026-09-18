# RAOS Explicit Reference Provenance V0.1 — Result

Status: **DOGFOOD READY**  
Date: 2026-09-19

## 1. Scope

This slice continues the frozen world-state-centric architecture after World Representation Snapshot V0.1.

It activates the existing provenance path:

```text
Connector
→ reference_candidates
→ ParserRun.references
→ resolve_references()
→ SourceGraph CITES
```

without changing Multi-Delta, Pareto, D/S/P, Attention semantics, or Event authority.

## 2. Frozen authority semantics

An explicit article hyperlink proves only:

```text
Source A explicitly links Source B
→ CITES(A, B)
```

It does **not** automatically prove:

```text
SAME_EVENT
DERIVED_FROM
INDEPENDENT_REPORT
ORIGINAL_SOURCE
```

Those stronger relations remain Representation-Auditor responsibilities.

Transport wrappers are not provenance. Known Wechat2RSS link-proxy URLs are unwrapped to the publisher target before identity comparison, so a transport-generated self-link cannot become a CITES fact.

## 3. Append-only historical hydration

Historical Sources are not rewritten when a newer extractor discovers references.

```text
Historical Source
├─ old ParserRun
└─ new reference-extractor-explicit-links ParserRun
        ↓
aggregate ParserRun.references
        ↓
deduplicate
        ↓
resolve_references()
```

For the real WeChat hydration used here, current extraction was allowed only because the newly fetched canonical `content_text` exactly matched the frozen historical Source text.

Ordinary web hyperlinks resolve to `URL` stubs. DOI/arXiv/bibliographic-only references remain `PAPER` stubs.

## 4. Landscape / Reader projection

`GET /sources/{source_id}/landscape` now exposes:

```text
references
provenance
```

alongside Coverage and Related.

Reader shows an explicit **References** group inside World context. The UI states that CITES is literal-link provenance only and does not imply original-source, derivation, independence, or same-event authority.

Coverage, Related, and References remain projections over the same SourceGraph/Event fact layer rather than separate truth stores.

## 5. Representation digest semantics

Under `decision-representation-v0.1`:

```text
CITES
→ graph_digest
→ audit / reconstruction / Reader context

CITES
↛ decision_representation_digest
```

A regression test now freezes this invariant.

The current decision digest continues to contain only relations already authorized by the present Core contract plus collective-attention evidence packets consumed by no-Delta D/S/P.

## 6. Real dogfood hydration

Historical Source:

```text
新智元
“Claude狂写80%代码，差点干崩Anthropic！CI半年暴涨25倍”
Source id: b6ea6cd2-6120-4853-b25c-10965b22fdbe
```

The recorded Wechat2RSS discovery transport was re-fetched.

Safety gate:

```text
historical content_text length  = 2275
fresh extracted text length     = 2275
exact equality                  = TRUE
```

The new extractor recovered exactly two substantive explicit references:

```text
X:
https://x.com/addyosmani/status/2099577600159158765?s=20

Anthropic:
https://claude.com/blog/agentic-coding-is-straining-ci-heres-how-we-scaled-test-impact-analysis-at-anthropic
```

A third transport-generated “跳转微信打开” link was detected during dry-run and fixed before hydration by unwrapping transport proxy targets and filtering the resulting self-link.

A new append-only ParserRun was created:

```text
parser_name    reference-extractor-explicit-links
parser_version v1
ParserRun id   e017f0d4-37a7-44d1-87e6-ba11fbf78be3
```

Both references resolved to `URL / REFERENCE_STUB` Sources and persisted as `CITES`.

## 7. Digest evidence

Before hydration:

```text
graph_digest
b8f37582cfd2d00327dc3a6c436bb8459a27eb23acfcc2f3de0f9be05fc824c7

decision_representation_digest
d25b11b0d599c159c97eda753307f2f6930bc3c839425a24c312668bebbc43c5
```

After hydration:

```text
graph_digest
a03fb7a8813db477c43592c43b847412b87409d9ee214e56a4d1dd9c0ea0ad63

decision_representation_digest
d25b11b0d599c159c97eda753307f2f6930bc3c839425a24c312668bebbc43c5
```

Therefore:

```text
graph changed     TRUE
decision unchanged TRUE
```

This is the intended behavior.

## 8. Validation

Focused provenance + Landscape + Representation regression:

```text
16 passed
```

Frontend:

```text
TypeScript typecheck PASS
Next.js production build PASS
```

Full backend regression from repository root:

```text
855 passed
63 skipped
1 failed
```

The only failure is the pre-existing Case-K urgency residual:

```text
expected PREEMPT
actual   PRIORITY
```

No new provenance, Representation, D/S/P, cognition, or Phase 13 regression was introduced.

## 9. Next gate

The strongest literal provenance path is now operational.

Next Representation work should proceed to:

```text
explicit CITES facts
→ Representation Auditor
→ bounded stronger provenance-role adjudication
→ shadow SAME_EVENT adjudication
→ high-precision authority gate
```

Do not promote CITES directly into DERIVED_FROM, ORIGINAL_SOURCE, SAME_EVENT, or P evidence.
