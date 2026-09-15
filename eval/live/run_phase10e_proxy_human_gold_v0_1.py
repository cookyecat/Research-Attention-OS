from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

DEFAULT_MANIFEST = ROOT / "eval/live/manifest.phase10e_proxy_human_gold.v0_1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "eval/live/results/phase10e_proxy_human_gold_v0_1"


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 10E operating-regime proxy Human-Gold gate")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    from eval.live.phase10e_proxy_human_gold_v0_1 import evaluate_case, load_manifest

    manifest = load_manifest(args.manifest)
    rows = [evaluate_case(case, i) for i, case in enumerate(manifest["cases"])]
    n = len(rows)
    hits = sum(bool(r["exact_hit"]) for r in rows)
    mismatches = [r for r in rows if not r["exact_hit"]]
    by_regime = {}
    for regime in sorted({r["regime"] for r in rows}):
        rr = [r for r in rows if r["regime"] == regime]
        by_regime[regime] = {"n": len(rr), "exact": sum(bool(x["exact_hit"]) for x in rr)}
    gate = "PASS" if n > 0 and hits == n else "REVIEW"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = {
        "phase": "10E",
        "instrument": "proxy-human-gold-v0.1",
        "timestamp_utc": timestamp,
        "git_sha": git_sha(),
        "manifest": str(args.manifest.relative_to(ROOT)),
        "label_author": manifest.get("label_author"),
        "delegation_note": manifest.get("delegation_note"),
        "guardrails": [
            "Proxy labels were frozen and committed before this measurement.",
            "No LLM/provider call is made by this instrument.",
            "No production state is written.",
            "Proxy Gold can provisionally validate the common operating regime but cannot by itself justify a Core-changing variable.",
        ],
        "metrics": {"n": n, "exact": hits, "exact_rate": hits / n if n else None, "mismatches": len(mismatches)},
        "by_regime": by_regime,
        "gate": {"operating_regime_proxy_adequacy": gate},
        "mismatches": mismatches,
        "rows": rows,
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    out = args.output_root / f"phase10e_proxy_human_gold_v0.1_{timestamp}.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2, default=str) + "\n")
    print(json.dumps(output["metrics"], indent=2))
    print(json.dumps(output["by_regime"], indent=2))
    print(json.dumps(output["gate"], indent=2))
    print(f"artifact={out.relative_to(ROOT)}")
    return 0 if gate == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
