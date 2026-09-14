# RAOS Frontend Design Principles

Status: **LIVING DESIGN CONTRACT**
Scope: User Space, Reader, Attention presentation, and explicit RAOS Inspector/System surfaces.

## 1. Core product principle

RAOS is an attention operating system, not a visualization of its own internals.

```text
Show the user their world.
Show the operating system only when they ask to inspect it.
```

Therefore:

```math
User\ Space \neq Operating\ System\ View
```

Normal UI optimizes for comprehension, attention allocation, reading comfort, and action. Scheduler state, cognition traces, D/S/P internals, raw claims, model provenance, and execution diagnostics belong in explicit Inspector/System surfaces.

## 2. Reader is attentional recomposition

The RAOS Reader is **not a mirror of the source webpage**. It is a reading space that re-composes the source's attentional structure.

```math
\boxed{RAOS\ Reader = Attentional\ Recomposition(Source)}
```

The source publisher optimizes for publishing, brand, engagement, advertising, navigation, and social distribution. RAOS optimizes for:

```math
\boxed{Comprehension + Attention + Cognitive\ Relevance}
```

## 3. Source fidelity is not layout fidelity

RAOS must preserve source truth and provenance without copying source layout.

Preserve faithfully:

- original text and quotations;
- title, author, publisher, URL, publication time;
- publisher-declared hero image, useful article visuals, captions, and alt text;
- provenance and links back to the original source.

Do not reproduce by default:

- publisher navigation and branding chrome;
- advertisements and sponsor modules;
- related-story widgets, comments, social/share controls;
- engagement mechanics and arbitrary DOM/layout structure.

```math
\boxed{Source\ Fidelity \neq Layout\ Fidelity}
```

Presentation metadata must remain presentation-only unless a separate research decision explicitly promotes it into cognition.

## 4. Visual structure is part of cognition ergonomics

A visual does not need to add new propositional facts to be valuable. Images, whitespace, typography, hierarchy, and rhythm can reduce visual fatigue and give the eye stable anchors.

A useful working model is:

```math
\boxed{Visual\ Value = Semantic\ Information + Attentional\ Structure + Reading\ Rhythm}
```

Implications:

- use publisher-declared hero visuals when available;
- preserve semantic article figures and diagrams conservatively;
- do not inject unrelated decorative images that could imply false source semantics;
- allow text-native sources to remain text-native rather than forcing fake covers;
- use hierarchy, spacing, and asymmetry to make importance visually legible.

A page itself is an attention-allocation problem. Title, image, RAOS guidance, evidence anchors, body text, and side rail all compete for visual priority and must be deliberately scheduled.

## 5. Human action first, internals last

Default presentation order:

```text
information / source
→ why it matters
→ what to do
→ evidence and reading support
→ technical trace only on request
```

This is the frontend analogue of RAOS's core mission: reduce the amount of cognitive work returned to the human.

## 6. Evidence should return to the source text

When RAOS has already extracted and audited claims, the Reader should map those results back to the original source where possible.

Evidence anchors must obey:

```text
frozen cognition result
→ presentation-only source-span alignment
→ subtle original-text anchor
```

Do not create new claims merely to make the UI richer. Underlines/highlights should be traceable to existing evidence spans. Clicking an anchor may reveal a concise human-readable explanation; raw claim schema remains in Inspector.

Evidence emphasis is itself a scarce attention resource. If everything is emphasized, nothing is emphasized. Reader anchors therefore remain sparse, deterministic, and spatially distributed: at most one anchor per selected paragraph and only a small bounded set across an article.

## 7. The reading companion should be context-sensitive

The side rail should not permanently occupy attention with static cards.

Before reading, it may answer:

- Why does this matter to me?
- What should I do?

During reading, it should shift toward:

- reading progress;
- evidence near the current paragraph;
- locally relevant RAOS guidance.

The interface should adapt to the reader's current task rather than repeat the same system message throughout the article.

## 8. Reading aids are presentation, not cognition

Text-size controls, theme, line-height, and optional half-bold/bionic reading are ergonomic transforms only.

They must not mutate:

- Source text;
- copied/searchable text;
- semantic extraction inputs;
- claims, Auditor results, Attention decisions, or Kernel state.

Defaults should remain conservative and optional. Accessibility and user preference outrank novelty.

## 9. Authority and provenance remain visible at the right depth

User Space may simplify language, but it must never fabricate provenance or imply that RAOS authored source content. Original-source links and attribution remain available. Human-committed cognition must remain visually distinct from AI judgment or proposed changes.

## 10. Dogfood rule

Frontend evolution should be residual-driven:

```text
real use
→ observe reading/interaction friction
→ identify earliest presentation cause
→ minimal correction
→ production-browser validation
```

Avoid speculative feature accumulation. Every added visual or interaction should reduce attention cost, improve comprehension, or make authority/provenance clearer.
