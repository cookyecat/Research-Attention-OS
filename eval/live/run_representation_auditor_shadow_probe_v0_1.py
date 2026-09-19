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

from app.db import SessionLocal
from app.services.representation_auditor import (
    REPRESENTATION_AUDITOR_CONTRACT,
    audit_frame_pair_shadow,
)
from app.services.same_event_candidates import same_event_frame_candidates

DEFAULT_SOURCE_IDS = [
    "7b14458f-6123-4fbe-9c4b-52415e850fee",
    "bf74b466-ecc9-4226-8247-a27260fbf69f",
    "1fbc440f-9cc3-4417-8f30-d0146491fd3e",
    "c858cff2-f5f2-468a-9aef-9fb6ff2add1b",
    "f4af7d30-805d-44f7-b47b-31ec5394a553",
]


def run(max_cases: int) -> dict:
    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    with SessionLocal() as db:
        for source_id in DEFAULT_SOURCE_IDS:
            candidates = same_event_frame_candidates(
                db,
                UUID(source_id),
                source_limit=8,
                max_pairs=40,
                include_intra_source=True,
            )
            intra = [row for row in candidates["pairs"] if row["candidate_kind"] == "INTRA_SOURCE_FRAME_PAIR"]
            cross = [row for row in candidates["pairs"] if row["candidate_kind"] == "CROSS_SOURCE_FRAME_PAIR"]
            for row in [*intra[:2], *cross[:3]]:
                key = tuple(sorted((row["frame_id_a"], row["frame_id_b"])))
                if key in seen:
                    continue
                seen.add(key)
                selected.append(row)
                if len(selected) >= max_cases:
                    break
            if len(selected) >= max_cases:
                break

        results = []
        for index, row in enumerate(selected):
            try:
                audit, trace = audit_frame_pair_shadow(
                    db,
                    UUID(row["frame_id_a"]),
                    UUID(row["frame_id_b"]),
                    run_tag=f"d4-probe-v0.1-{index:02d}",
                )
                actual = {
                    "event_identity": audit.judgments["event_identity"]["value"],
                    "provenance_dependency": audit.judgments["provenance_dependency"]["value"],
                    "relation_context": audit.judgments["relation_context"]["value"],
                }
                results.append(
                    {
                        "index": index,
                        "status": "OK",
                        "candidate_kind": row["candidate_kind"],
                        "frame_id_a": row["frame_id_a"],
                        "frame_id_b": row["frame_id_b"],
                        "source_id_a": row["source_id_a"],
                        "source_id_b": row["source_id_b"],
                        "source_rank": row["source_rank"],
                        "source_retrieval_score": row["source_retrieval_score"],
                        "frame_similarity": row["frame_similarity"],
                        "audit_run_id": str(audit.id),
                        "reused": bool(trace.get("reused")),
                        "actual": actual,
                        "event_support_ids": audit.judgments["event_identity"].get("support_ids") or [],
                        "provenance_support_ids": audit.judgments["provenance_dependency"].get("support_ids") or [],
                        "context_support_ids": audit.judgments["relation_context"].get("support_ids") or [],
                        "frame_summary_a": row.get("frame_summary_a"),
                        "frame_summary_b": row.get("frame_summary_b"),
                    }
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                results.append(
                    {
                        "index": index,
                        "status": "FAIL",
                        "candidate_kind": row["candidate_kind"],
                        "frame_id_a": row["frame_id_a"],
                        "frame_id_b": row["frame_id_b"],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "frame_summary_a": row.get("frame_summary_a"),
                        "frame_summary_b": row.get("frame_summary_b"),
                    }
                )

    ok = [row for row in results if row["status"] == "OK"]
    return {
        "probe_version": "representation-auditor-shadow-probe-v0.1",
        "auditor_contract": REPRESENTATION_AUDITOR_CONTRACT,
        "n_selected": len(results),
        "n_ok": len(ok),
        "n_fail": len(results) - len(ok),
        "event_identity_distribution": dict(Counter(row["actual"]["event_identity"] for row in ok)),
        "provenance_distribution": dict(Counter(row["actual"]["provenance_dependency"] for row in ok)),
        "relation_context_distribution": dict(Counter(row["actual"]["relation_context"] for row in ok)),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(max(1, min(args.max_cases, 50)))
    body = json.dumps(report, ensure_ascii=False, indent=2)
    print(body)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n")


if __name__ == "__main__":
    main()
