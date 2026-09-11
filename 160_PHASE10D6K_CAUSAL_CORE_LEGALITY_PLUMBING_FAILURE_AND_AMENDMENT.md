# Phase 10D.6K — Decision-Causal Core Legality Plumbing Failure and Amendment

**Status:** SECOND PRE-MEASUREMENT TECHNICAL FAILURE RETAINED / AMENDMENT LOCKED  
**Date:** 2026-09-11

## Failure

The amended 10D.6K execution using the new semantic-effect-existence strategy still produced all-DROP. Artifact SHA256: `3661c32c1dd9eb493e74d55e830aa9b84ee8f08e1522c8f4f5d544c19fe26423`. This is not a cognitive outcome.

Attribution found that `Decision-Causal Core` independently prefiltered the normalized assessment through legacy `legal_public_effects()` before calling the supplied decision strategy. Therefore the instrument erased zero-magnitude semantic effects even though the new strategy itself no longer did.

## Amendment

Effect-existence legality must be owned by the decision strategy. Add a strategy-level `legal_effects()` selector and make both `strategy.route()` and `Decision-Causal Core` use that same selector. Existing strategies preserve their historical positive-magnitude legality; the experimental cardinal-free strategy uses semantic relation legality. The causal-core algorithm, ablation unit, Attention projection, directness policy, authority arms, and frozen 10D.6H inputs remain unchanged.

No production default changes. Phase 9A remains paused.
