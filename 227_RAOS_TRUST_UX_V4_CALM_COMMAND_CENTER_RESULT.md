# RAOS Trust UX V4 — Calm Command Center / Causal Legibility

Date: 2026-09-17  
Status: **IMPLEMENTED / DOGFOOD READY**

## 1. Product promise

Trust UX V4 is not a cosmetic redesign. It makes the user-facing product express the actual RAOS operating doctrine.

> **The user should not have to scan the world personally. RAOS should already have observed and judged the incoming world, so the user can understand within seconds why these items surfaced, why the rest did not, and whether anything requires action now.**

```text
用户不必自己扫描世界。
RAOS 已经替他看过、判断过；
用户只需要迅速知道：
为什么是这些、为什么不是那些、现在到底要不要做什么。
```

This complements the frozen doctrine:

```text
Observe broadly.
Understand automatically.
Interrupt sparsely.
```
## 2. The five-second Today contract

Within roughly five seconds, Today should answer four questions without requiring Inspector knowledge:

```text
1. What happened that is worth knowing?
2. Why does it matter to me?
3. Do I need to do anything now?
4. What is RAOS already carrying so I do not have to remember it?
```

If the page answers only the first question, it is still a news dashboard rather than an Attention OS.

Today therefore uses the following user-space hierarchy:

```text
current attention state / caught-up status
→ Needs you / Worth knowing
→ Why this is here
→ source content
→ RAOS is carrying these
→ invisible work summary
```

WATCH is primarily a responsibility-transfer state, so WATCH items should not compete with AWARE/ENGAGE for editorial Hero prominence by default. They belong primarily under **RAOS is carrying these**.
## 3. Trust model

Trust is not produced by making the AI look more confident. The default product surface should provide:

```text
Legibility  — I understand what RAOS did.
Causality   — I understand why RAOS did it.
Agency      — I can inspect and correct it when needed.
```

In shorthand:

```text
Trust = Legibility + Causality + Agency
      = I understand it + I can predict it + I can correct it
```

The emotional target is **calm confidence**, not novelty, urgency, or engagement maximization.

RAOS should feel less like a news homepage competing for attention and more like a calm command center that says:

> **The world is still moving. You do not need to watch all of it yourself.**
## 4. User-space language versus system language

Canonical internal states remain unchanged, but normal User Space no longer requires the user to memorize the RAOS ontology.

```text
Canonical       User Space
ENGAGE          Needs you
WATCH           Being watched
AWARE           Worth knowing
DROP            Filtered
```

The canonical terms remain visible in RAOS Inspector / System surfaces and may appear as technical provenance. This is presentation translation, not semantic renaming.

Permanent rule:

> **The deeper RAOS becomes internally, the simpler its default surface should become.**

The existing User Space / System Space boundary remains authoritative:

```text
USER SPACE       information → meaning → action
RAOS INSPECTOR   cognition → provenance → execution internals
```
## 5. Visual hierarchy follows cognitive hierarchy

The previous Today page allocated the strongest visual weight to hero media and headline, which made the product feel like an editorial news reader. V4 changes the intended priority to:

```text
1. What needs me?
2. Why does it need me?
3. What changed?
4. What is the source?
5. Decorative / editorial media
```

This does not mean images disappear. It means visual weight must follow cognitive importance rather than publisher aesthetics.

The Hero therefore adds an explicit **Why this is here** block grounded in stored decision provenance. Brief items receive compact relevance reasons rather than behaving like an unexplained news sidebar.

No user-facing explanation may invent a causal story. Explanations are projected from stored `decision_cause`, no-Delta awareness evidence, or persisted Kernel matches.
## 6. The WATCH promise

The strongest product language on Today remains:

> **RAOS is carrying these.**
>
> **You do not need to keep them in working memory.**

This expresses a responsibility transfer rather than a saved-items list.

The user-space Watch representation therefore exposes what RAOS is waiting for when the persisted Watch has explicit triggers:

```text
waiting for new evidence
waiting for a paper release
waiting for a code release
waiting for independent replication
```

The psychological promise is simple:

```text
你不用记着，我替你记着。
```

A Watch item without visible responsibility semantics risks being perceived as a bookmark. V4 makes the delegated responsibility legible.
## 7. Making invisible labor visible

RAOS has a product-value paradox:

```text
the better RAOS becomes at filtering,
the less visible work the user sees.
```

A successful Attention OS can therefore look inactive unless it exposes aggregate evidence of the work it absorbed.

Today now uses **Behind the quiet** instead of the internal `Attention pulse / policy budget` presentation. It shows the current Source-judgment residue in human terms:

```text
filtered out
worth knowing
left to watch
need you
```

Long-lived active Watch responsibilities are reported separately because they are a different population from current Source judgments. Trust UX must never make unlike counters look additive.

Permanent rule:

> **Make invisible labor visible without making invisible information visible.**
## 8. Wide-screen layout contract

Real dogfood on a full browser window exposed a global visual defect: dense content occupied the left half of the application while a large accidental void remained on the right. The imbalance made the product feel unfinished and increased local visual pressure.

V4 changes the User Space canvas from a narrow left-anchored region to a centered wide-screen system:

