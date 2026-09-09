# Phase 8C.9 — Anchored OPEN_NEW Admission Result

Status: EXPERIMENTALLY COMPLETE
Date: 2026-09-10

Implementation commit:
`caca4b6c54a033ca008371cb7fdc3676cef93622`

Measurement commit:
`f7d6c0aea43932802fc4b10674592b508faacba0`

Canonical artifact:
`eval/live/results/phase8c9_anchored_open_new_admission_v0_1/phase8c9_anchored_open_new_admission_v0.1_20260909T200448Z.json`

SHA256:
`01e74482a1883b234f9446efd2cfd7ce6af2d23930c09a303460c5a58ade8efe`

## Candidate

`anchored-open-new-v0.1` is a deterministic Effect Admission chip. It does not use raw magnitude and does not alter targeted REINFORCE or CHALLENGE effects.

OPEN_NEW is admitted only if Locate exposes a user-relative Kernel jurisdiction anchor: GOAL/PROJECT, or STRUCTURAL/DECISION/BOTTLENECK/EVIDENCE relevance, or a structural match.

## Frozen Phase 8C.8 replay

The exact 48 valid Phase 8C.8 Impact outputs were replayed through baseline Magnitude-Free Pareto and the anchored candidate.

- RS05: ENGAGE 6/6 -> ENGAGE 6/6. Four runs contained OPEN_NEW; project/structural/evidence anchors preserve them. Critical CHALLENGE is untouched.
- RS15: WATCH 6/6 -> WATCH 6/6.
- RS11: AWARE 6/6 -> AWARE 6/6.
- RS12: WATCH 6/6 -> WATCH 6/6.
- A: AWARE 6/6 -> AWARE 6/6.
- C: DROP 6/6 -> DROP 6/6.
- X: AWARE 6/6 -> AWARE 6/6.
- D: baseline DROP 5/6 + ENGAGE 1/6 -> candidate DROP 6/6. The only changed repeat is the previously observed free-floating OPEN_NEW burst.

Thus the candidate removes the observed D product-level failure with zero article-level collateral change across the other seven cases.

## Fresh D empty-Locate stress

Twelve additional Cognitive Impact repeats were run with the exact frozen D audited world and exact empty modal Locate.

All 12 happened to emit no OPEN_NEW burst; both baseline and candidate remained DROP 12/12. This is a no-regression stress result, not additional evidence that the historical burst is reproducible at a fixed frequency.

## Regression

Full backend suite after implementation:

```text
581 passed
63 skipped
1 failed
```

The sole failure is the pre-existing Case K residual (`PREEMPT` expected, `PRIORITY` actual). No new regression was observed.

## Interpretation

The strongest evidence is the frozen counterfactual replay: the real observed failure disappears exactly when free-floating OPEN_NEW loses admission authority, while anchored positives and all targeted effects are preserved.

This supports the structural statement:

```text
OPEN_NEW is a new user-relative cognitive branch, not merely an interesting new fact.
OPEN_NEW may have target=null, but should not have jurisdiction=null.
```

The v0.1 anchor invariant is necessary-looking but not yet proven sufficient. It does not verify branch novelty, source grounding, or redundancy once an anchor exists. Those remain later admission questions if anchored false positives appear.

Production default remains `one-delta-v1`; no experimental strategy is promoted by this phase.
