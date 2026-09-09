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
from app.cognitive.factory import get_provider
from app.services.pipeline import run_pipeline
from eval.live.phase8c2_production_sensor_bridge_v0_1 import SemanticSensorProductionBridgeV0_1
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _arm_summary, _base_world, _load_manifest
OUT_DIR = ROOT / "eval/live/results/phase8c2_rs15_sensor_model_ablation_v0_1"
RUN_VERSION = "phase8c2-rs15-sensor-model-ablation-v0.1"
SOURCE_ID = "RS15"
SENSOR_MODELS = ("deepseek-v4-pro", "deepseek-v4-flash")
AUDITOR_MODEL = "deepseek-v4-flash"


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _forced_chat(model_name: str):
    def _chat(messages, **kwargs):
        return chat_json(
            messages,
            model=model_name,
            timeout=float(kwargs.get("timeout") or 45.0),
            thinking=kwargs.get("thinking"),
            reasoning_effort=kwargs.get("reasoning_effort"),
        )
    return _chat


class ModelPinnedBridge(SemanticSensorProductionBridgeV0_1):
    def __init__(self, sensor_model: str):
        self.sensor_model = sensor_model
        super().__init__(sensor_chat_fn=_forced_chat(sensor_model), auditor_chat_fn=_forced_chat(AUDITOR_MODEL))
    def execution_snapshot(self) -> dict[str, Any]:
        snapshot = dict(super().execution_snapshot())
        snapshot["sensor_model_override"] = self.sensor_model
        snapshot["auditor_model_override"] = AUDITOR_MODEL
        snapshot["ablation_run_version"] = RUN_VERSION
        return snapshot


def _landing(row: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    update = row.get("update") or {}
    attention = row.get("attention") or {}
    return (
        update.get("operation"),
        update.get("target_fixture_code"),
        attention.get("disposition"),
        attention.get("expected_output"),
    )


def _match_scores(row: dict[str, Any]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for match in row.get("matches") or []:
        code = match.get("fixture_code")
        if code in {"Q2", "B2"}:
            scores[str(code)] = float(match.get("score") or 0.0)
    return scores

def _run_arm(case: dict[str, Any], *, sensor_model: str, repeat: int) -> dict[str, Any]:
    engine, db, source, code_by_id = _base_world(SOURCE_ID, case)
    provider = get_provider()
    bridge = ModelPinnedBridge(sensor_model)
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
        summary.update({
            "sensor_model": sensor_model,
            "auditor_model": AUDITOR_MODEL,
            "repeat": repeat,
            "status": "OK",
            "error": None,
        })
        return summary
    except Exception as exc:
        return {
            "sensor_model": sensor_model,
            "auditor_model": AUDITOR_MODEL,
            "repeat": repeat,
            "status": "ERROR",
            "error_type": type(exc).__name__,
            "error": str(exc)[:3000],
        }
    finally:
        db.close()
        engine.dispose()

def _compact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sensor_model": row.get("sensor_model"),
        "repeat": row.get("repeat"),
        "status": row.get("status"),
        "landing": list(_landing(row)) if row.get("status") == "OK" else None,
        "q2_b2_scores": _match_scores(row) if row.get("status") == "OK" else {},
        "n_claims": row.get("n_claims"),
        "delta_content": row.get("delta_content"),
        "error": row.get("error"),
    }


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for model in SENSOR_MODELS:
        items = [r for r in rows if r.get("sensor_model") == model]
        ok = [r for r in items if r.get("status") == "OK"]
        targets = [((r.get("update") or {}).get("target_fixture_code")) for r in ok]
        out[model] = {
            "n_runs": len(items),
            "n_ok": len(ok),
            "target_counts": dict(Counter(str(x) for x in targets)),
            "landings": [list(_landing(r)) for r in ok],
            "q2_b2_scores": [_match_scores(r) for r in ok],
            "claim_counts": [r.get("n_claims") for r in ok],
        }
    return out

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be >= 1")

    case = dict(_load_manifest()["cases"][SOURCE_ID])
    measurement_sha = git_head()
    rows: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for sensor_model in SENSOR_MODELS:
            row = _run_arm(case, sensor_model=sensor_model, repeat=repeat)
            rows.append(row)
            print(json.dumps(_compact(row), ensure_ascii=False), flush=True)

    summary = _summarize(rows)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_CAUSAL_ATTRIBUTION_ONLY",
        "measurement_sha": measurement_sha,
        "source_id": SOURCE_ID,
        "kernel_fixture": case["kernel_fixture"],
        "controlled_variable": "Semantic Sensor model only",
        "sensor_models": list(SENSOR_MODELS),
        "auditor_model": AUDITOR_MODEL,
        "repeats": args.repeats,
        "summary": summary,
        "runs": rows,
    }
    output["interpretation_guardrails"] = [
        "Both arms use the same raw RS15 source and current production source packaging.",
        "Both arms use Semantic Sensor v0.2.6 with the same prompt and settings except the requested Sensor model.",
        "Both arms force Auditor v0.1.1 through deepseek-v4-flash.",
        "Both arms use the same current production Locate/Delta/Attention downstream.",
        "No production default, Sensor prompt, Auditor prompt, Delta, or Attention Policy code is modified.",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"RESULT_PATH={path.relative_to(ROOT)}", flush=True)
    print(f"RESULT_SHA256={digest}", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
