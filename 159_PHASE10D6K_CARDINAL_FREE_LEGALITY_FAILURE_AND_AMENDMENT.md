# Phase 10D.6K — Cardinal-Free Legality Failure and Amendment

**Status:** PRE-MEASUREMENT TECHNICAL FAILURE RETAINED / AMENDMENT LOCKED  
**Date:** 2026-09-11

## Failure

The first 10D.6K execution at measurement SHA `2053ad0` produced DROP 6/6 for every A/D/X/N4 arm. Artifact SHA256: `bed036e39041f296c0b1b88234daa910f9de65021f6c60191e4a26a363072bbf`. This is not a cognitive outcome.

Attribution found that the cardinal-free compatibility projection correctly set `change_magnitude=0.0`, but the shared pre-Pareto `legal_public_effects()` contract still requires `float(change_magnitude) > 0`. Thus Magnitude-Free v0.1 is magnitude-free for ranking/channel decisions but still retains a raw-magnitude dependency for effect existence admission. `normalize_frozen_transition()` can restore frozen target node types, so missing target type is not the principal all-DROP cause.

## Amendment

Do not inject an arbitrary positive sentinel magnitude. Preserve the deployed/history-compatible Magnitude-Free v0.1 strategy unchanged. Add a separately versioned experimental cardinal-free strategy whose legality stage admits a semantic effect based on operation/target legality alone, without reading `change_magnitude`. It must reuse the same Anchored OPEN_NEW admission, Magnitude-Free ordinal decision vector/channel plan, Pareto frontier, article-level join, and runtime overlay.

The valid 10D.6K rerun may change only this effect-existence seam plus the already-intended cardinal-free compatibility plumbing. Directness policy, provenance policy, authority arms, frozen 10D.6H input, sampling, and all Attention rules remain unchanged.

Production defaults remain unchanged. Phase 9A remains paused.
