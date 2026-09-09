from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()

from app.cognitive.client import chat_json
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.services.pipeline import run_pipeline
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _arm_summary, _base_world, _load_manifest
from eval.live.run_phase8c2_rs05_historical_downstream_stability_v0_1 import _load_hist4
from eval.live.run_phase8c2_rs15_event_projection_ablation_v0_1 import FrozenExtractionBridge, _hash_units, _make_extraction
from eval.live.run_phase8c2_rs15_fixed_sensor_auditor_stability_v0_1 import _load_fixed_sensor_units

RUN_VERSION = "phase8c3-temperature-stability-ab-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase8c3_temperature_stability_ab_v0_1"
CASES = ("RS15", "RS05")
TEMPERATURES = (0.1, 0.0)


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _temp_chat(temperature: float):
    def _chat(messages, **kwargs):
        return chat_json(
            messages,
            model=kwargs.get("model"),
            timeout=float(kwargs.get("timeout") or 45.0),
            thinking=kwargs.get("thinking"),
            reasoning_effort=kwargs.get("reasoning_effort"),
            temperature=temperature,
        )
    return _chat


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return update.get("operation"), update.get("target_fixture_code"), attention.get("disposition"), attention.get("expected_output")


def _frozen_units(case_id: str) -> tuple[list[dict[str, Any]], str]:
    if case_id == "RS15":
        units, artifact_sha = _load_fixed_sensor_units()
        return units, artifact_sha
    if case_id == "RS05":
        units, artifact_sha = _load_hist4()
        return units, artifact_sha
    raise KeyError(case_id)


def _run_once(case_id: str, case: dict[str, Any], units: list[dict[str, Any]], temperature: float, repeat: int) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(case_id, case)
    provider = ModelBackedCognitiveProvider(chat_fn=_temp_chat(temperature))
    extraction = _make_extraction(units, event_title=source.title or case_id)
    bridge = FrozenExtractionBridge(
        condition=f"{RUN_VERSION}:{case_id}:T={temperature}:r={repeat}",
        extraction=extraction,
        semantic_hash=_hash_units(units),
    )
    try:
        result = run_pipeline(
            db,
            source.id,
            provider=provider,
            extraction_bridge=bridge,
            reprocess=True,
            allow_watch_creation=False,
        )
        summary = _arm_summary(result, provider, code_by_id)
        return {"status": "OK", "error": None, "summary": summary}
    except Exception as exc:
        return {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)[:3000], "summary": None}
    finally:
        db.close()
        engine.dispose()


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for case_id in CASES:
        out[case_id] = {}
        for temperature in TEMPERATURES:
            items = [r for r in rows if r["case"] == case_id and r["temperature"] == temperature and r["status"] == "OK"]
            landings = [_landing(r["summary"]) for r in items]
            out[case_id][str(temperature)] = {
                "n_ok": len(items),
                "target_counts": dict(Counter(str(x[1] or "NONE") for x in landings)),
                "attention_counts": dict(Counter(str(x[2] or "NONE") for x in landings)),
                "landing_counts": dict(Counter(str(x) for x in landings)),
                "landings": [list(x) for x in landings],
            }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=6)
    args = parser.parse_args()
    manifest = _load_manifest()
    frozen = {case_id: _frozen_units(case_id) for case_id in CASES}
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for case_id in CASES:
            case = dict(manifest["cases"][case_id])
            units, artifact_sha = frozen[case_id]
            for temperature in TEMPERATURES:
                raw = _run_once(case_id, case, units, temperature, repeat)
                row = {"case": case_id, "repeat": repeat, "temperature": temperature, "semantic_sha256": _hash_units(units), "source_artifact_sha256": artifact_sha, **raw}
                rows.append(row)
                print(json.dumps({"case": case_id, "repeat": repeat, "temperature": temperature, "status": row["status"], "landing": list(_landing(row["summary"])) if row["summary"] else None}, ensure_ascii=False), flush=True)

    output = {"run_version": RUN_VERSION, "measurement_sha": git_head(), "status": "DEVELOPMENT_TEMPERATURE_AB_ONLY", "repeats": args.repeats, "temperatures": list(TEMPERATURES), "summary": _summarize(rows), "runs": rows,
              "guardrails": ["Sensor and Auditor are frozen; only Locate/Delta/Attention cognition is rerun.", "RS15 uses the exact fixed semantic realization from the prior causal attribution.", "RS05 uses the exact four Phase7A Auditor-admitted canonical units.", "Temperature is the only intended LLM sampling variable in this experiment."]}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={digest}")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
