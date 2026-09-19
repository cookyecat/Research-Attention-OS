from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.models.event import RepresentationAuditRun
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.representation_auditor import REPRESENTATION_AUDITOR_CONTRACT
from app.services.representation_authority import (
    AUTHORITY_POLICY_VERSION,
    simulate_representation_authority,
)


def _resolve_frame(db, spec: dict):
    source_id = UUID(spec["source_id"])
    wanted = spec.get("event_key")
    rows = latest_event_evidence_frames_for_source(db, source_id)
    matches = [row for row in rows if (row.frame_payload or {}).get("event_key") == wanted]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one frame for source={source_id} event_key={wanted}; found {len(matches)}"
        )
    return matches[0]


def _latest_audit(db, frame_a_id: UUID, frame_b_id: UUID) -> RepresentationAuditRun:
    row = db.execute(
        select(RepresentationAuditRun)
        .where(
            RepresentationAuditRun.audit_type == "FRAME_PAIR",
            RepresentationAuditRun.auditor_contract_version == REPRESENTATION_AUDITOR_CONTRACT,
            or_(
                (
                    (RepresentationAuditRun.subject_id == frame_a_id)
                    & (RepresentationAuditRun.object_id == frame_b_id)
                ),
                (
                    (RepresentationAuditRun.subject_id == frame_b_id)
                    & (RepresentationAuditRun.object_id == frame_a_id)
                ),
            ),
        )
        .order_by(RepresentationAuditRun.created_at.desc(), RepresentationAuditRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise RuntimeError(f"no {REPRESENTATION_AUDITOR_CONTRACT} audit for {frame_a_id} ↔ {frame_b_id}")
    return row


def run(corpus_path: Path) -> dict:
    corpus = json.loads(corpus_path.read_text())
    results = []
    dimension_outcomes = Counter()
    with SessionLocal() as db:
        for case in corpus["cases"]:
            frame_a = _resolve_frame(db, case["a"])
            frame_b = _resolve_frame(db, case["b"])
            audit = _latest_audit(db, frame_a.id, frame_b.id)
            simulation = simulate_representation_authority(audit)
            for dimension, outcome in (simulation.get("outcomes") or {}).items():
                dimension_outcomes[f"{dimension}:{outcome.get('outcome')}"] += 1
            results.append(
                {
                    "name": case["name"],
                    "category": case["category"],
                    "audit_run_id": str(audit.id),
                    "auditor_contract": audit.auditor_contract_version,
                    "audit_judgments": {
                        key: (value or {}).get("value")
                        for key, value in (audit.judgments or {}).items()
                    },
                    "simulation": simulation,
                }
            )
    return {
        "corpus_version": corpus["corpus_version"],
        "auditor_contract": REPRESENTATION_AUDITOR_CONTRACT,
        "authority_policy": AUTHORITY_POLICY_VERSION,
        "n_cases": len(results),
        "dimension_outcome_counts": dict(sorted(dimension_outcomes.items())),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "eval" / "fixtures" / "representation_auditor_v0_1_cases.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.corpus)
    body = json.dumps(report, ensure_ascii=False, indent=2)
    print(body)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n")


if __name__ == "__main__":
    main()
