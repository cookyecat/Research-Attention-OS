"""Run Live Eval against a real OpenAI-compatible model. Not part of ordinary CI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.report import compute_metrics, render_markdown
from eval.live.schema import LiveCase, LiveManifest, gold_status_of, dump_human_gold

FALLBACK_STAGE_STATUSES = {"fallback", "rule-after-fallback"}

# Live Eval scores each Cognitive Dynamics field from the stage that produced it.
METRIC_STAGE = {
    "disposition": "impact",
    "update": "impact",
    "target": "impact",
    "delta_content": "delta",
    "epistemic_separation": "extraction",
}


def _stage_record(provenance, stage: str) -> dict:
    if not isinstance(provenance, dict):
        return {}
    rec = provenance.get(stage)
    return rec if isinstance(rec, dict) else {}


def stage_is_model(provenance, stage: str) -> bool:
    rec = _stage_record(provenance, stage)
    if rec.get("status") in FALLBACK_STAGE_STATUSES:
        return False
    if rec.get("fallback_from"):
        return False
    return rec.get("status") == "success" and rec.get("provider") in {"model", None}


def live_eval_runtime_fields(
    provider=None,
    *,
    provenance=None,
    fallback_used=None,
    provider_type=None,
) -> dict[str, Any]:
    """Surface per-stage provenance. Fallback on one stage does not poison others."""
    provenance = provenance if provenance is not None else getattr(provider, "stage_provenance", None)
    fallback_used = bool(
        fallback_used if fallback_used is not None else getattr(provider, "fallback_used", False)
    )
    provider_type = provider_type if provider_type is not None else getattr(provider, "provider_type", None)
    fallback_stages: list[str] = []
    model_stages: list[str] = []
    prediction_source_by_stage: dict[str, str] = {}
    if isinstance(provenance, dict):
        for stage, rec in provenance.items():
            if not isinstance(rec, dict):
                continue
            if rec.get("status") in FALLBACK_STAGE_STATUSES or rec.get("fallback_from"):
                fallback_stages.append(stage)
                prediction_source_by_stage[stage] = "rule-fallback"
            elif rec.get("provider") == "rule":
                prediction_source_by_stage[stage] = "rule"
            elif rec.get("status") == "success":
                model_stages.append(stage)
                prediction_source_by_stage[stage] = "model"
            else:
                prediction_source_by_stage[stage] = str(rec.get("provider") or rec.get("status") or "unknown")
    any_fallback = fallback_used or bool(fallback_stages)
    impact_model = stage_is_model(provenance, "impact")
    if provider_type == "rule" and not model_stages:
        source = "rule"
    elif impact_model and not fallback_stages:
        source = "model"
    elif impact_model and fallback_stages:
        source = "mixed"
    elif any_fallback:
        source = "rule-fallback"
    elif provider_type == "model+rule-fallback":
        source = "mixed"
    else:
        source = "model"
    return {
        "stage_provenance": provenance,
        "fallback": any_fallback,
        "fallback_stages": fallback_stages,
        "model_stages": model_stages,
        "prediction_source_by_stage": prediction_source_by_stage,
        "prediction_source": source,
        "model_prediction": impact_model,
        "scorable": {
            "disposition": impact_model,
            "update": impact_model,
            "target": impact_model,
            "delta_content": stage_is_model(provenance, "delta"),
            "epistemic_separation": stage_is_model(provenance, "extraction"),
        },
    }


def analysis_payload_to_eval_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Map production pipeline output onto a Live Eval cases.jsonl row."""
    plan = payload.get("attention_plan") or {}
    run = payload.get("analysis_run") or {}
    retrieval = payload.get("retrieval") or {}
    matches = payload.get("kernel_matches") or []
    delta = payload.get("model_delta") or {}
    features = payload.get("features") or {}
    provenance = run.get("stage_provenance") or payload.get("stage_provenance")
    runtime = live_eval_runtime_fields(
        provenance=provenance,
        fallback_used=run.get("fallback_used"),
        provider_type=run.get("provider_type"),
    )
    update = payload.get("update") or plan.get("update") or {"operation": None, "target_node_id": None}
    return {
        "disposition": payload.get("disposition") or plan.get("disposition"),
        "update": update,
        "delta_content": payload.get("delta_content") or delta.get("summary"),
        "kernel_matches": matches,
        "matched_kernel_titles": [m.get("title") for m in matches],
        "matched_kernel_ids": [m.get("node_id") for m in matches],
        "match_relevance_types": [m.get("relevance_type") for m in matches],
        "match_scores": [m.get("score") for m in matches],
        "embedding_model": retrieval.get("embedding_model"),
        "embedding_used": retrieval.get("embedding_used"),
        "lexical_fallback": retrieval.get("lexical_fallback"),
        "query_instruct_applied": retrieval.get("query_instruct_applied"),
        "retrieval_method": retrieval.get("method"),
        "retrieval_candidates": retrieval.get("candidates") or [],
        "primary_effect": (payload.get("cognitive_impact") or {}).get("primary_effect")
        if isinstance(payload.get("cognitive_impact"), dict)
        else None,
        "scheduler_features": features,
        "delta_summary": delta.get("summary"),
        "claim_texts": [c.get("text") for c in (payload.get("claims") or [])],
        "observation_texts": [o.get("text") for o in (payload.get("observations") or [])],
        "inference_texts": [i.get("text") for i in (payload.get("inferences") or [])],
        "cognitive_impact": payload.get("cognitive_impact") or (payload.get("attention_plan") or {}).get("score_debug", {}).get("cognitive_impact"),
        "evidence_stage_skipped": payload.get("evidence_stage_skipped")
        if payload.get("evidence_stage_skipped") is not None
        else features.get("evidence_stage_skipped"),
        "evidence_skip_reason": payload.get("evidence_skip_reason")
        if payload.get("evidence_skip_reason") is not None
        else features.get("evidence_skip_reason"),
        "latency_ms": run.get("latency_ms"),
        "tokens": {"prompt": run.get("prompt_tokens"), "completion": run.get("completion_tokens")},
        "cost": run.get("estimated_cost_usd"),
        "source_id": payload.get("source_id"),
        "analysis_run_id": run.get("id"),
        **runtime,
    }


