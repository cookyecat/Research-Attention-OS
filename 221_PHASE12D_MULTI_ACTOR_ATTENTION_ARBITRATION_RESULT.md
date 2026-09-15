# Phase 12D — Multi-Actor Attention Arbitration Result

Date: 2026-09-16
Status: **CLOSED / SHARED-RESPONSIBILITY v0.1 VALIDATED**
Parent: `209_PHASE12_PERSONALIZATION_SCALE_PLAN.md`
Preregistration: `220_PHASE12D_MULTI_ACTOR_ATTENTION_ARBITRATION_PREREGISTRATION.md`

## 1. Result

Phase 12D v0.1 closes the first real multi-actor problem without adding a second Attention authority or actor-priority model.

```text
Many Agents
→ many WatchDelegations
→ one canonical Watch
→ one canonical RAOS Attention authority
→ one human
```

The only new persistent state is delegation provenance. `declared_actor_id` is caller-declared provenance, not authentication and not an Attention signal.

## 2. Validated semantics

- Exact normalized `(target_type, target_ref)` agent delegations share one canonical Watch when trigger semantics match.
- Actor count does not change D/S/P, cognitive authority, Attention severity, urgency, or delivery class.
- Cancelling one actor cancels only that delegation.
- An agent-only Watch remains ACTIVE while any delegation remains and is released only after the last delegation is cancelled.
- A core-owned Watch is not cancelled merely because agent delegations disappear.
- Conflicting trigger semantics fail closed rather than broadening observation scope.
- Agent requests cannot directly set `DROP/AWARE/WATCH/ENGAGE`, urgency, importance, or a second scheduler policy.

## 3. Validation

Migration `0012_feedback_attribution -> 0013_watch_delegations` passed on a copy of the dogfood database and was then applied to the actual dogfood database.

Focused Phase-12D tests passed, and the broader Agent/WATCH/Delivery/Attention regression closed at:

```text
165 passed
1 existing Starlette/httpx deprecation warning
```

A versioned localhost dogfood used two distinct declared actors with Active Acquisition disabled. Both delegations resolved to one canonical Watch; cancelling actor A preserved the Watch; cancelling actor B released the final agent-only responsibility. All 11 dogfood checks passed. Artifact:

`eval/live/results/phase12d_multi_actor_dogfood_v0_1/phase12d_multi_actor_dogfood_v0.1_20260915T213406Z.json`

## 4. Occam stop rule

No quota, fairness weight, actor priority, or per-agent Attention budget is introduced. No material real contention has yet been observed. Those mechanisms would add unsupported policy capacity.

Current rule:

```text
shared responsibility problem observed → solved now
resource-contention problem not observed → leave to the flywheel
```

Reopen quota/fairness research only if real usage shows repeated actor contention with material resource or human-attention consequences.

## 5. Conclusion

Phase 12D is CLOSED at shared-responsibility v0.1. The next question is Phase 12E: what isolation boundary is actually required before multi-user/product scale, without prematurely tenantizing the whole schema.
