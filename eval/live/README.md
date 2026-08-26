# Live Eval

Real OpenAI-compatible model evaluation. **Not part of ordinary CI.**

Ordinary CI remains Rule + Fake Model (Eval v0.1). Live Eval is explicit:

```bash
# from repo root
python eval/live/run_live_eval.py --dry-run
python eval/live/run_live_eval.py --manifest eval/live/manifest.example.yaml
```

Requires `RAOS_COGNITIVE_PROVIDER=model` and `RAOS_LLM_API_KEY` for a real run.

## Human Gold v2 (fixed template)

Label every case with these **five** fields only. Human Gold is never produced by a model.

```yaml
human_gold:
  attention_state: [ENGAGE]                 # multi-select: DROP | AWARE | WATCH | ENGAGE
  processing_modes: [VERIFY, SYNTHESIZE]    # multi-select: SCAN | LEARN | VERIFY | DEEP_DIVE | SYNTHESIZE
  kernel_targets: [Motor Intelligence]      # Kernel titles/ids, or [NONE]
  cognitive_effects: [REFINE, REINFORCE]    # multi-select: REINFORCE | CHALLENGE | REFINE | OPEN_NEW | NO_MATERIAL_CHANGE
  expected_delta: "If absorbed, refine the motor/cognitive split without treating the source as proof."
```

| Field | Kind | Locate / Estimate / Route |
|---|---|---|
| `kernel_targets` | choice (nodes or `NONE`) | Locate |
| `cognitive_effects` | multi-select | Estimate |
| `expected_delta` | free text | Estimate |
| `attention_state` | multi-select (acceptable set) | Route |
| `processing_modes` | multi-select | Route |

Same-length `kernel_targets` and `cognitive_effects` zip into target–effect pairs. Otherwise `cognitive_effects` is the acceptable set for every listed target.

Empty gold ⇒ `UNLABELED`: the run is stored, **excluded from accuracy denominators**.

## What Codex provides

- schema (`schema.py`)
- example manifest (slots only)
- runner
- metrics
- report writer
- Human Gold template

## What Codex does not provide

- 30 invented “real” articles
- Human Gold labels
- Source automation (RSS, arXiv, GitHub watchers, 公众号 crawlers)

Add real `source.text` / `url` / `local_file` and Human Gold incrementally.

## Target composition (30)

| n | kind |
|---|---|
| 5 | 公众号 / 媒体长文 |
| 5 | paper abstract / section / PDF |
| 5 | official company / research blog |
| 5 | GitHub / benchmark / technical release |
| 5 | cross-domain decision / investment / startup |
| 5 | low-value / irrelevant / hype |

Future in-domain cases when original materials exist: 银河通用, SpaceClaw / WorldDreamer, 共生知行, 创业股权.

## Report

Each run writes `eval/live/results/<timestamp>/`:

- `summary.json`
- `summary.md`
- `cases.jsonl`

The report scores the v2 Human Gold fields:

- Attention hit
- Processing Mode acceptable (predicted ⊆ gold)
- Kernel Target hit (`NONE` is first-class)
- Cognitive Effect acceptable
- Expected Delta present for human review (not auto-scored)

`cases.jsonl` includes `stage_provenance`, `attention_state`, `processing_mode`, kernel matches, `cognitive_impact`, `evidence_stage_skipped`, and `delta_summary`.

Live Eval v0.1.1+ runs the **production pipeline** (chunking → extraction → evidence → query embedding → kernel match → cognitive impact assessment → Attention Policy → model delta). It does not reimplement an eval-only path.

Legacy gold keys (`must_match_kernel`, `key_claims`, `expected_effects`, …) still parse if present. They are not part of the default template and are not required to run v2 Live Eval.

A model-stage fallback is recorded as `prediction_source: "rule-fallback"` with `model_prediction: false` and is excluded from model accuracy denominators. Do not treat rule-fallback output as a successful model prediction.
