# Phase 10D.6L.4J — OPEN_NEW Jurisdiction Capacity Preregistration

**Status:** PREREGISTERED / NO OUTCOME YET
**Date:** 2026-09-12

## Question

When an `OPEN_NEW` relation and its support evidence are already frozen, can the weak evaluator determine whether the proposed jurisdiction anchors genuinely cover that new cognitive branch when the full anchor semantics are supplied?

This gate isolates jurisdiction admission from relation-support fit. It does not regenerate relations or support bindings.
## Frozen inputs

Use only the two `OPEN_NEW` items already present in the frozen 10D.6L.4 strong reference. Strong labels remain hidden from the weak evaluator.

For each proposed jurisdiction anchor, provide full frozen Kernel semantics: id/code, node type, title and proposition/description. Empty anchor lists are legal and should be preferred when no current Kernel jurisdiction is appropriate.

The evaluator may output only `SUPPORTED_JURISDICTION` or `INSUFFICIENT_JURISDICTION` plus a reason. It may not change relation, support, anchors or Attention.
## Measurement and gate

Run three independent weak-model judgments per frozen `OPEN_NEW` item (`2 × 3 = 6` calls).

Primary metrics: structured success, modal stability, exact agreement with the frozen strong jurisdiction reference, and any `strong insufficient -> weak supported` critical error.

Formal gate is unchanged by outcome: both items must be structurally valid and have stable modal judgments; any critical modal jurisdiction error prevents weak-evaluator promotion. This follow-up is diagnostic and does not authorize production switching.
