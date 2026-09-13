# 187 — RAOS Frontend UX V2 Result

Date: 2026-09-14
Status: **IMPLEMENTED / DOGFOOD READY**

## 1. Motivation

Real developer dogfood showed that RAOS cognition was often useful while the frontend remained difficult to use. The old UI optimized for internal-state visibility rather than human attention: AnalysisRun metadata, raw cognitive terminology, watch records, and extracted claims dominated the default presentation.

The product-level failure was:

```text
RAOS backend reduces cognitive load
but
RAOS frontend gives internal cognitive work back to the user
```

UX V2 therefore adopts one presentation rule:

```text
Human action first
→ cognitive explanation
→ evidence
→ technical trace
```

This is a presentation/interaction change only. No cognition, D/S/P, Attention, WATCH, Kernel authority, Acquisition, or backend API semantics were changed.
## 2. Global interaction model

The visual system was replaced with a high-scan-density research cockpit: modern sans typography, stronger contrast, semantic status rails, consistent spacing, active navigation state, wider desktop layouts, and responsive collapse for smaller screens.

The five primary user surfaces are now:

```text
Today      what needs me now
Inbox      give RAOS information
Attention my filtered world
Watch      what RAOS is remembering for me
Kernel     my durable cognitive state
```

Developer-oriented state remains available, but is visually subordinate and usually collapsed.

## 3. Today

Home is now an action surface rather than a metrics dashboard. It leads with focused-attention work, exposes delegated WATCH responsibility, and reframes discarded information as attention saved.

A final dogfood consistency fix removed ledger-derived summary counts from the user surface: Today now counts current de-duplicated Source states and distinct active WATCH responsibilities, matching Attention and Watch rather than `/meta/home` historical/raw-plan totals. In the live checkpoint this changed the misleading `11 watches / 363 min` presentation to `7 distinct monitoring responsibilities / 42 min across current Source states`. The underlying backend ledger is unchanged.

## 4. Inbox

The old input-type select form is replaced by explicit URL / Text / PDF / Observation entry modes. Recent Sources are shown below the composer so the user can recover recent work without navigating through internal ledgers.
## 5. Attention

Attention is now the primary filtered-world workbench. Current source states can be searched and filtered by ENGAGE / WATCH / AWARE / DROP. Cards emphasize the source title, current disposition, human-readable meaning, cognitive operation, provenance, and attention budget rather than Pareto/debug language.

The detail view now follows this order:

```text
Decision
→ why RAOS surfaced this
→ cognitive impact
→ Kernel relevance
→ human judgment
→ evidence / technical trace
```

For no-Delta awareness, the D/S/P explanation is surfaced directly. The real The Verge dogfood case now renders `D=IN`, `S=MATERIAL`, `P=UNKNOWN` as a comprehensible explanation for `AWARE` while preserving full estimator reasoning behind disclosure controls.

AnalysisRun versions, extracted claims/observations/inferences, and other pipeline internals remain inspectable under Technical trace instead of dominating the default view.

## 6. Human authority boundary

The previous generic `Confirm` action could be confused with committing a Kernel change. Feedback is now labelled `Judgment looks right` / `Correct RAOS`, with explicit language that this evaluates the frozen analysis only and never commits cognition.

KernelPatch authorization remains a separate surface with `Authorize change`, `Modify`, and `Reject`, preserving the constitutional boundary:

```text
AI judgment != human-committed cognition
```
## 7. Kernel

Kernel is now presented as a searchable cognitive workspace with compact summary counts, grouped cognitive object types, and a dedicated authorization area for pending proposals. This keeps durable cognition legible without turning the page into a raw database browser.

## 8. Watch

Raw WATCH rows are grouped by monitoring target so repeated records no longer look like duplicate obligations. The page communicates that RAOS owns the next check, shows current monitoring state and trigger history, and hides `Simulate trigger` under Technical / developer controls.

This changes presentation only; persisted WATCH records and trigger semantics remain untouched.

## 9. Validation

Validation on the live Mac dogfood environment:

```text
npm run typecheck      PASS
npm run build          PASS, zero warnings after CSS compatibility cleanup
GET /                  200
GET /inbox             200
GET /attention         200
GET /kernel            200
GET /watch             200
```

All main surfaces were also visually inspected in a real Chromium render against the running backend. The production build was run only after stopping `next dev`, preserving the known `.next` hydration safety invariant.
## 10. Architecture status and next dogfood

`RAOS_CANONICAL_ARCHITECTURE.md` is unchanged because UX V2 does not alter module inventory, authority, main dataflow, execution identity, or research↔dogfood semantics.

`README.md` is updated because it is the current product/run entry point and must describe the user-facing surfaces accurately.

Known follow-up remains dogfood-driven rather than speculative. In particular, historical dev/smoke Sources are still mixed with live dogfood Sources in Attention. UX V2 makes the feed usable but deliberately does not delete provenance or invent a lifecycle taxonomy without evidence.

Next rule remains:

```text
Use the system
→ capture the first real UX or decision residual
→ attribute it
→ make the smallest justified correction
```
