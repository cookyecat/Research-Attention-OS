from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess
import sys

import pytest
from sqlalchemy import create_engine

from app.schema_authority import (
    assert_database_schema_current,
    repository_schema_heads,
)


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
VERSIONS = BACKEND / "alembic" / "versions"
ALEMBIC_BIN = Path(sys.executable).with_name("alembic")
SCHEMA_CHECK = ROOT / "scripts" / "check-schema-authority.py"


def test_migration_history_is_frozen_from_runtime_orm():
    violations: list[str] = []
    for path in sorted(VERSIONS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "app.models" or alias.name.startswith("app.models."):
                        violations.append(f"{path.name}: imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module == "app.models" or str(node.module or "").startswith("app.models."):
                    violations.append(f"{path.name}: imports from {node.module}")
                if node.module == "app.db" and any(alias.name == "Base" for alias in node.names):
                    violations.append(f"{path.name}: imports runtime Base")
    assert violations == []


def test_repository_migration_graph_has_one_head():
    heads = repository_schema_heads()
    assert len(heads) == 1


def test_fresh_database_upgrades_to_head_and_matches_orm(tmp_path):
    db_path = tmp_path / "fresh-schema.db"
    url = f"sqlite:///{db_path}"
    env = os.environ.copy()
    env["RAOS_DATABASE_URL"] = url
    env["RAOS_AUTO_CREATE_TABLES"] = "false"

    upgraded = subprocess.run(
        [str(ALEMBIC_BIN), "upgrade", "head"],
        cwd=BACKEND,
        env=env,
        text=True,
        capture_output=True,
    )
    assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr

    checked = subprocess.run(
        [sys.executable, str(SCHEMA_CHECK), "--database-url", url],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "SCHEMA_DRIFT_COUNT=0" in checked.stdout

    engine = create_engine(url, future=True)
    contract = assert_database_schema_current(engine)
    assert contract["current"] is True
    assert contract["database_revisions"] == contract["repository_heads"]


def test_schema_guard_rejects_unversioned_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'unversioned.db'}", future=True)
    with pytest.raises(RuntimeError, match="UNVERSIONED"):
        assert_database_schema_current(engine)


def test_canonical_runtime_rejects_create_all(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main.settings, "auto_create_tables", True)
    monkeypatch.setattr(main.settings, "execution_purpose", "CANONICAL")
    with pytest.raises(RuntimeError, match="forbids Base.metadata.create_all"):
        main.startup()


def test_relative_sqlite_database_url_is_anchored_to_backend():
    from sqlalchemy.engine import make_url
    from app.config import Settings

    settings = Settings(database_url="sqlite:///./raos.db")
    path = Path(make_url(settings.database_url).database)
    assert path.is_absolute()
    assert path == (BACKEND / "raos.db").resolve()


def test_test_runtime_never_create_all_on_import_time_app_engine(monkeypatch):
    import app.main as main

    calls = []

    def forbidden_create_all(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError(
            "TEST startup must not mutate the import-time app engine"
        )

    monkeypatch.setattr(main.settings, "auto_create_tables", True)
    monkeypatch.setattr(main.settings, "execution_purpose", "TEST")
    monkeypatch.setattr(
        main.Base.metadata,
        "create_all",
        forbidden_create_all,
    )

    main.startup()
    assert calls == []
