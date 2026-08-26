# Live Eval

Real OpenAI-compatible model evaluation. **Not part of ordinary CI.**

Ordinary CI remains Rule + Fake Model (Eval v0.1). Live Eval is explicit:

```bash
# from repo root
python eval/live/run_live_eval.py --dry-run
python eval/live/run_live_eval.py --manifest eval/live/manifest.example.yaml
```

Requires `RAOS_COGNITIVE_PROVIDER=model` and `RAOS_LLM_API_KEY` for a real run.

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
Empty gold is `UNLABELED`: the run is stored, **excluded from accuracy denominators**.

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
