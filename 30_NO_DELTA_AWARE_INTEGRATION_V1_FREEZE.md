# no-Delta AWARE Integration v1 — Freeze

Status: **FROZEN — FRESH END-TO-END ATTRIBUTION NEXT**  
Date: 2026-09-07  
Policy: `AWARE iff S AND (D OR P)`

## Frozen identity

```text
integration_version  no-delta-awareness-integration-v1
policy_gate_version  aware-iff-s-and-d-or-p-v1
```

Implementation:

```text
eval/live/no_delta_awareness_integration_v1.py
```

Implementation commit:

```text
5a9f040ebdf6d227a546483916d7cbfc78e66c7c
```

Truth-table tests:

```text
backend/tests/eval/test_no_delta_awareness_integration_v1.py
```

Test commit:

```text
306e36645306f614871abceec7c2ae35f577c6a0
```

GitHub Actions:

```text
run 34055454442
conclusion SUCCESS
```

## Frozen mapping

```text
D = IN          -> AwarenessSignals.domain_fit = true
D = OUT         -> AwarenessSignals.domain_fit = false

S = MATERIAL    -> AwarenessSignals.event_significance = true
S = NOT_MATERIAL-> AwarenessSignals.event_significance = false

P = SALIENT     -> AwarenessSignals.attention_momentum = true
P = NOT_SALIENT -> AwarenessSignals.attention_momentum = false
```

No semantic claim is attached to the historical slot names beyond this adapter. The canonical meanings remain D/S/P.

## Layer-A result

All eight Boolean rows were run through the real production Scheduler with `Delta=NONE`:

```text
D   S             P              expected
OUT NOT_MATERIAL  NOT_SALIENT    DROP
OUT NOT_MATERIAL  SALIENT        DROP
IN  NOT_MATERIAL  NOT_SALIENT    DROP
IN  NOT_MATERIAL  SALIENT        DROP
OUT MATERIAL      NOT_SALIENT    DROP
OUT MATERIAL      SALIENT        AWARE
IN  MATERIAL      NOT_SALIENT    AWARE
IN  MATERIAL      SALIENT        AWARE
```

Observed wiring result:

```text
truth-table rows       8/8 match
wiring mismatches      0
non DROP/AWARE output  0
```

This is a composition/wiring test only, not estimator generalization evidence.

## Fail-closed integration behavior

The integration harness does not emit a final disposition if any required component is non-scorable.

In particular:

```text
P insufficient_evidence != P NOT_SALIENT
D/S/P technical failure  != false
```

Component failures remain visible for attribution.

## Change policy

From this freeze forward, do not change:

```text
D/S/P -> AwarenessSignals mapping
Boolean gate
Delta=NONE composition semantics
integration harness behavior
```

merely to improve the forthcoming fresh integrated result.

If a fresh end-to-end error appears, attribute it to D, S, P, evidence/sensor input, Human policy boundary, or wiring before changing any component.

## Next

```text
integration harness FROZEN
        ↓
author fresh integrated cases
        ↓
Human D/S/P + AWARE/DROP Gold
        ↓
first end-to-end attribution run
```
