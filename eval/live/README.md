# Live Eval

Real OpenAI-compatible model evaluation. **Not part of ordinary CI.**

Ordinary CI remains Rule + Fake Model (Eval v0.1). Live Eval is explicit:

```bash
# from repo root
python eval/live/run_live_eval.py --dry-run
python eval/live/run_live_eval.py --manifest eval/live/manifest.example.yaml
```

Requires `RAOS_COGNITIVE_PROVIDER=model` and `RAOS_LLM_API_KEY` for a real run.

## Human Gold (fixed template)

Label every case with these **three** blocks only. Human Gold is never produced by a model.

```yaml
human_gold:
  disposition: WATCH

  update:
    operation: REINFORCE
    target_node_id: "P1"   # Kernel Snapshot picker id, or empty for OPEN_NEW

  delta_content: "吸收这条信息后，具体形成、改变或新增了什么认知"
```

`target_node_id` is a selectable reference into the **fixed Kernel Snapshot** (`eval/live/kernel_snapshot.py`), not a topic tag and not a recommendation from the current model prediction. Pick by node title; the program stores the snapshot id. Annotators do not need Kernel ontology (PROJECT / BELIEF / QUESTION / MODEL / BOTTLENECK).

| Field | Kind | Meaning |
|---|---|---|
| `disposition` | enum | DROP / AWARE / WATCH / ENGAGE |
| `update.operation` | enum | REINFORCE / CHALLENGE / OPEN_NEW |
| `update.target_node_id` | snapshot picker | required for REINFORCE / CHALLENGE; empty for OPEN_NEW |
| `delta_content` | free text | cognitive delta after absorbing — not a source claim or evidence quote |

Disposition (SCAN / LEARN / REASON / CREATE are internal interpretations, not annotation fields):

| Value | Meaning |
|---|---|
| DROP | 不用管 |
| AWARE | 知道就行 |
| WATCH | 先不深挖，但继续盯 |
| ENGAGE | 现在就认真处理 |

Update operation:

| Value | Meaning |
|---|---|
| REINFORCE | Strengthen Existing — 加固已有 cognitive branch |
| CHALLENGE | Change Existing — 已有 branch 需要被修改、削弱或推翻 |
| OPEN_NEW | Create New — Kernel 中没有合适落点，产生新的 cognitive branch |

Empty gold ⇒ `UNLABELED`: the run is stored, **excluded from accuracy denominators**.

## What Codex provides

- schema (`schema.py`)
- Kernel Snapshot picker (`kernel_snapshot.py`)
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

The report scores the Human Gold contract:

- Disposition hit
- Update Operation hit (operation only)
- Target hit (only when gold is REINFORCE / CHALLENGE on an existing Kernel Snapshot node)
- Exact Update hit (operation and target together; OPEN_NEW must be predicted as OPEN_NEW)
- DeltaContent present for human review (not auto-scored)

`cases.jsonl` includes `stage_provenance`, `disposition`, `update`, `delta_content`, `retrieval_candidates` (pre-matcher Locate list with id/title/rank/score), kernel matches, `cognitive_impact`, `primary_effect`, `evidence_stage_skipped`, and `delta_summary`.

Live Eval v0.1.1+ runs the **production pipeline** (chunking → extraction → evidence → query embedding → kernel match → cognitive impact assessment → Attention Policy → model delta). It does not reimplement an eval-only path.

Legacy gold keys (`attention_state`, `processing_modes`, `kernel_targets`, `cognitive_effects`, `expected_delta`, …) still parse on ingest if present. Retired operations (`REFINE`, `NO_MATERIAL_CHANGE`) are not mapped onto the live contract. They are not part of the default template and are not used to label new cases.

A model-stage fallback is recorded per stage in `stage_provenance`. Live Eval scores Disposition / Update / Target only when the **impact** stage is a model success. A later Delta fallback does not exclude those fields. `prediction_source_by_stage` and `scorable` are written on every cases.jsonl row.
