from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for path in (str(ROOT), str(BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.db import Base
from app.services.event_evidence_frames import _persist_payload
from app.services.ingestion import ingest_text
from app.services.representation_auditor import (
    REPRESENTATION_AUDITOR_CONTRACT,
    audit_frame_pair_shadow,
)
from app.services.representation_belief import (
    BASE_RATE_SAME,
    PRIOR_IGNORANCE_WEIGHT,
    _jsd_bits,
    _operational_opinion,
)

RUN_VERSION = "phase14b-controlled-representation-evolution-v0.1"
OUT_DIR = ROOT / "eval/live/results/phase14b_controlled_representation_evolution_v0_1"
N_PER_STAGE = 4

STAGES = [
    {
        "stage": "E0_WEAK",
        "a": {
            "title": "Acme developer platform announcement",
            "content": "Acme announced a change to its developer platform. Product, timing, and rollout details were not specified.",
            "summary": "Acme announced a change to its developer platform.",
            "action": "announced a developer platform change",
            "status": "ANNOUNCED",
            "affected": "developers",
            "uncertainties": ["exact product unavailable", "exact timing unavailable"],
        },
        "b": {
            "title": "Acme developer platform release update",
            "content": "Acme described a new release for developers. The report did not identify the exact product or launch date.",
            "summary": "Acme described a new release for developers.",
            "action": "described a developer platform release",
            "status": "ANNOUNCED",
            "affected": "developers",
            "uncertainties": ["exact product unavailable", "exact timing unavailable"],
        },
    },
    {
        "stage": "E1_NAMED",
        "a": {
            "title": "Acme launches Nimbus API public beta",
            "content": "Acme launched the Nimbus API public beta for software developers.",
            "summary": "Acme launched the Nimbus API public beta for developers.",
            "action": "launched Nimbus API public beta",
            "status": "ENACTED",
            "affected": "software developers",
            "uncertainties": ["venue and exact launch date unavailable"],
        },
        "b": {
            "title": "Nimbus API beta released by Acme",
            "content": "Acme released the Nimbus API public beta to developers.",
            "summary": "Acme released the Nimbus API public beta to developers.",
            "action": "released Nimbus API public beta",
            "status": "ENACTED",
            "affected": "software developers",
            "uncertainties": ["venue and exact launch date unavailable"],
        },
    },
    {
        "stage": "E2_CORROBORATED",
        "a": {
            "title": "Acme launches Nimbus API beta at AtlasConf",
            "content": "At AtlasConf on September 19, Acme launched the Nimbus API public beta for software developers, adding streaming tool calls.",
            "summary": "Acme launched the Nimbus API public beta at AtlasConf on September 19, adding streaming tool calls for developers.",
            "action": "launched Nimbus API public beta at AtlasConf on September 19 with streaming tool calls",
            "status": "ENACTED",
            "affected": "software developers using Nimbus API",
            "uncertainties": [],
        },
        "b": {
            "title": "Nimbus API public beta debuts at AtlasConf",
            "content": "Acme debuted the Nimbus API public beta at AtlasConf on September 19. The developer release includes streaming tool-call support.",
            "summary": "Acme debuted the Nimbus API public beta at AtlasConf on September 19 with streaming tool-call support.",
            "action": "debuted Nimbus API public beta at AtlasConf on September 19 with streaming tool calls",
            "status": "ENACTED",
            "affected": "software developers using Nimbus API",
            "uncertainties": [],
        },
    },
    {
        "stage": "E3_CONFLICT",
        "a": {
            "title": "Acme launches Nimbus API beta at AtlasConf",
            "content": "At AtlasConf on September 19, Acme launched the Nimbus API public beta for software developers, adding streaming tool calls.",
            "summary": "Acme launched the Nimbus API public beta at AtlasConf on September 19, adding streaming tool calls for developers.",
            "action": "launched Nimbus API public beta at AtlasConf on September 19 with streaming tool calls",
            "status": "ENACTED",
            "affected": "software developers using Nimbus API",
            "uncertainties": [],
        },
        "b": {
            "title": "Acme says Nimbus API beta will launch September 26",
            "content": "Acme said the Nimbus API public beta had not launched on September 19 and is scheduled for September 26. The planned beta includes streaming tool calls.",
            "summary": "Acme said Nimbus API public beta had not launched on September 19 and is scheduled for September 26.",
            "action": "scheduled Nimbus API public beta for September 26 and denied a September 19 launch",
            "status": "PLANNED",
            "affected": "software developers using Nimbus API",
            "uncertainties": ["conflicts with a report claiming an enacted September 19 launch"],
        },
    },
]


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def entropy_bits(distribution: dict[str, float]) -> float:
    return -sum(p * math.log2(p) for p in distribution.values() if p > 0.0)


def _frame_payload(stage: str, side: str, row: dict) -> dict:
    return {
        "event_key": f"controlled-nimbus-launch-{side}-{stage}",
        "event_title": "Acme Nimbus API public beta launch",
        "event_summary": row["summary"],
        "semantic_provenance": {
            "mode": "AUDITED_BRIDGE",
            "authority": "SEMANTIC_AUDITED",
            "controlled_evolution": True,
            "controlled_stage": stage,
        },
        "source": {},
        "actors": [{"name": "Acme", "role": "actor"}],
        "actions": [
            {
                "description": row["action"],
                "temporal_status": row["status"],
            }
        ],
        "affected_systems_populations": [{"name": row["affected"]}],
        "uncertainties": list(row["uncertainties"]),
        "rejected_or_unscorable_objects": [],
        "rendered_event_text": row["summary"],
        "claim_evidence": [],
        "observation_evidence": [],
        "audit_summary": {"controlled": True},
    }


def make_frame_pair(db: Session, stage_row: dict):
    stage = stage_row["stage"]
    frames = []
    for side in ("a", "b"):
        row = stage_row[side]
        source = ingest_text(db, row["content"], title=row["title"])
        source.publisher = "Publisher Alpha" if side == "a" else "Publisher Beta"
        source.canonical_url = f"https://{side}.example.test/nimbus/{stage.lower()}"
        source.published_at = datetime(2026, 9, 19, 12 if side == "a" else 13, tzinfo=timezone.utc)
        db.flush()
        frame = _persist_payload(
            db,
            source=source,
            payload=_frame_payload(stage, side.upper(), row),
            analysis_run_id=None,
            frame_ordinal=0,
            workspace_id="phase14b-controlled",
        )
        frames.append(frame)
    return tuple(frames)


def summarize_stage(rows) -> dict:
    counts = Counter(
        str((row.judgments.get("event_identity") or {}).get("value") or "UNCERTAIN")
        for row in rows
    )
    labels = ("SAME_EVENT", "DIFFERENT_EVENT", "UNCERTAIN")
    count_payload = {label: int(counts.get(label, 0)) for label in labels}
    total = sum(count_payload.values())
    q = {label: count_payload[label] / max(1, total) for label in labels}
    opinion = _operational_opinion(
        count_payload,
        prior_ignorance_weight=PRIOR_IGNORANCE_WEIGHT,
        base_rate_same=BASE_RATE_SAME,
    )
    return {
        "sample_count": total,
        "counts": count_payload,
        "response_distribution": {k: round(v, 6) for k, v in q.items()},
        "response_entropy_bits": round(entropy_bits(q), 6),
        "operational_opinion": opinion,
        "audit_run_ids": [str(row.id) for row in rows],
        "bundle_digests": sorted({str(row.input_evidence_digest) for row in rows}),
        "iid_sampling_certified": False,
        "calibrated_world_truth_probability": False,
    }


def run() -> dict:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    results = []

    with Session(engine) as db:
        for stage_row in STAGES:
            stage = stage_row["stage"]
            frame_a, frame_b = make_frame_pair(db, stage_row)
            rows = []
            for ordinal in range(1, N_PER_STAGE + 1):
                audit, _trace = audit_frame_pair_shadow(
                    db,
                    frame_a.id,
                    frame_b.id,
                    run_tag=f"{RUN_VERSION}-{stage}-{ordinal:02d}",
                    provider_label="model",
                )
                db.commit()
                rows.append(audit)
                print(
                    json.dumps(
                        {
                            "stage": stage,
                            "sample": ordinal,
                            "event_identity": (audit.judgments.get("event_identity") or {}).get("value"),
                            "relation_context": (audit.judgments.get("relation_context") or {}).get("value"),
                            "model": audit.model,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            summary = summarize_stage(rows)
            summary["stage"] = stage
            summary["frame_ids"] = [str(frame_a.id), str(frame_b.id)]
            summary["stage_evidence"] = {
                "A": stage_row["a"],
                "B": stage_row["b"],
            }
            results.append(summary)

    for idx, row in enumerate(results):
        row["jsd_from_previous_stage_bits"] = None
        if idx:
            row["jsd_from_previous_stage_bits"] = round(
                _jsd_bits(
                    results[idx - 1]["response_distribution"],
                    row["response_distribution"],
                ),
                6,
            )

    same = [row["response_distribution"]["SAME_EVENT"] for row in results]
    diagnostics = {
        "named_or_corroborated_not_below_weak": max(same[1], same[2]) >= same[0],
        "explicit_conflict_does_not_raise_same_support": same[3] <= same[2],
        "weak_same_rate": same[0],
        "named_same_rate": same[1],
        "corroborated_same_rate": same[2],
        "conflict_same_rate": same[3],
        "note": "Directional diagnostics only; non-monotonic behavior is reported, not tuned away.",
    }

    return {
        "run_version": RUN_VERSION,
        "status": "CONTROLLED_EVOLUTION_COMPLETE",
        "measurement_git_head": git_head(),
        "auditor_contract": REPRESENTATION_AUDITOR_CONTRACT,
        "n_per_stage": N_PER_STAGE,
        "conceptual_hypothesis": "Do Publisher Alpha and Publisher Beta describe the same Acme Nimbus API public-beta launch event?",
        "stages": results,
        "directional_diagnostics": diagnostics,
        "guardrails": [
            "In-memory database only.",
            "No production Event/EventSource topology.",
            "No production Attention/WATCH/Kernel/Delivery mutation.",
            "Each stage is a controlled immutable evidence epoch.",
            "Operational probability proxy is uncalibrated.",
            "This experiment does not estimate a natural stochastic-process transition law.",
        ],
    }


def main() -> None:
    report = run()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = OUT_DIR / f"{RUN_VERSION.replace('-', '_')}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("RESULT_PATH=" + str(path.relative_to(ROOT)))
    for row in report["stages"]:
        print(
            row["stage"],
            "N", row["sample_count"],
            "counts", row["counts"],
            "q", row["response_distribution"],
            "H", row["response_entropy_bits"],
            "opinion", row["operational_opinion"],
            "JSD", row["jsd_from_previous_stage_bits"],
        )
    print("DIAGNOSTICS", json.dumps(report["directional_diagnostics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
