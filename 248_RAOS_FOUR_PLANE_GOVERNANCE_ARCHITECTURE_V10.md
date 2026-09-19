# RAOS Four-Plane Governance Architecture V1.0

Status: **FROZEN NAMING / DOGFOOD ALIGNED**  
Date: 2026-09-19

## 1. Canonical naming

RAOS governance and inference are organized into four distinct planes.

### Epistemic Plane

```text
Semantic Evidence Auditor
        ↓
Audited Evidence
        ↓
Representation Auditor
        ↓
Probabilistic Epistemic World Representation
```

Responsibilities:

- determine what a Source supports;
- infer cross-source / source-event / event-event hypotheses;
- preserve support, conflict and uncertainty;
- maintain revisable epistemic belief.

It does not own topology side effects or runtime authorization.

### Decision / Commitment Plane

```text
Epistemic / cognitive state
        ↓
Attention decision
and/or
Topology Commitment Policy
```

Responsibilities:

- decide what action is warranted under uncertainty;
- keep topology commitment separate from belief admission;
- use asymmetric loss rather than truth-certification language.

The E1 gate is a **Topology Commitment Gate**, not a world-truth certification gate.

### Agent / Control Plane

```text
Agent API / CLI / future MCP-A2A
        ↓
observe / explain / orchestrate / delegate / propose
```

Responsibilities:

- invoke existing canonical capabilities;
- coordinate workflows;
- carry actor/delegation provenance;
- propose or request actions through canonical paths.

Permanent prohibitions:

```text
no independent epistemic truth
no independent Attention authority
no direct topology authority
no direct Kernel authority
no direct Delivery authority
no bypass of Phase13
```

### Integrity Plane

```text
Phase13 Execution Integrity
```

Responsibilities:

- identify the runtime;
- attest contract/build/profile identity;
- determine canonical side-effect permission;
- fail closed for unauthorized mutation.

It is orthogonal to epistemic truth.

```text
Execution Authority != Epistemic Belief
```

## 2. Complete architecture

```text
                         LATENT WORLD X_t
                               │
                               ↓
                        Observed Evidence
                            E_{<=t}
                               │
                               ↓
                    ┌─────────────────────┐
                    │   Epistemic Plane   │
                    │                     │
                    │ Semantic Auditor    │
                    │       ↓             │
                    │ Audited Evidence    │
                    │       ↓             │
                    │ Representation      │
                    │ Auditor             │
                    │       ↓             │
                    │ P(R | E_{<=t})      │
                    └─────────┬───────────┘
                              │
                              ↓
                    Cognitive stochasticity
                    P(T,A | R,K,Theta)
                              │
                              ↓
                    ┌─────────────────────┐
                    │ Decision /          │
                    │ Commitment Plane    │
                    │                     │
                    │ Attention policy    │
                    │ Topology policy     │
                    └─────────┬───────────┘
                              │
                       canonical side effect
                              │
              ┌───────────────┴────────────────┐
              │                                │
              │ Phase13 Integrity Plane        │
              │ gates every canonical write    │
              │                                │
              └────────────────────────────────┘

        Agent / Control Plane is orthogonal orchestration:
        it may invoke the above paths but may not bypass them.
```

## 3. Functional planes remain distinct

This governance decomposition does not remove functional boundaries such as:

```text
Acquisition Plane
Delivery Plane
Presentation Plane
```

Those describe *what work is done*.

The four-plane model describes *where epistemic inference, decisions, orchestration and mutation legitimacy live*.

## 4. Agent / Integrity alignment fix

Review of `agent-interface-v0.2` found that direct Agent WATCH creation/cancellation and direct WATCH API mutations could write canonical WATCH state without an explicit Phase13 side-effect gate.

This violated the new Integrity Plane invariant.

A single helper now enforces:

```text
require_side_effects_authorized()
```

for direct WATCH mutation entry points.

Covered paths:

```text
POST /agent/v1/watch
POST /agent/v1/watch/{id}/cancel
POST /watches
POST /watches/{id}/active-acquisition
POST /watches/{id}/triggers/{trigger_id}/fire
```

Read-only Agent/WATCH endpoints remain ungated by side-effect authority.

`analyze` continues to enter the canonical cognition pipeline, which already applies Phase13 internally.

## 5. Agent interface contract

Agent interface is now:

```text
agent-interface-v0.3
```

Capabilities explicitly declare:

```text
agent_plane_role = orchestration_control_only
canonical_write_integrity = phase13_required
agent_may_bypass_integrity = false
agent_interface_may_assign_attention = false
```

## 6. Regression

Focused Agent + Phase13 suite:

```text
19 passed
```

Tests include:

- ordinary WATCH mutation fails without side-effect authority;
- Agent WATCH creation fails without side-effect authority;
- Agent cannot cancel an existing WATCH after execution purpose becomes REPLAY;
- existing read/orchestration semantics remain intact.

## 7. Frozen terminology

Use these names going forward:

```text
Epistemic Plane
  Semantic Evidence Auditor
  Representation Auditor
  Probabilistic Epistemic World Representation

Decision / Commitment Plane
  Attention Policy
  Topology Commitment Policy

Agent / Control Plane
  orchestration / delegation / proposal

Integrity Plane
  Phase13 Execution Integrity
```

Avoid describing Phase13 as a third epistemic auditor.

Avoid describing E1 as world-truth authority.

## 8. Core invariant

```text
connect mathematically
separate responsibilities
gate side effects orthogonally
```

or:

> **Composable, but not conflated.**


## 9. Final dogfood validation

Final backend regression after the Integrity/Agent alignment change:

896 passed / 63 skipped / 1 known Case-K failure.

The only failure remains the pre-existing PREEMPT expected vs PRIORITY actual residual.

After restart, runtime doctor reports CANONICAL / ATTESTED / READY with no mismatches. Live Agent capabilities report agent-interface-v0.3, orchestration_control_only, canonical_write_integrity=phase13_required, agent_may_bypass_integrity=false, and agent_interface_may_assign_attention=false.


## 10. Observation persistence vs authority-bearing side effects

The Integrity Plane does not mean that every database write requires Attention/side-effect authority. Append-only observation and analysis evidence must remain available in degraded or forensic operation when their own contract allows it.

Phase13 side-effect gating applies to authority-bearing mutations such as materialized Event topology, manual decision-relevant SourceGraph mutation, Attention, WATCH, Kernel mutation, and Delivery mutation.

A Phase14A review found and fixed one important contamination path: REPLAY/FORENSIC analysis could previously create Event/EventSource working topology before Attention authority was checked. Forensic cognition now persists analysis evidence without materializing Event topology.