def _empty_eval_fields() -> dict[str, Any]:
    return {
        "disposition": None,
        "update": None,
        "delta_content": None,
        "match_scores": [],
        "embedding_used": None,
        "lexical_fallback": None,
        "query_instruct_applied": None,
        "retrieval_method": None,
        "retrieval_candidates": [],
        "primary_effect": None,
        "scheduler_features": None,
        "cognitive_impact": None,
        "evidence_stage_skipped": None,
        "evidence_skip_reason": None,
    }


def ensure_kernel_fixture(db, fixture: str | None) -> None:
    if fixture not in {None, "mvp"}:
        return
    from sqlalchemy import func, select

    from app.models.kernel import KernelNode
    from app.services.embeddings import refresh_node_embedding
    from app.testing.kernel_fixture import seed_mvp_kernel

    n = db.execute(select(func.count()).select_from(KernelNode).where(KernelNode.deleted_at.is_(None))).scalar_one()
    if n:
        return
    nodes = seed_mvp_kernel(db)
    for node in nodes.values():
        refresh_node_embedding(db, node)


def ingest_live_case_source(db, case: LiveCase):
    from app.services.ingestion import ingest_text, ingest_url

    text = case.source.text or ""
    if case.source.local_file:
        path = Path(case.source.local_file)
        if not path.is_file():
            path = ROOT / case.source.local_file
        text = path.read_text(encoding="utf-8")
    if text:
        source = ingest_text(db, text, title=case.source.title or case.id)
        meta = dict(source.raw_metadata or {})
        meta["live_eval_case_id"] = case.id
        source.raw_metadata = meta
        if case.source.type and case.source.type.upper() not in {"TEXT", "POST"}:
            source.source_type = case.source.type.upper()
        return source
    if case.source.url:
        return ingest_url(db, case.source.url)
    raise ValueError("empty source")


def run_live_pipeline(db, case: LiveCase) -> dict[str, Any]:
    """Reuse production ingest + run_pipeline. Do not reimplement an eval-only path."""
    from app.services.pipeline import run_pipeline

    ensure_kernel_fixture(db, case.kernel_fixture)
    source = ingest_live_case_source(db, case)
    db.flush()
    return run_pipeline(db, source.id, reprocess=True)


