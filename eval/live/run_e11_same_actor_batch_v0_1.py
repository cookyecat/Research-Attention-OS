from __future__ import annotations

import argparse
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
import json
from pathlib import Path
import re
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import select

from app.db import SessionLocal
from app.models.event import EventEvidenceFrame
from app.services.event_evidence_frames import latest_event_evidence_frames_for_source
from app.services.representation_auditor import audit_frame_pair_shadow, REPRESENTATION_AUDITOR_CONTRACT
from app.services.representation_authority import _norm


TARGET_ACTORS = {
    "openai": 4,
    "jev": 4,
    "microsoft": 3,
    "anthropic": 3,
    "apple": 2,
    "valve": 2,
    "google": 2,
}


def _summary(frame: EventEvidenceFrame) -> str:
    return str((frame.frame_payload or {}).get("event_summary") or "").strip()


def _actor_names(frame: EventEvidenceFrame) -> set[str]:
    return {
        _norm(row.get("name"))
        for row in (frame.frame_payload or {}).get("actors") or []
        if isinstance(row, dict) and _norm(row.get("name"))
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]{1,6}", (text or "").lower()))


def _similarity(a: str, b: str) -> float:
    seq = SequenceMatcher(None, a.lower(), b.lower()).ratio()
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return round(max(seq, jac), 4)


def _latest_frames(db) -> list[EventEvidenceFrame]:
    all_rows = db.execute(select(EventEvidenceFrame)).scalars().all()
    latest: list[EventEvidenceFrame] = []
    for source_id in sorted({row.source_id for row in all_rows}, key=str):
        latest.extend(latest_event_evidence_frames_for_source(db, source_id))
    return latest


def select_batch(db) -> list[dict]:
    by_actor: dict[str, list[EventEvidenceFrame]] = defaultdict(list)
    for frame in _latest_frames(db):
        for actor in _actor_names(frame):
            if actor in TARGET_ACTORS:
                by_actor[actor].append(frame)

    selected: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for actor, quota in TARGET_ACTORS.items():
        candidates = []
        for a, b in combinations(by_actor.get(actor, []), 2):
            if a.source_id == b.source_id:
                continue
            key = tuple(sorted((str(a.id), str(b.id))))
            if key in seen:
                continue
            candidates.append(
                {
                    "actor": actor,
                    "frame_id_a": str(a.id),
                    "frame_id_b": str(b.id),
                    "source_id_a": str(a.source_id),
                    "source_id_b": str(b.source_id),
                    "summary_a": _summary(a),
                    "summary_b": _summary(b),
                    "summary_similarity": _similarity(_summary(a), _summary(b)),
                }
            )
        # Lowest-similarity exact-actor pairs are the strongest hard-negative probe.
        candidates.sort(key=lambda row: (row["summary_similarity"], row["frame_id_a"], row["frame_id_b"]))
        for row in candidates[:quota]:
            seen.add(tuple(sorted((row["frame_id_a"], row["frame_id_b"]))))
            selected.append(row)
    return selected


def run(*, audit: bool) -> dict:
    with SessionLocal() as db:
        batch = select_batch(db)
        results = []
        for index, row in enumerate(batch):
            out = dict(row)
            if audit:
                audit_row, trace = audit_frame_pair_shadow(
                    db,
                    UUID(row["frame_id_a"]),
                    UUID(row["frame_id_b"]),
                    run_tag=f"e11-same-actor-v0.1-{index:02d}",
                )
                out["audit_run_id"] = str(audit_row.id)
                out["reused"] = bool(trace.get("reused"))
                out["judgments"] = {
                    key: {
                        "value": value.get("value"),
                        "direction": value.get("direction"),
                    }
                    for key, value in (audit_row.judgments or {}).items()
                }
                db.commit()
            results.append(out)
    return {
        "study": "e11-same-actor-bounded-batch-v0.1",
        "auditor_contract": REPRESENTATION_AUDITOR_CONTRACT,
        "selection_rule": "exact shared actor; cross-source; lowest summary similarity per actor; fixed quotas",
        "max_cases": sum(TARGET_ACTORS.values()),
        "n_cases": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(audit=args.audit)
    body = json.dumps(report, ensure_ascii=False, indent=2)
    print(body)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n")


if __name__ == "__main__":
    main()
