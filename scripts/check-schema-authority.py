#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402
from app.db import Base  # noqa: E402
import app.models  # noqa: F401,E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail if Alembic head schema structurally drifts from ORM metadata."
    )
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    url = args.database_url or settings.database_url
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    if diffs:
        print(f"SCHEMA_DRIFT_COUNT={len(diffs)}")
        for diff in diffs:
            print(diff)
        return 1
    print("SCHEMA_DRIFT_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