def load_manifest(path: Path) -> LiveManifest:
    raw = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("PyYAML is required to load YAML manifests. pip install pyyaml") from exc
        data = yaml.safe_load(raw) or {}
    else:
        data = json.loads(raw)
    return LiveManifest.model_validate(data)


def run_case(case: LiveCase, *, dry_run: bool, db=None) -> dict[str, Any]:
    status = gold_status_of(case)
    row: dict[str, Any] = {
        "id": case.id,
        "gold_status": status,
        "source_kind": case.source_kind,
        "cognitive_tasks": case.cognitive_tasks,
        "human_gold": dump_human_gold(case.human_gold),
        "dry_run": dry_run,
        "model": None,
        "provider_versions": None,
        "prompt_version": None,
        "embedding_model": None,
        "latency_ms": None,
        "tokens": None,
        "cost": None,
        "fallback": None,
        "fallback_stages": [],
        "model_stages": [],
        "prediction_source_by_stage": {},
        "prediction_source": None,
        "model_prediction": None,
        "scorable": None,
        "stage_provenance": None,
        "disposition": None,
        "kernel_matches": [],
        "matched_kernel_titles": [],
        "matched_kernel_ids": [],
        "match_relevance_types": [],
        "delta_summary": None,
        "claim_texts": [],
        "observation_texts": [],
        "inference_texts": [],
        "delta_rubric": (case.human_gold.delta_rubric if case.human_gold else None),
        "error": None,
        **_empty_eval_fields(),
    }
    if dry_run or not (case.source.text or case.source.local_file or case.source.url):
        row["skipped"] = True
        row["skip_reason"] = "dry-run or empty source (UNLABELED slot)"
        return row
    from app.config import settings
    from app.cognitive.versions import (
        EXTRACTOR_VERSION,
        MATCHER_VERSION,
        PIPELINE_VERSION,
        PROMPT_VERSION,
        PROVIDER_VERSION,
    )

    close = False
    if db is None:
        from app.db import SessionLocal

        db = SessionLocal()
        close = True
    try:
        print(f"live-eval case {case.id}", flush=True)
        payload = run_live_pipeline(db, case)
        if close:
            db.commit()
        row.update(analysis_payload_to_eval_row(payload))
        row.update(
            {
                "model": settings.llm_model,
                "provider_versions": {
                    "extractor": EXTRACTOR_VERSION,
                    "matcher": MATCHER_VERSION,
                    "provider": PROVIDER_VERSION,
                    "pipeline": PIPELINE_VERSION,
                },
                "prompt_version": PROMPT_VERSION,
                "skipped": False,
            }
        )
        if row.get("embedding_model") is None:
            row["embedding_model"] = settings.embedding_model
        return row
    except Exception as exc:
        if close:
            db.rollback()
        row["error"] = str(exc)[:4000]
        row["skipped"] = False
        return row
    finally:
        if close:
            db.close()


def write_report(out_dir: Path, summary: dict, rows: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    with (out_dir / "cases.jsonl").open("w", encoding="utf-8") as fh:
        for row in sorted(rows, key=lambda r: r["id"]):
            fh.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAOS Live Eval (real model; not CI)")
    parser.add_argument("--manifest", type=Path, default=ROOT / "eval" / "live" / "manifest.example.yaml")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--timestamp", default=None, help="Stable stamp for reproducible reports")
    parser.add_argument("--dry-run", action="store_true", help="Validate manifest and write a report without calling a model")
    args = parser.parse_args(argv)
    if not args.dry_run:
        from app.config import settings
        from app.db import Base, engine
        import app.models  # noqa: F401

        if settings.auto_create_tables:
            Base.metadata.create_all(bind=engine)
    manifest = load_manifest(args.manifest)
    stamp = args.timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_dir or (ROOT / "eval" / "live" / "results" / stamp)
    rows = [run_case(case, dry_run=args.dry_run) for case in manifest.cases]
    summary = compute_metrics(rows)
    summary["timestamp"] = stamp
    summary["manifest"] = str(args.manifest)
    summary["dry_run"] = args.dry_run
    summary["name"] = manifest.name
    write_report(out_dir, summary, rows)
    print(f"wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
