# 185 — Session Hand-off: RAOS Dogfood, DSP, Acquisition, UI

Date: 2026-09-13

## 0. Read this first

This file is the shortest recovery point for the next session.
Do **not** infer current architecture from old phase docs alone.
The authoritative current architecture is `RAOS_CANONICAL_ARCHITECTURE.md`.
The roadmap is `11_ROADMAP_AND_PROGRESS.md`.

Functional HEAD before this hand-off-only commit:

```text
b4175dddd97ac5ff9b6ffd3ff8166d3682746042
ui: make attention feed source-centric
```

Repo:

```text
https://github.com/cookyecat/Research-Attention-OS
/Users/liyang/Developer/Research-Attention-OS
branch: main
```
## 1. Current global map

RAOS is now in real developer dogfood, not another isolated research harness.
Current intended main flow:

```text
External World
→ Acquisition Plane
→ RAOS Source
→ Semantic Sensor
→ Semantic Evidence Auditor
→ Audited World Representation
   ├─ Cognitive Path
   │  → Locate → Relation Mapping → Support Binding
   │  → Grounding / Jurisdiction → Authority
   │  → cardinal-free legality → Magnitude-Free / Pareto
   │  → AWARE / WATCH / ENGAGE
   └─ No-Delta Awareness Path
      → audited Event projection → D / S / P
      → AWARE iff S AND (D OR P)
      → DROP / AWARE
→ Final Attention
→ authorized public update / WATCH / KernelPatch
```

Critical invariant:

```text
Acquisition observes; it does not judge.
Cognitive effects own cognitive Attention.
DSP only owns DROP ↔ AWARE when DecisionCause/Delta is NONE.
```
## 2. DSP restoration — completed

A major architecture gap was found and fixed this session.
D/S/P had **not** been replaced; it had been researched and validated earlier,
then accidentally left out of the online pipeline during later cognitive-path work.

Restored contract:

```text
Delta / DecisionCause exists
→ cognitive path owns Attention

Delta / DecisionCause = NONE
→ D/S/P no-Delta awareness gate
→ DROP or AWARE
```

Frozen no-Delta rule:

```text
AWARE iff S AND (D OR P)
```

D = standing attention jurisdiction.
S = material consequence to consequential shared/public systems.
P = collective-attention salience in the event's objective constituency.

Relevant closure commit:

```text
8ac0b65 fix: restore no-delta dsp awareness path
```
## 3. The Verge article re-test — key result

Article:

```text
OpenAI’s rogue AI tried to hack another company in May | The Verge
```

Old incomplete online result (DSP missing):

```text
Relation Mapping = ∅
Delta = NONE
→ DROP
```

After DSP restoration:

```text
Delta = NONE
D = IN
S = MATERIAL
P = UNKNOWN
→ AWARE
```

This matched the user's Human Gold.
Interpretation: no Kernel-changing cognition, but the event is in standing jurisdiction
and materially consequential, therefore it is worth knowing once.

Result doc:

```text
184_CANONICAL_ARCHITECTURE_AND_DSP_ONLINE_RESTORATION_RESULT.md
```
## 4. P handling — important discipline

Theory remains latent:

```text
P(E,t) = LatentSalience(R_E(≤t))
```

Direct internet-wide statistics are not available, so engineering may use an estimator
or an explicitly marked simulation/counterfactual.
Do not pretend simulated P is observed P.

Current frozen P state semantics are:

```text
SALIENT / NOT_SALIENT / UNKNOWN
```

For the Verge case, counterfactual bracketing showed:

```text
P = UNKNOWN       → AWARE
P = SALIENT       → AWARE
P = NOT_SALIENT   → AWARE
```

Because D=IN and S=MATERIAL already determine the Boolean gate.
Potential future optimization: evaluate D/S first and only estimate P when decision-critical.
This optimization was explicitly deferred; do not silently change the theoretical rule.
## 5. Acquisition Plane v0.1 — completed and active

Top-level design is frozen in:

```text
182_ACQUISITION_PLANE_V01_TOP_LEVEL_DESIGN.md
```

Core objects:

```text
Source
Observation
Information Object
Snapshot
```

Main principles:

```text
Source defines where RAOS looks, not what RAOS should care about.
Observation is distinct from Information Object.
External information has temporal snapshots; history is not overwritten.
Acquisition ends at the Raw Information Boundary.
No cognitive relevance filtering inside Acquisition.
```

Implementation/initial dogfood commits:

```text
d0a8968 feat: add acquisition plane v0.1 rss dogfood
4cddfb8 feat: activate unattended acquisition dogfood
```
## 6. Current unattended sources and worker

Current Source Registry intentionally stays small:

```text
The Verge RSS       every 30 min
Google DeepMind     every 60 min
NVIDIA Blog         every 60 min
```

New sources bootstrap a present-time baseline and do not analyze historical backlog.
One source failure is isolated and must not terminate the entire worker.

Worker uses the same `.env` contract as the HTTP backend, avoiding legacy/default drift.
Current intended execution identity:

```text
RAOS_COGNITIVE_PROVIDER=model
RAOS_COGNITIVE_CONTRACT=research-aligned-v1
RAOS_NO_DELTA_AWARENESS_CONTRACT=dsp-v1
RAOS_DECISION_STRATEGY_ID=pareto-multidelta-cardinal-free-effect-anchored-open-new
```

Observed running processes at hand-off time:

```text
backend uvicorn: PID 56057, port 8000
acquisition worker: PID 57197
frontend next dev: PID 60947, port 3000
```

PIDs are operational observations, not architectural constants.
## 7. Frontend / product state

