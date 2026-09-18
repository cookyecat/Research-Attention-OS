# RAOS Retrieval & Context Continuity Result

Status: IMPLEMENTED / DOGFOOD READY  
Date: 2026-09-18

## Product problem

Dogfood exposed two small but high-friction UX failures:

1. RAOS had no global way to retrieve an already-observed article from anywhere in User Space.
2. Inbox filter state was ephemeral. Opening a source and returning could lose the user's selected cognition/source filters, query, list depth, and working position.

These are continuity failures rather than cognition failures.

## Frozen product principle

> **Retrieval should preserve context.**

Search is for finding something RAOS has already observed. It must not feel like a new attention judgment. A filter configuration is part of the user's current working context and should survive reading detours.

## Global Search RAOS

A persistent Search RAOS entry now sits below the RAOS brand and above primary navigation. `Cmd/Ctrl+K` opens it from anywhere.

Search uses a dedicated server-side full-text endpoint over preserved Source title, full `content_text`, publisher, and canonical URL. It does not rely on the Source Library compact preview and therefore can find phrases occurring late in an article.
## Inbox continuity

Inbox state is now URL-addressable:

```text
q       search query
state   cognition-state filter
origin  source/publisher filter
n       visible result depth
```

Example:

```text
/inbox?q=GeForce&state=DROP&origin=blogs.nvidia.com&n=54
```

Source links carry this URL as `returnTo`. Reader/Inspector therefore renders a context-aware `Back to Inbox` or `Back to Search results` instead of always returning to Attention.

Inbox also saves scroll position in session storage for the exact filter URL, providing a best-effort return to the same place in a long source list.

The Inbox filter toolbar is sticky so long-list exploration does not require scrolling back to the top to change state or publisher.

## Validation

- frontend typecheck: PASS
- Next.js production build: PASS
- full-text body-only phrase search: PASS
- Inbox URL/filter DOM restoration: PASS
- Reader return context: PASS
- canonical runtime: READY / ATTESTED
- backend regression: 820 passed, 63 skipped, 1 known Case-K failure
