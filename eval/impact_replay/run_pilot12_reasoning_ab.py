#!/usr/bin/env python3
"""RAOS Pilot-12 Cognitive Impact reasoning A/B experiment.

Runs a fresh Pilot-12 production pass to create EXACT impact-input-v0.2
snapshots, then performs two controlled Impact-only experiments on the same
frozen input:

  1) Thinking effect:       disabled  vs enabled, reasoning_effort omitted
  2) Reasoning-effort effect: low     vs high, with thinking enabled

Outputs:
  report.md      - compact report intended to paste back into ChatGPT
  report.json    - machine-readable summary
  replays.jsonl  - detailed per-replay records (including raw/grounded/primary)
  experiment.db  - isolated SQLite DB for provenance/replay

This script intentionally does NOT rerun Scheduler for replay conditions, so
quality metrics here are Update(Operation, Target), not Disposition.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

EXPECTED_HEAD = "983c7f01071a5456979fcae8516dbda7a2be118f"
DIAGNOSTIC_CASES = {"pilot12-03", "pilot12-05", "pilot12-07", "pilot12-12"}
TARGETED_OPS = {"REINFORCE", "CHALLENGE"}


def repo_root() -> Path:
    here = Path(__file__).resolve()
    # Preferred location: <repo>/eval/impact_replay/<this-file>
    if len(here.parents) >= 3 and (here.parents[2] / "backend").is_dir():
        return here.parents[2]
    # Also allow running a downloaded copy from repo root or elsewhere.
    cwd = Path.cwd().resolve()
    if (cwd / "backend").is_dir() and (cwd / "eval" / "live").is_dir():
        return cwd
    raise SystemExit("Run this script from the Research-Attention-OS repository root.")


def load_simple_dotenv(path: Path) -> None:
    """Load the repo's ordinary KEY=value .env before app.config is imported."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def git_head(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def git_dirty(root: Path) -> bool:
    return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())


