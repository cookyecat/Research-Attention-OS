# Phase 6C — Human Authorization and Brain/Runtime Boundary Result

Status: **CLOSED / CANONICAL DEVELOPMENT RESULT**
Date: 2026-09-08

## 1. Question

Can a real cognitive change travel from audited source evidence through Δ and Attention Policy into a concrete KernelPatch proposal, while preserving the constitutional rule that AI may propose but may not silently mutate protected cognition?

Canonical path:

```text
Audited source semantics
→ Locate against K_t
→ Δ
→ Attention Policy
→ KERNEL_PATCH proposal
→ Human Accept / Modify / Reject
→ only then K_t → K_{t+1}
```

Phase 6C also exposed a separate Brain/Runtime-state authority bug during integration.## 2. Authorization state machine

The implemented lifecycle is explicitly stateful:

```text
AI Proposal
   ↓
PROPOSED
   ├─ Human REJECT → REJECTED → Kernel unchanged
   ├─ Human ACCEPT → ACCEPTED → KernelVersion(committed_by=USER)
   └─ Human MODIFY → MODIFIED → modified state committed by USER
```

Protected cognition also rejects direct AI writes through the existing guard.

Observed invariants:

```text
PROPOSED does not mutate Kernel
REJECT does not mutate Kernel
ACCEPT is required before mutation
MODIFY commits the human-modified state
KernelVersion records committed_by = USER
```

Therefore the human-authorization boundary is not only policy prose; it is implemented as a guarded state transition.## 3. Real challenge-to-patch path

Using RS05 audited evidence and the development-only counterfactual performance belief:

```text
RS05 audited profiling evidence
→ CHALLENGE(CF-B-PERF)
→ ENGAGE
→ expected_output = KERNEL_PATCH
→ one REVISE PatchDraft
```

The draft proposes changing the Belief status from `ACTIVE` to `CONTESTED` and carries four RS05 evidence pointers.

Post-fix canonical result at Git HEAD `695e39ad1fbbdd2c6b4fcb6468233a86eb5d2604`:

```text
n_patch_drafts = 1
kernel_unchanged_after_proposal = true
attention = ENGAGE
expected_output = KERNEL_PATCH
```

No persisted Kernel mutation occurs during proposal generation.## 4. Brain/Runtime authority bug found by integration

The first Phase 6C run produced a `PREEMPT` reason even though the experiment supplied no trusted state saying the source threatened the user's current work.

Root cause:

```text
caller supplied no threatens_active_work state
→ ModelBackedCognitiveProvider accepted LLM-parsed threatens_active_work
→ Scheduler treated it as authoritative runtime state
→ PREEMPT
```

The Attention Policy was behaving correctly relative to its input. The wrong layer was allowed to manufacture the input.

This is a Brain World Model authority failure:

> **A model inference about the user is not automatically an authoritative user/runtime state.**

Fix: when no trusted caller/runtime signal is provided, `threatens_active_work` is false. Explicit trusted caller input still retains authority.## 5. Canonical engineering rule

```text
Cognitive inference
!=
Runtime-state sensing
```

Or more generally:

> **Before blaming the decision layer, inspect the world it was shown.**

This applies symmetrically to both RAOS world models:

```text
External World Model wrong
→ correct Δ may still be wrong about reality

Brain World Model wrong
→ correct Attention Policy may still be wrong about the user
```

Phase 6C therefore validates both the human-authorization state machine and the need for explicit authority boundaries inside the Brain World Model.