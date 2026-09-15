from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (ROOT, BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

DEFAULT_DB_URL = f"sqlite:///{(BACKEND / 'raos.db').as_posix()}"
DEFAULT_PROXY = ROOT / "eval/live/results/phase10e_proxy_human_gold_v0_1/phase10e_proxy_human_gold_v0.1_20260915T193629Z.json"
DEFAULT_OUTPUT = ROOT / "eval/live/results/phase12b_residual_necessity_v0_1"


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 12B residual-necessity audit")
    parser.add_argument("--database-url", default=DEFAULT_DB_URL)
    parser.add_argument("--proxy-artifact", type=Path, default=DEFAULT_PROXY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    os.environ["RAOS_DATABASE_URL"] = args.database_url

    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models.scheduler import AttentionFeedback
    from eval.live.phase12b_residual_necessity_v0_1 import summarize_feedback

    with SessionLocal() as db:
        feedback = db.execute(select(AttentionFeedback).order_by(AttentionFeedback.created_at.asc())).scalars().all()
        feedback_summary = summarize_feedback(feedback)

    proxy = json.loads(args.proxy_artifact.read_text())
    proxy_metrics = dict(proxy.get("metrics") or {})
    proxy_clean = int(proxy_metrics.get("mismatches") or 0) == 0
    eligible = int(feedback_summary["personalization_eligible_rows"])
    # Count alone cannot establish a stable personal residual. Two explicit
    # corrections may still be unrelated cases, a shared Core issue, or a
    # misattribution. The deterministic audit can keep the identity baseline
    # or escalate to causal review; it may not auto-authorize calibration.
    calibration_justified = False
    if eligible == 0 and proxy_clean:
        conclusion = "NO_NON_IDENTITY_CALIBRATION_JUSTIFIED"
        phase12c = "SKIP"
    elif eligible <= 1:
        conclusion = "IDENTITY_RETAINED_PENDING_MORE_EVIDENCE"
        phase12c = "SKIP"
    else:
        conclusion = "REPEATED_ELIGIBLE_RESIDUAL_REQUIRES_CAUSAL_REVIEW"
        phase12c = "REVIEW"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = {
        "phase": "12B",
        "instrument": "residual-necessity-v0.1",
        "timestamp_utc": timestamp,
        "git_sha": git_sha(),
        "database_url": args.database_url,
        "feedback": feedback_summary,
        "proxy_operating_regime": {
            "artifact": str(args.proxy_artifact.relative_to(ROOT)),
            "label_author": proxy.get("label_author"),
            "n": proxy_metrics.get("n"),
            "exact": proxy_metrics.get("exact"),
            "mismatches": proxy_metrics.get("mismatches"),
            "used_as_personalization_training_gold": False,
        },
        "decision": {
            "non_identity_calibration_justified": calibration_justified,
            "theta_u": "IDENTITY" if phase12c == "SKIP" else "UNRESOLVED_REVIEW",
            "phase12c": phase12c,
            "conclusion": conclusion,
        },
        "guardrails": [
            "No LLM/provider calls.",
            "No feedback synthesis.",
            "Assistant-proxy Gold cannot itself authorize personalization.",
            "Absence of evidence is interpreted as no justification for extra model capacity, not proof that future residuals cannot exist.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    path = args.output_root / f"phase12b_residual_necessity_v0.1_{timestamp}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out["feedback"], ensure_ascii=False, indent=2))
    print(json.dumps(out["decision"], ensure_ascii=False, indent=2))
    print(f"artifact={path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
