from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
for p in (ROOT, BACKEND):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app import models as _models  # noqa: F401
from app.db import Base
from app.services.ingestion import ingest_url

RUN_VERSION = "phase10d3-acquisition-preflight-v0.1"
MANIFEST = ROOT / "eval/live/manifest.phase10d3_acquisition_preflight.v0.1.yaml"
OUTDIR = ROOT / "eval/live/results/phase10d3_acquisition_preflight_v0_1"
def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    min_chars = int(manifest["viability"]["min_content_chars"])
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    rows = []
    selected = {}

    with Session(engine) as db:
        for stratum, candidates in manifest["strata"].items():
            selected[stratum] = []
            for spec in candidates:
                row = {
                    "stratum": stratum,
                    "id": spec["id"],
                    "publisher": spec["publisher"],
                    "url": spec["url"],
                }
                try:
                    src = ingest_url(db, str(spec["url"]))
                    chars = len(src.content_text or "")
                    row.update({
                        "status": "PREFLIGHT_PASS" if chars >= min_chars else "PREFLIGHT_FAIL",
                        "content_chars": chars,
                        "content_hash": src.content_hash,
                        "title": src.title,
                        "canonical_url": src.canonical_url,
                    })
                except Exception as exc:
                    row.update({
                        "status": "PREFLIGHT_FAIL",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    })
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), flush=True)
            passing = [r for r in rows if r["stratum"] == stratum and r["status"] == "PREFLIGHT_PASS"]
            selected[stratum] = [r["id"] for r in passing[:2]]

    artifact = {
        "run_version": RUN_VERSION,
        "measurement_sha": git_head(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_version": manifest["version"],
        "selection_rule": manifest["selection_rule"],
        "viability": manifest["viability"],
        "rows": rows,
        "selected": selected,
        "guardrails": [
            "No Sensor, Auditor, Locate, Relation Mapping, CognitiveEffect, Attention, or probability-map call is made in this preflight.",
            "Selection uses only manifest order and acquisition viability.",
            "Website access failures are acquisition-tool limitations, not cognitive-model failures.",
        ],
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUTDIR / f"phase10d3_acquisition_preflight_v0.1_{stamp}.json"
    out.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SELECTED=" + json.dumps(selected, ensure_ascii=False))
    print("RESULT_PATH=" + str(out.relative_to(ROOT)))
    print("RESULT_SHA256=" + sha256(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
