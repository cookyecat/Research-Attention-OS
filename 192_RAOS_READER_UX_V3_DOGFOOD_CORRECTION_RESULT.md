# RAOS Reader UX V3 — Dogfood Correction Result

Date: 2026-09-14
Status: **CLOSED / DOGFOOD READY**

## Residual

First hands-on testing of Reader UX V3 exposed two presentation-only failures. Audited evidence mapping was technically correct but visually over-complete: the short OpenAI/RubyGems article rendered 11 anchors and appeared almost fully underlined. Preferences also lived inside the sticky Sidebar stacking context, allowing the sticky Reader rail to cross the modal surface.

## Correction

Evidence anchoring now treats emphasis as a scarce resource. The Reader selects a deterministic, spatially distributed subset: no more than one anchor per selected paragraph, with the article-level count growing slowly with length and capped at five. The five-paragraph OpenAI/RubyGems article now renders two anchors instead of eleven. No Claim/Auditor output is changed.

Preferences now renders with a React portal under `document.body`, uses an isolated top-level backdrop, locks background scrolling, and constrains panel height with internal scrolling. This removes the Sidebar stacking-context leak rather than masking it with local z-index escalation.

## Validation

Clean production build and browser validation passed. OpenAI/RubyGems rendered exactly 2 evidence anchors. Preferences validation observed `portalParent=true`, backdrop `z-index=10000`, `bodyOverflow=hidden`, and hit-testing over the Reader rail returned the Preferences backdrop rather than an underlying rail card.

No cognition, D/S/P, Attention, Claim/Auditor semantics, Kernel authority, or Source content changed.
