from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
STEP4 = ROOT / "eval/live/results/phase8c3_per_channel_attention_v0_1/phase8c3_per_channel_attention_v0.1_20260909T144907Z.json"
OUT_DIR = ROOT / "eval/live/results/phase8c3_article_attention_aggregation_v0_1"
RUN_VERSION = "phase8c3-article-attention-aggregation-v0.1"
ORDER = {"DROP": 0, "AWARE": 1, "WATCH": 2, "ENGAGE": 3}


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def aggregate(channels: list[dict]) -> tuple[str, list[dict]]:
    if not channels:
        return "DROP", []
    best_rank = max(ORDER.get(c.get("channel_attention"), 0) for c in channels)
    best = [c for c in channels if ORDER.get(c.get("channel_attention"), 0) == best_rank]
    disposition = next(k for k, v in ORDER.items() if v == best_rank)
    return disposition, best
def main() -> int:
    data = json.loads(STEP4.read_text(encoding="utf-8"))
    rows = []
    summary = {}
    for case in ("RS05", "RS15", "RS11", "RS12"):
        case_rows = []
        for run in [r for r in data["runs"] if r.get("case") == case]:
            article_attention, winning = aggregate(run.get("channels") or [])
            row = {
                "case": case,
                "repeat": run["repeat"],
                "article_attention": article_attention,
                "winning_channels": [
                    {k: c.get(k) for k in ("operation", "target", "change_magnitude", "epistemic_strength", "target_importance", "channel_attention")}
                    for c in winning
                ],
            }
            rows.append(row); case_rows.append(row)
        counts = Counter(r["article_attention"] for r in case_rows)
        summary[case] = {
            "n_runs": len(case_rows),
            "article_attention_counts": dict(counts),
            "stable": len(counts) <= 1,
        }
    output = {
        "run_version": RUN_VERSION,
        "status": "DEVELOPMENT_ARTICLE_AGGREGATION_ONLY",
        "measurement_sha": git_head(),
        "source_artifact": str(STEP4.relative_to(ROOT)),
        "source_artifact_sha256": hashlib.sha256(STEP4.read_bytes()).hexdigest(),
        "aggregation_order": ["ENGAGE", "WATCH", "AWARE", "DROP"],
        "summary": summary,
        "runs": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RESULT_PATH={path.relative_to(ROOT)}")
    print(f"RESULT_SHA256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