```text
sidebar
+ centered main canvas up to ~1720 px
+ responsive internal columns
+ controlled reading/form widths where long lines would reduce usability
```

The rule is not “stretch everything.” Reader prose, forms, and other line-length-sensitive surfaces remain bounded. Editorial grids, Attention, Watch, and Source Library use the available horizontal field more fully.

> **Wide-screen utilization means balanced composition, not maximum line length.**

This layout rule applies across Today, Inbox, Attention, Watch, Context, and future User Space surfaces.
## 9. Implementation summary

Trust UX V4 changes presentation only. It does not alter cognition, D/S/P, Attention authority, Watch semantics, Kernel authority, Acquisition, Delivery, or Execution Integrity.

Implemented changes include:

```text
Today
- caught-up / needs-you trust status
- optional browser-local "since last visit" summary
- ENGAGE/AWARE editorial surface; WATCH delegated out of the news stream
- grounded Why this is here explanation
- Brief relevance reasons
- RAOS is carrying these + explicit waiting-for triggers
- Behind the quiet invisible-work summary

Global User Space
- centered wide-screen canvas
- human-facing Attention labels
- canonical state retained in Inspector/System
```

The implementation reuses persisted provenance. It does not add a second relevance model or a Trust-specific cognition policy.
## 10. Validation

Validation used the live production dogfood runtime and current data, not a mock UI.

```text
frontend typecheck             PASS
Next.js production build       PASS
backend health                 ok
frontend health                ok
Execution Integrity            READY / ATTESTED
capability mismatches          []
```

Wide-screen Chromium renders were inspected at 2496×1600 for:

```text
Today
Inbox
Attention
Watch
```

The previous left-heavy / right-empty global composition is removed. Today now reads as a calm command center: system state first, causal explanation second, source content third, delegated responsibility and invisible-work evidence below.

A final dogfood audit also caught and corrected one Trust-specific counter bug: current Source judgments and long-lived Watch responsibilities had been mixed into one apparent additive total. V4 keeps those populations explicitly separate.
## 11. Frozen Trust UX principles

```text
Today must answer the four five-second questions.
Visual hierarchy follows cognitive hierarchy.
User Space speaks human language; Inspector preserves canonical language.
WATCH is transferred responsibility, not a bookmark.
Quiet is a feature, but invisible labor must remain legible.
Wide-screen balance must be intentional rather than accidental empty space.
```

Trust UX should continue to evolve from real dogfood residuals. The next major trust work is expected to come from Productization rather than decoration: stronger correction/agency flows, privacy and ownership legibility, Cold Start, and real-user evidence about over- versus under-interruption.

The permanent product test is:

> **Can the user understand in seconds what RAOS did for them, why it did it, and whether they need to act — without learning how RAOS is implemented?**

## 12. V4.1 refinement — continuity, concrete causality, and visual restraint

Dogfood exposed four follow-up Trust residuals and they are now part of the design contract:

```text
Generic causal explanation
→ concrete event change + explicit user context

Any available image becomes a Hero
→ visual-value gate: editorial / evidence / none

Invisible-work proof buried below the fold
→ Behind the quiet directly under You're caught up

Page refresh resets “last visit”
→ visit-session continuity based on last activity
```

The product rule for causal copy is now **causally correct + individually concrete**. A no-Delta AWARE explanation should prefer the actual material change, the user's standing radar, and the closest current context over generic D/S/P prose.
The temporal model is user-continuous rather than calendar-continuous:

```text
user leaves RAOS
→ RAOS keeps observing
→ user returns after a meaningful inactivity gap
→ summarize only what changed since the prior visit
→ You're caught up
```

A refresh or ordinary navigation inside one active session must not move the prior-visit boundary. V4.1 uses a 30-minute inactivity gap for single-user dogfood. Private Paid Beta should move this state from browser-local storage to authenticated user/workspace state so continuity works across devices.

Visual evidence is also separated from decorative editorial media. Social screenshots and evidence-like captures should be preserved faithfully but shown with lower visual dominance; weak screenshots must not become oversized Hero decoration merely because an image exists.

> **The user should feel that RAOS remembers where they left off, not that every page load starts a new day.**

## 13. Inspector refinement — decision composition

Dogfood showed that exposing D, S and P individually is not enough. The user must also be able to see how the frozen Core rule composes them into the final no-Delta disposition.

The Inspector now renders the canonical contract:

```text
AWARE iff S AND (D OR P)
```

When any component is UNKNOWN, the UI enumerates the valid Boolean completions of that unknown state and evaluates the same frozen gate for each completion. The explanation therefore distinguishes **unknown evidence** from **decision-critical unknown evidence**.

Examples:

```text
D=IN,  S=NOT_MATERIAL, P=UNKNOWN
→ P=SALIENT      → DROP
→ P=NOT_SALIENT  → DROP
→ final DROP is logically determined

D=IN,  S=MATERIAL, P=UNKNOWN
→ P=SALIENT      → AWARE
→ P=NOT_SALIENT  → AWARE
→ final AWARE is logically determined
```

The permanent Trust rule is:

> **Inspector should expose not only what each signal says, but which signal is decision-critical and why uncertainty can or cannot change the outcome.**
