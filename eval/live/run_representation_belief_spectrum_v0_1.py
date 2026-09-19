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
from app.services.representation_auditor import audit_frame_pair_shadow
from app.services.representation_belief import frame_pair_belief_history

CASES = [
    ("jev_same_event", "1fbc440f-9cc3-4417-8f30-d0146491fd3e", "1fbc440f-9cc3-4417-8f30-d0146491fd3e-evt-01",
     "9ba9e72a-3dbb-40b2-9066-1b7a2bc5dc27", "9ba9e72a-3dbb-40b2-9066-1b7a2bc5dc27-evt-jev-release"),
    ("steam_related_different", "7b14458f-6123-4fbe-9c4b-52415e850fee", "7b14458f-6123-4fbe-9c4b-52415e850fee-evt-002",
     "ba822d55-83d1-4a49-8a1e-dbd56091e63e", "ba822d55-steam-frame-accessories"),
    ("php_unrelated", "39bd3b81-12eb-41db-b080-bbd37a465f16", "39bd3b81-12eb-41db-b080-bbd37a465f16-evt-1",
     "de2189a6-0a3e-4a18-a6e6-d8ec5ef1d826", "de2189a6-0a3e-4a18-a6e6-d8ec5ef1d826-evt-001"),
]


def _resolve(db, source_id: str, event_key: str):
    frames = latest_event_evidence_frames_for_source(db, UUID(source_id))
    matches = [f for f in frames if (f.frame_payload or {}).get("event_key") == event_key]
    if len(matches) != 1:
        raise RuntimeError(f"expected one frame for source={source_id} event={event_key}; got {len(matches)}")
    return matches[0]


def _matching_epoch(history: dict, digest: str, provider: str, model: str) -> dict | None:
    for epoch in history.get("epochs") or []:
        if (
            epoch.get("input_evidence_digest") == digest
            and str(epoch.get("provider") or "") == provider
            and str(epoch.get("model") or "") == model
        ):
            return epoch
    return None


def run(target_n: int) -> dict:
    results = []
    with SessionLocal() as db:
        for case_name, sa, ea, sb, eb in CASES:
            fa = _resolve(db, sa, ea)
            fb = _resolve(db, sb, eb)

            # First call establishes/reuses the exact current frozen-bundle epoch.
            audit, trace = audit_frame_pair_shadow(
                db,
                fa.id,
                fb.id,
                run_tag=f"belief-spectrum-v0.1-{case_name}-bootstrap",
            )
            db.commit()
            digest = audit.input_evidence_digest
            provider = str(audit.provider or "")
            model = str(audit.model or "")

            history = frame_pair_belief_history(db, fa.id, fb.id)
            epoch = _matching_epoch(history, digest, provider, model)
            current_n = int((epoch or {}).get("sample_count") or 0)

            sample_index = 0
            while current_n < target_n:
                sample_index += 1
                row, _ = audit_frame_pair_shadow(
                    db,
                    fa.id,
                    fb.id,
                    run_tag=f"belief-spectrum-v0.1-{case_name}-sample-{sample_index:02d}",
                )
                db.commit()
                if row.input_evidence_digest != digest:
                    raise RuntimeError(
                        f"evidence changed during frozen spectrum experiment for {case_name}"
                    )
                history = frame_pair_belief_history(db, fa.id, fb.id)
                epoch = _matching_epoch(history, digest, provider, model)
                current_n = int((epoch or {}).get("sample_count") or 0)

            results.append(
                {
                    "case": case_name,
                    "frame_id_a": str(fa.id),
                    "frame_id_b": str(fb.id),
                    "input_evidence_digest": digest,
                    "provider": provider,
                    "model": model,
                    "target_n": target_n,
                    "epoch": epoch,
                }
            )

    return {
        "experiment": "representation-belief-spectrum-v0.1",
        "target_n_per_case": target_n,
        "n_cases": len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-n", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(max(2, min(args.target_n, 24)))
    body = json.dumps(report, ensure_ascii=False, indent=2)
    print(body)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(body + "\n")


if __name__ == "__main__":
    main()