def mean(values: list[float | int | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else None


def median(values: list[float | int | None]) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return round(float(statistics.median(vals)), 3) if vals else None


def pct(num: int, den: int) -> str:
    return "n/a" if not den else f"{100.0 * num / den:.1f}%"


def normalize_op(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    text = str(value)
    return None if text in {"", "None", "null"} else text


def prediction_label(op: str | None, target_code: str | None) -> str:
    if op is None:
        return "NONE"
    if op in TARGETED_OPS:
        return f"{op}:{target_code or 'UNKNOWN'}"
    return op


def score_update(pred: dict, gold: dict) -> dict:
    pop = pred.get("operation")
    ptarget = pred.get("target_code")
    gop = gold.get("operation")
    gtarget = gold.get("target_code")
    op_hit = pop == gop
    target_applicable = gop in TARGETED_OPS
    target_hit = (ptarget == gtarget) if target_applicable else None
    if gop is None:
        exact = pop is None and pred.get("target_uuid") is None
    elif gop == "OPEN_NEW":
        exact = pop == "OPEN_NEW" and pred.get("target_uuid") is None
    elif target_applicable:
        exact = op_hit and bool(target_hit)
    else:
        exact = op_hit
    return {
        "operation_hit": bool(op_hit),
        "target_applicable": target_applicable,
        "target_hit": target_hit,
        "exact_update_hit": bool(exact),
    }


def summarize_prediction_labels(records: list[dict]) -> str:
    labels = Counter(r["prediction"]["label"] for r in records if not r.get("error"))
    if not labels:
        return "ERROR"
    return ", ".join(f"{k}×{v}" if v > 1 else k for k, v in sorted(labels.items()))


def summarize_condition(records: list[dict]) -> dict:
    ok = [r for r in records if not r.get("error")]
    targeted = [r for r in ok if r["score"]["target_applicable"]]
    execution_valid = [r for r in ok if (r.get("runtime") or {}).get("execution", {}).get("valid")]
    return {
        "n": len(ok),
        "errors": len(records) - len(ok),
        "execution_valid": len(execution_valid),
        "operation_hits": sum(r["score"]["operation_hit"] for r in ok),
        "operation_accuracy": (sum(r["score"]["operation_hit"] for r in ok) / len(ok)) if ok else None,
        "target_hits": sum(bool(r["score"]["target_hit"]) for r in targeted),
        "target_n": len(targeted),
        "target_accuracy": (sum(bool(r["score"]["target_hit"]) for r in targeted) / len(targeted)) if targeted else None,
        "exact_hits": sum(r["score"]["exact_update_hit"] for r in ok),
        "exact_accuracy": (sum(r["score"]["exact_update_hit"] for r in ok) / len(ok)) if ok else None,
        "latency_ms_mean": mean([(r.get("runtime") or {}).get("latency_ms") for r in ok]),
        "latency_ms_median": median([(r.get("runtime") or {}).get("latency_ms") for r in ok]),
        "prompt_tokens_mean": mean([(r.get("runtime") or {}).get("prompt_tokens") for r in ok]),
        "completion_tokens_mean": mean([(r.get("runtime") or {}).get("completion_tokens") for r in ok]),
        "cost_usd_mean": mean([(r.get("runtime") or {}).get("estimated_cost_usd") for r in ok]),
    }


def aggregate_pairwise(pairs: list[dict], subset: set[str] | None = None) -> dict:
    rows = [p for p in pairs if subset is None or p["case_id"] in subset]
    valid = [p for p in rows if p.get("causal_valid")]
    improved = regressed = both_correct = both_wrong = 0
    raw_changed = grounded_changed = primary_changed = 0
    for p in valid:
        a, b = p["a_score"]["exact_update_hit"], p["b_score"]["exact_update_hit"]
        if (not a) and b:
            improved += 1
        elif a and (not b):
            regressed += 1
        elif a and b:
            both_correct += 1
        else:
            both_wrong += 1
        diff = p.get("comparison", {}).get("diff", {})
        raw_changed += bool(diff.get("raw_effects"))
        grounded_changed += bool(diff.get("grounded_effects"))
        primary_changed += bool(diff.get("primary_update"))
    return {
        "pairs": len(rows),
        "valid_pairs": len(valid),
        "improved": improved,
        "regressed": regressed,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "raw_changed": raw_changed,
        "grounded_changed": grounded_changed,
        "primary_changed": primary_changed,
    }


def fmt_acc(x: float | None) -> str:
    return "n/a" if x is None else f"{100*x:.1f}%"


def main() -> int:
    root = repo_root()
    load_simple_dotenv(root / ".env")

    # Pydantic optional numeric fields reject blank strings; treat blank as unset.
    for key in ("RAOS_LLM_INPUT_COST_PER_1M", "RAOS_LLM_OUTPUT_COST_PER_1M", "RAOS_EMBEDDING_DIMENSIONS"):
        if os.environ.get(key) == "":
            os.environ.pop(key, None)

    parser = argparse.ArgumentParser(description="Pilot-12 exact Impact reasoning A/B")
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--repeats", type=int, default=2, help="repeats per condition; default 2")
    parser.add_argument("--timeout", type=float, default=120.0, help="same Impact timeout on all conditions")
    parser.add_argument("--manifest", default="eval/live/manifest.pilot12.v2.yaml")
    parser.add_argument("--cases", default="", help="comma-separated case ids; default all 12")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--sleep", type=float, default=0.2, help="sleep between model replays")
    parser.add_argument("--allow-head-mismatch", action="store_true")
    args = parser.parse_args()

    head = git_head(root)
    if head != EXPECTED_HEAD and not args.allow_head_mismatch:
        raise SystemExit(
            f"HEAD is {head}, expected reviewed harness {EXPECTED_HEAD}. "
            "Use --allow-head-mismatch only if you intentionally changed code."
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir).resolve() if args.out_dir else (root / "eval" / "impact_replay" / "results" / f"{stamp}_pilot12_reasoning_ab")
    out_dir.mkdir(parents=True, exist_ok=False)
    db_path = (out_dir / "experiment.db").resolve()

    # Override experiment-critical config BEFORE app.config is imported.
    os.environ["RAOS_DATABASE_URL"] = "sqlite:///" + str(db_path)
    os.environ["RAOS_AUTO_CREATE_TABLES"] = "true"
    os.environ["RAOS_COGNITIVE_PROVIDER"] = "model"
    os.environ["RAOS_LLM_MODEL"] = args.model
    os.environ["RAOS_LLM_THINKING_PROTOCOL"] = "deepseek"

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    backend = root / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    from sqlalchemy import select

    import app.models  # noqa: F401
    from app.config import settings
    from app.db import Base, SessionLocal, engine
    from app.models.kernel import KernelNode
    from app.services.impact_replay import ImpactReplayConfig, compare_replays, replay_analysis_run
    from eval.live.kernel_snapshot import snapshot_for_fixture
    from eval.live.run_live_eval import analysis_payload_to_eval_row, ensure_kernel_fixture, load_manifest, run_live_pipeline

    if not settings.llm_api_key:
        raise SystemExit("RAOS_LLM_API_KEY is missing. Put it in the shell environment or repo .env.")
    if settings.llm_thinking_protocol != "deepseek":
        raise SystemExit(f"thinking protocol is {settings.llm_thinking_protocol!r}, expected 'deepseek'")
    if settings.cognitive_provider != "model":
        raise SystemExit(f"cognitive provider is {settings.cognitive_provider!r}, expected 'model'")

    Base.metadata.create_all(bind=engine)
    manifest = load_manifest(root / args.manifest)
    wanted = {x.strip() for x in args.cases.split(",") if x.strip()}
    cases = [c for c in manifest.cases if not wanted or c.id in wanted]
    if wanted - {c.id for c in cases}:
        raise SystemExit(f"Unknown case ids: {sorted(wanted - {c.id for c in cases})}")
    if not cases:
        raise SystemExit("No cases selected")

    db = SessionLocal()
    all_records: list[dict] = []
    pair_records: dict[str, list[dict]] = {"thinking": [], "effort": []}
    production: list[dict] = []

    try:
        # Fresh isolated MVP Kernel, including best-effort embeddings.
        ensure_kernel_fixture(db, "mvp")
        db.commit()
        snapshot_refs = snapshot_for_fixture("mvp")
        title_to_code = {ref.title: ref.id for ref in snapshot_refs}
        nodes = db.execute(select(KernelNode).where(KernelNode.deleted_at.is_(None))).scalars().all()
        uuid_to_code = {str(n.id): title_to_code.get(n.title or "") for n in nodes}

        conditions = {
            "OFF": ImpactReplayConfig(
                provider="model", model=args.model, thinking="disabled", reasoning_effort=None,
                timeout=args.timeout,
            ),
            "ON": ImpactReplayConfig(
                provider="model", model=args.model, thinking="enabled", reasoning_effort=None,
                timeout=args.timeout,
            ),
            "LOW": ImpactReplayConfig(
                provider="model", model=args.model, thinking="enabled", reasoning_effort="low",
                timeout=args.timeout,
            ),
            "HIGH": ImpactReplayConfig(
                provider="model", model=args.model, thinking="enabled", reasoning_effort="high",
                timeout=args.timeout,
            ),
        }

        for case_index, case in enumerate(cases, 1):
            print(f"\n[{case_index}/{len(cases)}] fresh production run: {case.id}", flush=True)
            try:
                payload = run_live_pipeline(db, case)
                db.commit()
            except Exception as exc:
                db.rollback()
                production.append({"case_id": case.id, "error": repr(exc)})
                print(f"  PRODUCTION ERROR: {exc}", flush=True)
                continue

            run_id = payload["analysis_run"]["id"]
            impact_input = payload.get("impact_input") or {}
            eval_row = analysis_payload_to_eval_row(payload)
            gold_obj = case.human_gold.update if case.human_gold else None
            gold = {
                "operation": normalize_op(gold_obj.operation) if gold_obj else None,
                "target_code": gold_obj.target_node_id if gold_obj else None,
            }
            production.append({
                "case_id": case.id,
                "analysis_run_id": run_id,
                "input_fidelity": impact_input.get("input_fidelity"),
                "input_fingerprint": impact_input.get("input_fingerprint"),
                "gold": gold,
                "production_disposition": payload.get("disposition"),
                "production_update": payload.get("update"),
                "embedding_used": eval_row.get("embedding_used"),
                "embedding_model": eval_row.get("embedding_model"),
                "retrieval_method": eval_row.get("retrieval_method"),
                "fallback_stages": eval_row.get("fallback_stages") or [],
                "stage_provenance": eval_row.get("stage_provenance"),
            })

            if impact_input.get("input_fidelity") != "EXACT":
                print(f"  WARNING: fresh run is {impact_input.get('input_fidelity')}, expected EXACT", flush=True)

            for rep in range(1, args.repeats + 1):
                # Counterbalance order to reduce time/load ordering bias.
                order = ["OFF", "ON", "LOW", "HIGH"] if rep % 2 else ["HIGH", "LOW", "ON", "OFF"]
                results: dict[str, dict] = {}
                entries: dict[str, dict] = {}
                print(f"  repeat {rep}: {' -> '.join(order)}", flush=True)

                for cond in order:
                    cfg = conditions[cond]
                    cfg = ImpactReplayConfig(**{**cfg.__dict__, "label": f"{case.id}-r{rep}-{cond.lower()}"})
                    try:
                        replay = replay_analysis_run(db, UUID(run_id), config=cfg, persist=True)
                        db.commit()
                        primary = (replay.get("stages") or {}).get("primary_update") or {}
                        target_uuid = primary.get("target_node_id")
                        pred = {
                            "operation": normalize_op(primary.get("operation")),
                            "target_uuid": target_uuid,
                            "target_code": uuid_to_code.get(str(target_uuid)) if target_uuid else None,
                        }
                        pred["label"] = prediction_label(pred["operation"], pred["target_code"])
                        score = score_update(pred, gold)
                        entry = {
                            "case_id": case.id,
                            "repeat": rep,
                            "condition": cond,
                            "analysis_run_id": run_id,
                            "input_fidelity": replay.get("input_fidelity"),
                            "input_fingerprint": replay.get("input_fingerprint"),
                            "gold": gold,
                            "prediction": pred,
                            "score": score,
                            "runtime": replay.get("runtime"),
                            "config": replay.get("config"),
                            "stages": replay.get("stages"),
                            "attribution": replay.get("attribution"),
                            "replay_id": replay.get("id"),
                            "error": None,
                        }
                        results[cond] = replay
                        entries[cond] = entry
                        all_records.append(entry)
                        print(
                            f"    {cond:<4} {pred['label']:<24} exact={score['exact_update_hit']} "
                            f"latency={((replay.get('runtime') or {}).get('latency_ms'))}ms",
                            flush=True,
                        )
                    except Exception as exc:
                        db.rollback()
                        entry = {
                            "case_id": case.id, "repeat": rep, "condition": cond,
                            "analysis_run_id": run_id, "gold": gold, "error": repr(exc),
                        }
                        entries[cond] = entry
                        all_records.append(entry)
                        print(f"    {cond:<4} ERROR {exc}", flush=True)
                    if args.sleep:
                        time.sleep(args.sleep)

                def add_pair(name: str, a: str, b: str, expected_var: str) -> None:
                    if a not in results or b not in results:
                        pair_records[name].append({
                            "case_id": case.id, "repeat": rep, "causal_valid": False,
                            "invalid_reasons": ["missing_replay"],
                        })
                        return
                    cmp = compare_replays(results[a], results[b])
                    valid = bool(cmp.get("causal_comparison")) and set(cmp.get("variable_diff") or {}) == {expected_var}
                    pair_records[name].append({
                        "case_id": case.id,
                        "repeat": rep,
                        "a_condition": a,
                        "b_condition": b,
                        "a_score": entries[a]["score"],
                        "b_score": entries[b]["score"],
                        "a_prediction": entries[a]["prediction"],
                        "b_prediction": entries[b]["prediction"],
                        "causal_valid": valid,
                        "expected_variable": expected_var,
                        "comparison": cmp,
                        "invalid_reasons": cmp.get("invalid_reasons") or ([] if valid else ["unexpected_variable_diff"]),
                    })

                add_pair("thinking", "OFF", "ON", "thinking")
                add_pair("effort", "LOW", "HIGH", "reasoning_effort")

        # ---------- aggregate ----------
        by_condition: dict[str, list[dict]] = defaultdict(list)
        by_case_condition: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in all_records:
            by_condition[r["condition"]].append(r)
            by_case_condition[(r["case_id"], r["condition"])].append(r)

        condition_summary = {c: summarize_condition(by_condition.get(c, [])) for c in ("OFF", "ON", "LOW", "HIGH")}
        thinking_all = aggregate_pairwise(pair_records["thinking"])
        thinking_diag = aggregate_pairwise(pair_records["thinking"], DIAGNOSTIC_CASES)
        effort_all = aggregate_pairwise(pair_records["effort"])
        effort_diag = aggregate_pairwise(pair_records["effort"], DIAGNOSTIC_CASES)

        exact_count = sum(p.get("input_fidelity") == "EXACT" for p in production if not p.get("error"))
        embedding_count = sum(bool(p.get("embedding_used")) for p in production if not p.get("error"))
        production_errors = [p for p in production if p.get("error")]
        production_fallbacks = [p for p in production if p.get("fallback_stages")]

        summary = {
            "timestamp": stamp,
            "git_head": head,
            "git_dirty": git_dirty(root),
            "expected_head": EXPECTED_HEAD,
            "model": args.model,
            "thinking_protocol": settings.llm_thinking_protocol,
            "manifest": args.manifest,
            "cases": [c.id for c in cases],
            "diagnostic_cases": sorted(DIAGNOSTIC_CASES & {c.id for c in cases}),
            "repeats": args.repeats,
            "impact_timeout": args.timeout,
            "database": str(db_path),
            "embedding_model_config": settings.embedding_model,
            "exact_fresh_runs": exact_count,
            "fresh_runs": len([p for p in production if not p.get("error")]),
            "embedding_used_runs": embedding_count,
            "production_errors": production_errors,
            "production_fallbacks": production_fallbacks,
            "condition_summary": condition_summary,
            "pairwise": {
                "thinking_all": thinking_all,
                "thinking_diagnostic": thinking_diag,
                "effort_all": effort_all,
                "effort_diagnostic": effort_diag,
            },
            "production": production,
            "thinking_pairs": pair_records["thinking"],
            "effort_pairs": pair_records["effort"],
        }

        # ---------- detailed JSONL ----------
        with (out_dir / "replays.jsonl").open("w", encoding="utf-8") as fh:
            for r in all_records:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True, default=str) + "\n")

        (out_dir / "report.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

        # ---------- markdown ----------
        md: list[str] = []
        md.append("# RAOS Pilot-12 — Cognitive Impact Reasoning A/B")
        md.append("")
        md.append(f"- **HEAD:** `{head}`")
        md.append(f"- **Model:** `{args.model}`")
        md.append(f"- **Thinking protocol:** `{settings.llm_thinking_protocol}`")
        md.append(f"- **Manifest:** `{args.manifest}`")
        md.append(f"- **Cases:** {len(cases)}; **repeats/condition:** {args.repeats}")
        md.append(f"- **Fresh EXACT inputs:** {exact_count}/{len(cases)}")
        md.append(f"- **Embedding used:** {embedding_count}/{len(cases)}")
        md.append(f"- **Production errors:** {len(production_errors)}; **runs with any fallback:** {len(production_fallbacks)}")
        md.append("")
        md.append("## Experiment definitions")
        md.append("")
        md.append("1. **Thinking:** `OFF = thinking=disabled, effort omitted` vs `ON = thinking=enabled, effort omitted`. Expected effective diff: `{thinking}`.")
        md.append("2. **Reasoning effort:** `LOW = thinking=enabled, effort=low` vs `HIGH = thinking=enabled, effort=high`. Expected effective diff: `{reasoning_effort}`.")
        md.append("")
        md.append("> This is Impact-only replay. It evaluates **Update(Operation, Target)**. Scheduler/Disposition is not rerun and is not scored here.")
        md.append("")

        md.append("## Experimental validity")
        md.append("")
        md.append("| Experiment | Valid causal pairs | Total pairs | Diagnostic valid | Diagnostic total |")
        md.append("|---|---:|---:|---:|---:|")
        md.append(f"| Thinking OFF→ON | {thinking_all['valid_pairs']} | {thinking_all['pairs']} | {thinking_diag['valid_pairs']} | {thinking_diag['pairs']} |")
        md.append(f"| Effort LOW→HIGH | {effort_all['valid_pairs']} | {effort_all['pairs']} | {effort_diag['valid_pairs']} | {effort_diag['pairs']} |")
        md.append("")

        md.append("## Aggregate Update quality and Impact cost")
        md.append("")
        md.append("| Condition | N | Operation acc | Target acc* | Exact Update acc | Mean latency ms | Mean prompt tok | Mean completion tok |")
        md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for cond in ("OFF", "ON", "LOW", "HIGH"):
            s = condition_summary[cond]
            md.append(
                f"| {cond} | {s['n']} | {fmt_acc(s['operation_accuracy'])} | {fmt_acc(s['target_accuracy'])} | "
                f"{fmt_acc(s['exact_accuracy'])} | {s['latency_ms_mean']} | {s['prompt_tokens_mean']} | {s['completion_tokens_mean']} |"
            )
        md.append("")
        md.append("*Target accuracy denominator only includes Gold REINFORCE/CHALLENGE cases.*")
        md.append("")

        def pair_table(title: str, agg_all: dict, agg_diag: dict) -> None:
            md.append(f"## {title}")
            md.append("")
            md.append("| Scope | Improved | Regressed | Both correct | Both wrong | Raw changed | Grounded changed | Primary changed |")
            md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
            md.append(f"| All | {agg_all['improved']} | {agg_all['regressed']} | {agg_all['both_correct']} | {agg_all['both_wrong']} | {agg_all['raw_changed']} | {agg_all['grounded_changed']} | {agg_all['primary_changed']} |")
            md.append(f"| Diagnostic 03/05/07/12 | {agg_diag['improved']} | {agg_diag['regressed']} | {agg_diag['both_correct']} | {agg_diag['both_wrong']} | {agg_diag['raw_changed']} | {agg_diag['grounded_changed']} | {agg_diag['primary_changed']} |")
            md.append("")

        pair_table("Thinking effect: OFF → ON", thinking_all, thinking_diag)
        pair_table("Reasoning-effort effect: LOW → HIGH", effort_all, effort_diag)

        def case_table(case_ids: list[str], title: str) -> None:
            md.append(f"## {title}")
            md.append("")
            md.append("| Case | Gold Update | OFF | ON | LOW | HIGH | OFF exact | ON exact | LOW exact | HIGH exact |")
            md.append("|---|---|---|---|---|---|---:|---:|---:|---:|")
            prod_by_case = {p.get("case_id"): p for p in production}
            for cid in case_ids:
                prod = prod_by_case.get(cid, {})
                gold = prod.get("gold") or {"operation": None, "target_code": None}
                gold_label = prediction_label(gold.get("operation"), gold.get("target_code"))
                cells = {}
                rates = {}
                for cond in ("OFF", "ON", "LOW", "HIGH"):
                    rs = by_case_condition.get((cid, cond), [])
                    cells[cond] = summarize_prediction_labels(rs)
                    good = [r for r in rs if not r.get("error")]
                    hits = sum(r["score"]["exact_update_hit"] for r in good)
                    rates[cond] = f"{hits}/{len(good)}" if good else "ERR"
                md.append(
                    f"| {cid} | {gold_label} | {cells['OFF']} | {cells['ON']} | {cells['LOW']} | {cells['HIGH']} | "
                    f"{rates['OFF']} | {rates['ON']} | {rates['LOW']} | {rates['HIGH']} |"
                )
            md.append("")

        selected_ids = [c.id for c in cases]
        case_table([c for c in selected_ids if c in DIAGNOSTIC_CASES], "Diagnostic probes")
        case_table(selected_ids, "Full selected set")

        invalid_pairs = []
        for exp, rows in pair_records.items():
            for p in rows:
                if not p.get("causal_valid"):
                    invalid_pairs.append({
                        "experiment": exp,
                        "case_id": p.get("case_id"),
                        "repeat": p.get("repeat"),
                        "reasons": p.get("invalid_reasons") or p.get("comparison", {}).get("invalid_reasons"),
                        "variable_diff": p.get("comparison", {}).get("variable_diff"),
                    })
        md.append("## Invalid / non-causal pairs")
        md.append("")
        if not invalid_pairs:
            md.append("None. All requested pairs satisfied the Harness causal-comparison contract.")
        else:
            for item in invalid_pairs:
                md.append(f"- `{item['experiment']}` `{item['case_id']}` repeat {item['repeat']}: reasons={item['reasons']}, variable_diff={item['variable_diff']}")
        md.append("")

        md.append("## Provenance notes")
        md.append("")
        md.append("- Every case was rerun through the current production pipeline in an isolated SQLite DB before replay, so the intended input fidelity is `EXACT` (`impact-input-v0.2`).")
        md.append("- A/B comparisons use the Harness `causal_comparison` gate and actual wire-effective runtime conditions.")
        md.append("- Model stochasticity is not treated as Harness failure; repeats are reported rather than silently collapsed.")
        md.append("- No pre-`raos-impact-replay-0.2.1` replay artifact is reused.")
        md.append("")
        md.append("## Files")
        md.append("")
        md.append("- `report.md` — send this first")
        md.append("- `report.json` — aggregate + pairwise machine-readable details")
        md.append("- `replays.jsonl` — full raw/grounded/primary/runtime records")
        md.append("- `experiment.db` — isolated replay database")
        md.append("")

        report_md = "\n".join(md) + "\n"
        (out_dir / "report.md").write_text(report_md, encoding="utf-8")

        print("\n=== DONE ===")
        print(f"Report: {out_dir / 'report.md'}")
        print(f"JSON:   {out_dir / 'report.json'}")
        print(f"Detail: {out_dir / 'replays.jsonl'}")
        print(f"DB:     {db_path}")
        print("\nPaste report.md back to ChatGPT. If a result needs stage-level diagnosis, also send replays.jsonl.")

        # Nonzero only for structural experiment failures, while still preserving report files.
        if exact_count != len(cases):
            print("WARNING: not every fresh run produced EXACT input.", file=sys.stderr)
            return 2
        if thinking_all["valid_pairs"] != thinking_all["pairs"] or effort_all["valid_pairs"] != effort_all["pairs"]:
            print("WARNING: one or more A/B pairs failed causal-comparison validity.", file=sys.stderr)
            return 3
        if production_errors:
            return 4
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
