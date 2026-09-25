from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env", override=False)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild disposable RAOS User Space projections."
    )
    parser.add_argument(
        "--runtime-profile",
        default=os.environ.get("RAOS_RUNTIME_PROFILE"),
        help="Canonical runtime profile path. Required unless already in environment.",
    )
    parser.add_argument(
        "--execution-purpose",
        default=os.environ.get("RAOS_EXECUTION_PURPOSE", "CANONICAL"),
    )
    return parser.parse_args()


def main() -> None:
    args = _args()
    if not args.runtime_profile:
        raise RuntimeError(
            "Refusing User Space rebuild without RAOS_RUNTIME_PROFILE. "
            "Pass --runtime-profile from the canonical service identity."
        )
    os.environ["RAOS_RUNTIME_PROFILE"] = str(
        Path(args.runtime_profile).expanduser().resolve()
    )
    os.environ["RAOS_EXECUTION_PURPOSE"] = str(
        args.execution_purpose
    )

    # Import only after canonical identity is fixed.
    from app.config import settings
    from app.db import SessionLocal
    from app.services.user_space_projection import (
        rebuild_user_space_projections,
    )

    if str(settings.execution_purpose).upper() != "CANONICAL":
        raise RuntimeError(
            "Production rebuild requires CANONICAL execution purpose."
        )

    db = SessionLocal()
    try:
        status = rebuild_user_space_projections(
            db,
            acknowledge_outbox=True,
        )
        db.commit()
        print(json.dumps(status, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
