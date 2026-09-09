# Phase 8C.8 — Semantic Topology Stability Attribution Result

Status: EXPERIMENTALLY COMPLETE
Date: 2026-09-10

Measurement commit:
`9dbe22dc7871e9f0e071519050d9d4303964ff06`

Canonical artifact:
`eval/live/results/phase8c8_semantic_topology_stability_v0_1/phase8c8_semantic_topology_stability_v0.1_20260909T195553Z.json`

SHA256:
`f1d41669867e8cdddd5d8beb62b65348b24e42facbd783d031844297f60f8216`

## Design

Gate 1A froze audited semantic units and Kernel, then repeated native Locate 6 times. Gate 1B froze one modal Locate realization and repeated native multi-effect Cognitive Impact 6 times. Pareto v0.1 and Magnitude-Free v0.1 remained frozen.

Primary Semantic Topology identity was `(operation,target)`. Raw magnitude never participated in topology identity or Magnitude-Free Attention.

## Main results

| Case | Locate target mode | Impact topology mode | Critical relation recall | Magnitude-Free Attention |
|---|---:|---:|---:|---|
| RS05 | 1.00 | 0.667 | CHALLENGE(CF-B-PERF) 1.00 | ENGAGE 6/6 |
| RS15 | 0.50 | 1.00 | Q2 1.00; B2 1.00 | WATCH 6/6 |
| RS11 | 1.00 | 0.333 | n/a | AWARE 6/6 |
| RS12 | 1.00 | 0.333 | n/a | WATCH 6/6 |
| A | 1.00 | 0.667 | n/a | AWARE 6/6 |
| C | 1.00 | 1.00 | n/a | DROP 6/6 |
| D | 0.833 | 0.833 | n/a | DROP 5/6; ENGAGE 1/6 |
| X | 1.00 | 0.833 | n/a | AWARE 6/6 |

## Attribution

RS05 shows stable core / variable periphery: the critical CHALLENGE edge is present 6/6 despite optional OPEN_NEW and one incidental REINFORCE branch. Product-level Attention remains ENGAGE 6/6.

RS15 separates Locate from Impact. Locate target sets vary (mode rate 0.50; pairwise Jaccard 0.88), but after freezing the modal Locate realization, Cognitive Impact topology is exactly stable 6/6 with simultaneous REINFORCE on B1/B2/BT1/M1/Q1/Q2. Q2 and B2 critical recall are both 1.00; Attention is WATCH 6/6.

RS11 and RS12 have substantial peripheral Cognitive Impact variance under frozen audited semantics and frozen matches, yet Magnitude-Free Attention is invariant 6/6. This empirically supports `Topology variance != Attention variance` for these cases.

C is a clean negative control: empty Locate 6/6, empty topology 6/6, DROP 6/6.

D exposes the only product-level failure. Its modal Locate realization is empty. With that empty Locate frozen, Cognitive Impact is empty 5/6, but one run spontaneously emits five OPEN_NEW effects and raises article Attention to ENGAGE. Because Sensor, Auditor, audited world, Kernel, and Locate are all frozen, this failure is attributed to free-floating OPEN_NEW generation in Cognitive Impact, not upstream perception.

## Decision

Do not open Auditor/Sensor variance yet. Gate 1 has already found a downstream product-level instability with a cleaner causal boundary. Freeze the Phase 8C.8 result and move next to OPEN_NEW jurisdiction/materiality attribution.

Working hypothesis for the next phase:

```text
OPEN_NEW is a new cognitive node, not a free-floating interesting fact.
It should have a user-relative Kernel jurisdiction anchor even though its update target is null.
```

Production default remains `one-delta-v1`. No Pareto/Magnitude-Free promotion is implied by this result.
