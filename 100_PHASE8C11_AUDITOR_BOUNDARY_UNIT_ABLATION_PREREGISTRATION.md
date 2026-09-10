# Phase 8C.11 — Auditor Boundary-Unit Causal Ablation Preregistration

Status: PREREGISTERED / NOT YET MEASURED
Date: 2026-09-10

## Question

Are the specific Auditor admission changes identified in Phase 8C.10 necessary causes of the observed downstream Attention shifts, or were those shifts merely coincident with fresh Cognitive Mapping randomness?

## Frozen source

Use the exact Phase 8C.10 Gate 2A artifact. No Sensor or Auditor calls are made.

## Arms

- RS15: current 8-unit world vs same world minus `RS15-NEU4`.
- RS11: 9-unit minority world vs same world minus `RS11-N1`.
- RS12: current 12-unit world vs same world minus `RS12-N11`.
- RS05 negative propagation control: current modal 6-unit world vs same world minus `RS05-U06` and `RS05-U08`, reconstructing the historical 4-unit core.

The ablation removes semantic units only. It does not rewrite remaining units, evidence packets, Kernel state, prompts, calibration, Pareto, or Attention.

## Downstream

Each arm independently runs Locate ×3 to select a modal localization. Cognitive Impact then runs ×6 with the arm-specific modal Locate frozen. Impact calls are interleaved by arm within each case to reduce temporal drift.

Final stack:

`Anchored OPEN_NEW Admission + Magnitude-Free Calibration + Pareto Multi-Delta + Article Join`.

## Primary outcomes

1. Article Attention distribution and stability;
2. preregistered critical-relation recall where available;
3. topology exact modal rate / Jaccard / entropy using `topology-stability-metrics-v0.1`.

A boundary unit is decision-causal when removing it produces a reproducible Attention/topology shift beyond within-arm Cognitive Mapping variation. Stability is not correctness: causal necessity does not itself prove that the Auditor should reject or admit the unit.
