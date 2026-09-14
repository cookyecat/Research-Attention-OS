# 188 — RAOS User Space / System Space Split Result

Date: 2026-09-14
Status: **IMPLEMENTED / DOGFOOD READY**

## 1. Dogfood residual

Frontend UX V2 made RAOS substantially easier to scan, but real use exposed a deeper product-layer error: opening an Attention item still led primarily to RAOS's structured interpretation rather than the information the user wanted to consume. The preserved article body existed in `Source.content_text`, but the UI showed AnalysisRun/Attention/DSP/Kernel/evidence structures instead.

The residual was architectural at the presentation layer:

```text
Operating-system state was still being used as the user interface.
```

An attention operating system should behave like other operating systems: scheduling and execution state must remain inspectable, but must not dominate ordinary user interaction.

## 2. Frozen presentation boundary

The frontend now uses two explicit spaces:

```text
USER SPACE
information -> meaning -> action

RAOS SYSTEM / INSPECTOR
scheduling -> cognition -> provenance -> execution
```

This is a presentation boundary only. No backend API contract, cognition semantics, D/S/P definition, Attention authority, WATCH semantics, Kernel authority, Acquisition behavior, or execution identity changed.

## 3. Source Reader

Opening an Attention Source now defaults to **Reader**, not analysis internals.

Reader shows:

- source title, author, origin, published/ingested time, and estimated reading time;
- preserved `Source.content_text` as the main visual object;
- direct link to the original Source when available;
- one compact Attention disposition note;
- plain-language `Why it matters to you` and `What to do` guidance;
- closest current user context when useful.

Source-title suffixes such as `| The Verge` are removed in Reader when origin is already displayed separately.

## 4. Per-Source RAOS Inspector

Each Source has an explicit **RAOS Inspector** tab. It contains the operating-system representation previously exposed by default:

- Attention disposition / budget / urgency;
- no-Delta D/S/P states and estimator reasoning;
- cognitive delta / operation;
- Kernel mapping;
- human judgment feedback;
- proposed Kernel changes;
- AnalysisRun versions and execution provenance;
- extracted claims / observations / inferences.

Inspector can be deep-linked with `?view=system`.

## 5. User-space cleanup

The same boundary was applied beyond Source detail:

- Attention cards no longer expose `REINFORCE/CHALLENGE/OPEN_NEW` by default.
- Watch no longer exposes raw `KERNEL`, trigger enum names, or duplicate-record counts in normal view; these remain under `RAOS Inspector`.
- `/kernel` is presented to users as **Context**: projects, questions, beliefs, models, and constraints. Kernel type/status/version/IDs remain inspectable but subordinate.
- persistent `Dogfood live / Research-aligned cognition` runtime state was removed from the user sidebar.

## 6. Global RAOS System view

A dedicated `/system` route now acts as the explicit operating-system surface. It shows real data from existing APIs, including:

- persisted Source count;
- current source Attention-state count;
- raw Watch ledger and grouped responsibility count;
- Kernel object inventory;
- latest available AnalysisRun contract;
- pipeline/provider/model/fallback state;
- latency and token provenance;
- deep link into the corresponding Source Inspector.

The left navigation is explicitly labelled **USER SPACE**; the separate `RAOS System — Inspect internals` entry sits outside the normal user navigation.

## 7. Visual language

Reader and Inspector intentionally use different visual grammars.

Reader uses long-form typography, a wide reading column, restrained RAOS annotations, and a small contextual rail. Inspector uses the existing research-cockpit cards, state badges, diagnostic grids, and technical disclosure controls.

This visual distinction makes the current mode legible without requiring users to understand RAOS architecture.

## 8. Validation

The implementation was exercised against the live Mac dogfood backend with real acquired Source content. The The Verge source `OpenAI’s rogue AI tried to hack another company in May` renders its full preserved article text in Reader while the existing `D=IN, S=MATERIAL, P=UNKNOWN -> AWARE` explanation remains available only in RAOS Inspector.

Validation before commit:

```text
npm run typecheck      PASS
npm run build          PASS
GET /                  200
GET /inbox             200
GET /attention         200
GET /kernel            200
GET /watch             200
GET /system            200
```

Reader, Attention, Watch, Context, RAOS System, and deep-linked Source Inspector were visually checked in a real Chromium render.

## 9. Architecture status

`RAOS_CANONICAL_ARCHITECTURE.md` remains unchanged. User Space / System Space is a frontend presentation separation and does not alter RAOS module boundaries, authority, dataflow, research↔dogfood identity, or persisted semantics.

Next frontend changes remain dogfood-driven. The new default question is no longer “can the user see RAOS internals?” but “does the user receive the right information, meaning, and action with the minimum necessary cognitive overhead?”
