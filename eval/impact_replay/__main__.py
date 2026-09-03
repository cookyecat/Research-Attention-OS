"""CLI: Cognitive Impact Replay / Attribution Harness v0.1.

Examples:

  python -m eval.impact_replay --run-id <analysis_run_uuid>
  python -m eval.impact_replay --run-id <uuid> --twice
  python -m eval.impact_replay --run-id <uuid> --ab \\
      --provider-a rule --provider-b rule --thinking-b enabled
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db import SessionLocal  # noqa: E402
from app.services.impact_replay import (  # noqa: E402
    ImpactReplayConfig,
    compare_replays,
    replay_analysis_run,
)


def _config(ns, side: str | None = None) -> ImpactReplayConfig:
    prefix = f"{side}_" if side else ""
    timeout = getattr(ns, f"{prefix}timeout", None)
    return ImpactReplayConfig(
        provider=getattr(ns, f"{prefix}provider", None),
        model=getattr(ns, f"{prefix}model", None),
        thinking=getattr(ns, f"{prefix}thinking", None),
        reasoning_effort=getattr(ns, f"{prefix}reasoning_effort", None),
        timeout=float(timeout) if timeout is not None else None,
        label=getattr(ns, f"{prefix}label", None) or side,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay Cognitive Impact on a frozen AnalysisRun")
    parser.add_argument("--run-id", required=True, help="Completed AnalysisRun UUID")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--thinking", default=None)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--twice", action="store_true", help="Run twice and assert stage reproducibility")
    parser.add_argument("--ab", action="store_true", help="Controlled A/B with two Impact configs")
    parser.add_argument("--provider-a", default=None)
    parser.add_argument("--provider-b", default=None)
    parser.add_argument("--model-a", default=None)
    parser.add_argument("--model-b", default=None)
    parser.add_argument("--thinking-a", default=None)
    parser.add_argument("--thinking-b", default=None)
    parser.add_argument("--reasoning-effort-a", default=None)
    parser.add_argument("--reasoning-effort-b", default=None)
    parser.add_argument("--timeout-a", type=float, default=None)
    parser.add_argument("--timeout-b", type=float, default=None)
    parser.add_argument("--out", default=None, help="Optional JSON output path")
    args = parser.parse_args(argv)

    run_id = UUID(args.run_id)
    db = SessionLocal()
    try:
        if args.ab:
            a_cfg = ImpactReplayConfig(
                provider=args.provider_a or args.provider,
                model=args.model_a or args.model,
                thinking=args.thinking_a or args.thinking,
                reasoning_effort=args.reasoning_effort_a,
                timeout=args.timeout_a if args.timeout_a is not None else args.timeout,
                label=args.label or "a",
            )
            b_cfg = ImpactReplayConfig(
                provider=args.provider_b or args.provider,
                model=args.model_b,
                thinking=args.thinking_b,
                reasoning_effort=args.reasoning_effort_b,
                timeout=args.timeout_b,
                label="b",
            )
            a = replay_analysis_run(db, run_id, config=a_cfg, persist=True)
            b = replay_analysis_run(db, run_id, config=b_cfg, persist=True)
            db.commit()
            payload = {"a": a, "b": b, "comparison": compare_replays(a, b)}
        elif args.twice:
            cfg = _config(args)
            first = replay_analysis_run(db, run_id, config=cfg, persist=True)
            second = replay_analysis_run(db, run_id, config=cfg, persist=True)
            db.commit()
            same = first["stages"] == second["stages"] and first["input_fingerprint"] == second["input_fingerprint"]
            payload = {
                "first": first,
                "second": second,
                "reproducible": same,
                "comparison": compare_replays(first, second),
            }
            if not same:
                print("Replay stages diverged on identical frozen input", file=sys.stderr)
                print(json.dumps(payload, indent=2, default=str))
                return 1
        else:
            payload = replay_analysis_run(db, run_id, config=_config(args), persist=True)
            db.commit()
        text = json.dumps(payload, indent=2, default=str)
        print(text)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
