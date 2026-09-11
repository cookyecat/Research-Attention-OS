# Phase 10D.6L.4 — Strong-Model Grounding Reference

**Status:** FROZEN BEFORE FLASH GROUNDING
**Date:** 2026-09-12

This reference is a GPT-5.6 Sol manual adjudication of the 28 frozen relation-support instances selected by the 10D.6L.4 preregistration. It is an architecture-capability upper-bound reference, not human Gold.

Class totals:
- `DIRECT`: 11
- `PARTIAL`: 12
- `INSUFFICIENT`: 5
- `CONTRADICTS_OPERATION`: 0

Exact machine-readable labels, frozen support texts, targets, and rationales are stored in `eval/live/phase10d6l4_strong_grounding_reference_v0_1.json`.

## Reference rationale by case

- **D:** all four relations are `INSUFFICIENT`. Astra agentic/coding evidence does not address high-frequency motor control, and absence of motor-control discussion is not evidence for Q1. The AI-safety / recursive-training OPEN_NEW branches may be substantively real, but the frozen Kernel lacks matching jurisdiction; broad G1/P2 attachment is insufficient.
- **X:** all five M1 relations are `DIRECT` because AgentHands explicitly separates backend LLM semantic generation from local timestamped parser/animation execution. The single BT1 relation is `INSUFFICIENT`: a small XR study with missing quantitative metrics does not establish the field-level latency×energy×task-success bottleneck for high-frequency embodied control.
- **N4:** all six M1 relations are `DIRECT`. All six BT1 relations are `PARTIAL`: latency and task/control success are directly measured, but energy is absent. All six Q1 relations are `PARTIAL`: evidence is directly relevant, but B1/M1/BT1 are more precise cognitive landing points.

These labels are frozen before weak-model Grounding runs and must not be edited to improve Flash agreement.