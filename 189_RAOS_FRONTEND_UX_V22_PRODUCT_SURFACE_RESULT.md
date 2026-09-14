# 189 — RAOS Frontend UX V2.2 Product Surface Result

Date: 2026-09-14
Status: **IMPLEMENTED / DOGFOOD READY**

## 1. Dogfood residual

Real use after the User Space / System Space split exposed three remaining product failures:

1. the local frontend still ran under `next dev`, leaking Next.js Dev Tools into the user surface; its theme/size preferences were easily mistaken for RAOS settings but only affected the framework overlay;
2. Today / Attention were cleaner but still visually flat and ledger-like, with insufficient editorial hierarchy for habitual information browsing;
3. backend naive UTC timestamps were rendered as local timestamps, making fresh crawler arrivals appear eight hours older in Beijing time.

A fourth presentation residual was historical internal smoke Sources appearing beside real user/acquisition content.

## 2. Production dogfood runtime

Frontend dogfood now runs from a clean production build. The safe restart command is:

```text
npm run dogfood:restart
→ stop old :3000 frontend
→ remove .next
→ typecheck + build
→ next start :3000
```

`next dev` is development-only. The persistent Next.js `N` / Dev Tools preferences therefore no longer exist in normal dogfood. Build output must never overwrite `.next` while either `next dev` or `next start` is serving it.

## 3. Real RAOS Preferences

RAOS now owns its own Preferences surface in User Space. Settings are browser-local and apply to the whole product:

```text
Theme      Dark / Light / System
Text size  Compact / Default / Large
```

Preferences are applied before hydration to avoid theme flash. `System` follows the host OS appearance. Font scaling affects normal UI and Reader typography rather than an isolated popup.

## 4. Editorial product surface

Today now follows an attention-first editorial hierarchy rather than equal-weight dashboard cards:

```text
unresolved ENGAGE alert
→ latest relevant lead story
→ compact Brief
→ delegated monitoring
→ Attention pulse
```

Attention defaults to current non-DROP states and uses a newsroom-like lead/secondary-card layout with source excerpts and freshness. Inbox recent Sources are presented as a content library rather than a log list.

Explicit internal smoke fixtures are excluded from User Space editorial/current views while remaining preserved in RAOS System ledgers. Manual user content is not globally hidden.

## 5. Time semantics

Backend naive datetimes are treated as UTC. User-facing time is rendered in:

```text
Asia/Shanghai = UTC+8
```

For example, `2026-09-13 19:43:37` from the backend is displayed as `2026/9/14 03:43` Beijing time, preventing false stale-crawler impressions.

## 6. Boundaries

No backend cognition, D/S/P, Attention policy, Watch semantics, Kernel authority, Acquisition logic, or canonical architecture changed. This remains a presentation/runtime correction driven by dogfood.

## 7. Validation target

The release gate is:

```text
frontend typecheck PASS
production build PASS
production next start on :3000
all User/System routes HTTP 200
Next Dev Tools absent
RAOS Preferences change whole-page theme and text size
CSS / JS chunk URLs referenced by HTML return 200 from the same production build
```

A dogfood regression during finalization reproduced the exact asset-safety failure: an older `next start` remained live while a new build overwrote `.next`, so HTML referenced an old CSS hash while disk contained a new hash and the page rendered as raw HTML. Recovery was to terminate the live server, delete `.next`, rebuild cleanly, then start one production server. `dogfood:restart` encodes this invariant so it does not depend on operator memory.

Browser-level validation confirmed RAOS Preferences affect the whole document: Dark changed the page background to `rgb(13, 17, 23)`, Large changed body text from 15px to 17px, and Light changed the page background to `rgb(244, 246, 248)`.
