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
DEFAULT_OUTPUT_ROOT = ROOT / "eval/live/results/phase10e_core_validity_v0_1"


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 10E deterministic Attention-Core validity gate")
    parser.add_argument("--database-url", default=DEFAULT_DB_URL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--include-rows", action="store_true", help="Include per-run audit rows in the JSON artifact")
    return parser.parse_args()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    args = _args()
    os.environ["RAOS_DATABASE_URL"] = args.database_url

    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models.analysis import AnalysisRun
    from eval.live.phase10e_core_validity_v0_1 import (
        CURRENT_STRATEGY_ID,
        CURRENT_STRATEGY_VERSION,
        audit_payload,
        strategy_snapshot_from_payload,
    )

    rows: list[dict] = []
    skipped: list[dict] = []
    completed_count = 0
    with SessionLocal() as db:
        runs = db.execute(
            select(AnalysisRun).where(AnalysisRun.status == "COMPLETED").order_by(AnalysisRun.created_at.asc())
        ).scalars().all()
        completed_count = len(runs)
        for run in runs:
            payload = dict(run.result_payload or {})
            snapshot = strategy_snapshot_from_payload(payload)
            if not isinstance(snapshot, dict):
                skipped.append({"run_id": str(run.id), "reason": "missing_strategy_snapshot"})
                continue
            if (
                snapshot.get("strategy_id") != CURRENT_STRATEGY_ID
                or snapshot.get("version") != CURRENT_STRATEGY_VERSION
            ):
                skipped.append(
                    {
                        "run_id": str(run.id),
                        "reason": "non_current_strategy",
                        "strategy_id": snapshot.get("strategy_id"),
                        "version": snapshot.get("version"),
                    }
                )
                continue
            try:
                row = audit_payload(payload)
            except Exception as exc:
                rows.append({"run_id": str(run.id), "audit_error": f"{type(exc).__name__}: {exc}"})
                continue
            row["run_id"] = row.get("run_id") or str(run.id)
            row["created_at"] = run.created_at.isoformat() if run.created_at else None
            rows.append(row)

    eligible = len(rows)
    audit_errors = [r for r in rows if r.get("audit_error")]
    valid_rows = [r for r in rows if not r.get("audit_error")]
    disposition_parity = sum(bool(r.get("disposition_parity")) for r in valid_rows)
    strategy_parity = sum(bool(r.get("strategy_identity_parity")) for r in valid_rows)
    cause_parity = sum(bool(r.get("decision_cause_parity")) for r in valid_rows)
    nonempty = [r for r in valid_rows if int(r.get("admitted_effect_count") or 0) > 0]
    observed_disposition_diffs = [
        r for r in nonempty if r.get("pareto_vs_all_join_disposition_parity") is False
    ]
    observed_cause_diffs = [r for r in nonempty if r.get("pareto_vs_all_join_cause_parity") is False]

    replay_pass = (
        eligible > 0
        and not audit_errors
        and disposition_parity == eligible
        and strategy_parity == eligible
        and cause_parity == eligible
    )
    main_regime_coherence_pass = len(observed_disposition_diffs) == 0
    gate_pass = replay_pass and main_regime_coherence_pass

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = {
        "phase": "10E",
        "instrument": "core-validity-gate-v0.1",
        "timestamp_utc": timestamp,
        "git_sha": _git_sha(),
        "database": {
            "url": args.database_url,
            "completed_analysis_runs": completed_count,
        },
        "frozen_strategy": {
            "strategy_id": CURRENT_STRATEGY_ID,
            "version": CURRENT_STRATEGY_VERSION,
        },
        "guardrails": [
            "No LLM/provider calls.",
            "No production writes.",
            "Replay requires an explicit stored decision-strategy id and version.",
            "Synthetic corner cases are not a hard gate; observed reachable states define the current operating-regime check.",
        ],
        "metrics": {
            "eligible_current_strategy_runs": eligible,
            "audit_errors": len(audit_errors),
            "exact_disposition_replay": disposition_parity,
            "exact_strategy_identity_replay": strategy_parity,
            "exact_decision_cause_replay": cause_parity,
            "observed_nonempty_effect_runs": len(nonempty),
            "observed_pareto_vs_all_join_disposition_diffs": len(observed_disposition_diffs),
            "observed_pareto_vs_all_join_cause_diffs": len(observed_cause_diffs),
            "skipped_noncurrent_or_unversioned_runs": len(skipped),
        },
        "gates": {
            "deterministic_replay_parity": "PASS" if replay_pass else "FAIL",
            "observed_main_regime_policy_coherence": "PASS" if main_regime_coherence_pass else "FAIL",
            "phase10e_deterministic_integrity": "PASS" if gate_pass else "FAIL",
        },
        "observed_disposition_differences": observed_disposition_diffs,
        "observed_cause_differences": observed_cause_diffs,
        "audit_errors": audit_errors,
        "skipped_summary": {
            "count": len(skipped),
            "reasons": {reason: sum(1 for row in skipped if row["reason"] == reason) for reason in sorted({row["reason"] for row in skipped})},
        },
    }
    if args.include_rows:
        output["rows"] = rows
        output["skipped"] = skipped

    args.output_root.mkdir(parents=True, exist_ok=True)
    out_path = args.output_root / f"phase10e_core_validity_v0.1_{timestamp}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(output["metrics"], indent=2))
    print(json.dumps(output["gates"], indent=2))
    print(f"artifact={out_path.relative_to(ROOT)}")
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