Web UI:

```text
http://localhost:3000
```

Backend:

```text
http://127.0.0.1:8000
```

Current pages:

```text
Home
Inbox
Attention
Kernel
Watch
```

`Inbox` supports pasted text, URL, PDF, and manual observation.
`Attention` is now source-centric: one Source card = one latest current Attention state.
Old plans remain provenance but should not be repeated in the feed.

Frontend UX commit:

```text
b4175dd ui: make attention feed source-centric
```
## 8. Frontend hydration issue found at end of session

Symptom reported by user:

```text
Only left navigation links worked.
Page-internal buttons did not respond.
Attention page stayed at: "No current attention items."
```

Backend was healthy and had 15 plans; deduped current non-DROP state was 6 Sources.
Root cause was a broken/stale Next.js client hydration runtime after `next build`
was run while a long-lived `next dev` process shared the same `.next` directory.

Operational fix performed:

```text
stop old next dev
rm -rf frontend/.next
npm run dev
```

After restart, fresh headless Chrome rendered all 6 cards correctly.
Do not run `next build` concurrently with the live `next dev` instance.
If internal buttons stop working again, suspect hydration/client runtime first.

Expected current first card:

```text
AWARE
OpenAI’s rogue AI tried to hack another company in May | The Verge
View analysis →
```
## 9. Known product/data residuals

The Attention feed currently mixes real dogfood Sources with historical development/test Sources.
Examples still visible after source-level dedup:

```text
OpenAI’s rogue AI...                 ← real crawler/dogfood
RAOS research-aligned live smoke     ← dev smoke
Phase 10D.4 rollout smoke test       ← dev smoke
latency paper                        ← historical dev
原方智能...                           ← historical dev
Galaxy General WRC folding robot     ← historical dev
```

Do not delete historical provenance just to make UI look cleaner.
A likely next product-level improvement is to separate:

```text
Live / Dogfood
History / Dev
```

This is a real dogfood UX residual, not an architecture change yet.

Another acquisition residual already observed:

```text
OpenAI RSS discovery works, but generic article URL retrieval returned HTTP 403.
```

Do not expand into a universal anti-bot crawler unless real use justifies it.
## 10. Validation status

DSP restoration focused suite:

```text
69 passed / 1 warning
```

Acquisition-focused suite:

```text
18 passed / 1 warning
```

Latest full backend regression during this session:

```text
713 passed
63 skipped
1 failed
1 warning
```

The only failure remains the historical Case K mismatch:

```text
expected PREEMPT
actual PRIORITY
```

No new backend regressions were introduced by DSP restoration or Acquisition work.
Frontend source-centric change passed TypeScript checking and Next.js production build.
## 11. Working-tree safety

The repo still contains many pre-existing unrelated changes/noise:

```text
tracked deletions under eval/live/results/...
untracked old Phase9A v0.1 WIP
backend/uv.lock untracked
many untracked Phase10/Phase8C14 result directories
docs/ untracked
```

These were intentionally **not** staged in this session.
Continue exact-stage discipline.
Never stage `.env` or unrelated historical result noise.

Important old Phase9A WIP examples:

```text
backend/tests/eval/test_phase9a_kernel_causal_alignment_v0_1.py
eval/live/phase9a_kernel_causal_alignment_v0_1.py
eval/live/run_phase9a_kernel_causal_alignment_v0_1.py
```

Do not clean or commit them unless explicitly working on that old branch of research.
## 12. Recommended next-session first actions

1. Open `RAOS_CANONICAL_ARCHITECTURE.md` first.
2. Confirm backend, acquisition worker, and frontend are alive.
3. Open `http://localhost:3000/attention` and verify cards hydrate/client buttons work.
4. Use the system normally; do not pre-invent crawler corner cases.
5. Capture the first real bad DROP/AWARE/WATCH/ENGAGE or retrieval failure as a residual.
6. Attribute from the earliest causal layer before changing policy.

Current product/research strategy:

```text
Use the system → collect real residuals → causal attribution → minimal correction.
```

The user explicitly prefers top-level architecture first, then real use;
do not spend cycles anticipating dozens of edge cases before they occur.

If architecture changes, update `RAOS_CANONICAL_ARCHITECTURE.md` in the same commit.
If only implementation/UX changes and architecture does not, do not churn the canonical diagram.

Current likely near-term work is product dogfood and crawler/feed expansion only when justified by use,
not another abstract research phase.
## 13. Key documents / commits to read only if needed

```text
RAOS_CANONICAL_ARCHITECTURE.md
11_ROADMAP_AND_PROGRESS.md
181_RESEARCH_PRODUCTION_ALIGNMENT_DOGFOOD_ROLLOUT_RESULT.md
182_ACQUISITION_PLANE_V01_TOP_LEVEL_DESIGN.md
183_ACQUISITION_PLANE_V01_RSS_DOGFOOD_RESULT.md
184_CANONICAL_ARCHITECTURE_AND_DSP_ONLINE_RESTORATION_RESULT.md
```

Recent functional commits:

```text
d7c09a4 docs: freeze acquisition plane v0.1 design
d0a8968 feat: add acquisition plane v0.1 rss dogfood
8ac0b65 fix: restore no-delta dsp awareness path
4cddfb8 feat: activate unattended acquisition dogfood
b4175dd ui: make attention feed source-centric
```

Final reminder:

```text
The system is now intended to be used.
Do not confuse "no cognitive Delta" with DROP.
No Delta must pass through DSP.
Do not let Acquisition perform cognitive filtering.
Do not silently treat P UNKNOWN as false.
```
