from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.run_standing_radar_fit_eval import load_repo_env
load_repo_env()
from eval.live.run_phase8c2_production_sensor_bridge_ab_v0_1 import _base_world, _load_manifest

RUN_VERSION = "phase8c3-multi-delta-analysis-v0.1"
SOURCE = ROOT / "eval/live/results/phase8c3_native_interface_probe_v0_1/phase8c3_native_interface_probe_v0.1_20260909T135412Z.json"
SOURCE_SHA256 = "3f68c034b55fd8a132c282027f87fe3665a388ed94e8be2e653bfba6aaf55d9e"
OUT_DIR = ROOT / "eval/live/results/phase8c3_multi_delta_analysis_v0_1"
CASES = ("RS05", "RS15", "RS11", "RS12")

def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _code_map(case_id: str, case: dict) -> dict[str, str]:
    engine, db, _source, code_by_id = _base_world(case_id, case)
    try:
        return {str(k): str(v) for k, v in code_by_id.items()}
    finally:
        db.close(); engine.dispose()


def _signature(effect: dict, code_map: dict[str, str]) -> tuple[str, str]:
    op = str(effect.get("operation") or "NONE")
    raw = effect.get("target")
    if raw is None:
        return op, "OPEN_NEW"
    return op, code_map.get(str(raw), str(raw))


def _utility(effect: dict) -> float:
    return float(effect.get("change_magnitude") or 0.0) * float(effect.get("target_importance") or 0.0)

def _case_summary(case_id: str, runs: list[dict], code_map: dict[str, str]) -> dict:
    ok = [r for r in runs if r.get("case") == case_id and r.get("status") == "OK"]
    frequency: Counter = Counter()
    utilities: dict[tuple[str, str], list[float]] = defaultdict(list)
    per_repeat = []
    for row in ok:
        seen = set()
        effects_out = []
        for effect in row.get("effects") or []:
            sig = _signature(effect, code_map)
            seen.add(sig)
            utilities[sig].append(_utility(effect))
            effects_out.append({"operation": sig[0], "target": sig[1], "utility": _utility(effect),
                                "change_magnitude": effect.get("change_magnitude"),
                                "epistemic_strength": effect.get("epistemic_strength"),
                                "target_importance": effect.get("target_importance")})
        for sig in seen:
            frequency[sig] += 1
        per_repeat.append({"repeat": row.get("repeat"), "effects": effects_out})
    n = len(ok)
    stats = []
    for sig, count in sorted(frequency.items()):
        vals = utilities[sig]
        stats.append({"operation": sig[0], "target": sig[1], "repeat_frequency": count,
                      "repeat_fraction": count / n if n else 0.0,
                      "utility_min": min(vals) if vals else 0.0,
                      "utility_max": max(vals) if vals else 0.0,
                      "utility_mean": statistics.fmean(vals) if vals else 0.0})
    return {"n_ok": n, "core_effects": [x for x in stats if x["repeat_frequency"] == n],
            "optional_effects": [x for x in stats if x["repeat_frequency"] != n],
            "all_effect_stats": stats, "per_repeat": per_repeat}

def main() -> int:
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise RuntimeError(f"source artifact SHA mismatch: {digest}")
    data = json.loads(raw)
    manifest = _load_manifest()
    summary = {}
    for case_id in CASES:
        code_map = _code_map(case_id, dict(manifest["cases"][case_id]))
        summary[case_id] = _case_summary(case_id, list(data.get("runs") or []), code_map)
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_MULTI_DELTA_ANALYSIS_ONLY",
        "measurement_sha": git_head(),
        "source_artifact": str(SOURCE.relative_to(ROOT)),
        "source_artifact_sha256": digest,
        "summary": summary,
        "guardrails": [
            "No new LLM calls are made; this is a deterministic analysis of the frozen Step-2 artifact.",
            "No primary effect is selected.",
            "Core means the same operation-target channel appears in every valid repeat; it does not mean objective truth.",
            "Utility=change_magnitude*target_importance is diagnostic only in Step 3; no attention threshold is applied yet.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
