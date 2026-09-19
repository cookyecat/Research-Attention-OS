from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.db import SessionLocal
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.representation_auditor import (
    REPRESENTATION_AUDITOR_CONTRACT,
    audit_frame_pair_shadow,
)


def _resolve_frame(db, spec: dict):
    source_id = UUID(spec["source_id"])
    frames = latest_event_evidence_frames_for_source(db, source_id)
    wanted = spec.get("event_key")
    matches = [f for f in frames if (f.frame_payload or {}).get("event_key") == wanted]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one frame for source={source_id} event_key={wanted}; found {len(matches)}"
        )
    return matches[0]


def run(corpus_path: Path) -> dict:
    corpus = json.loads(corpus_path.read_text())
    results = []
    with SessionLocal() as db:
        for case in corpus["cases"]:
            frame_a = _resolve_frame(db, case["a"])
            frame_b = _resolve_frame(db, case["b"])
            audit, trace = audit_frame_pair_shadow(
                db,
                frame_a.id,
                frame_b.id,
                run_tag=f"d4-seed-v0.1-{case['name']}",
            )
            actual = {
                "event_identity": audit.judgments["event_identity"]["value"],
                "provenance_dependency": audit.judgments["provenance_dependency"]["value"],
                "relation_context": audit.judgments["relation_context"]["value"],
            }
            expected = case["expected"]
            passed = actual == expected
            results.append(
                {
                    "name": case["name"],
                    "category": case["category"],
                    "frame_a_id": str(frame_a.id),
                    "frame_b_id": str(frame_b.id),
                    "audit_run_id": str(audit.id),
                    "reused": bool(trace.get("reused")),
                    "expected": expected,
                    "actual": actual,
                    "pass": passed,
                }
            )
            db.commit()

    return {
        "corpus_version": corpus["corpus_version"],
        "auditor_contract": REPRESENTATION_AUDITOR_CONTRACT,
        "n_cases": len(results),
        "n_pass": sum(1 for row in results if row["pass"]),
        "n_fail": sum(1 for row in results if not row["pass"]),
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
