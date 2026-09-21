from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy import Engine, inspect, text


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_VERSIONS_DIR = _BACKEND_ROOT / "alembic" / "versions"


def _literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"{path.name} does not define literal {name}")


def repository_schema_heads() -> tuple[str, ...]:
    revisions: dict[str, Path] = {}
    parents: set[str] = set()
    for path in sorted(_VERSIONS_DIR.glob("*.py")):
        revision = _literal_assignment(path, "revision")
        down_revision = _literal_assignment(path, "down_revision")
        if not isinstance(revision, str) or not revision:
            raise RuntimeError(f"Invalid revision in {path}")
        if revision in revisions:
            raise RuntimeError(
                f"Duplicate Alembic revision {revision}: {revisions[revision]} and {path}"
            )
        revisions[revision] = path
        if isinstance(down_revision, str):
            parents.add(down_revision)
        elif isinstance(down_revision, (tuple, list)):
            parents.update(str(value) for value in down_revision if value)

    missing = sorted(parent for parent in parents if parent not in revisions)
    if missing:
        raise RuntimeError(f"Migration graph references missing revisions: {missing}")
    heads = tuple(sorted(set(revisions) - parents))
    if not heads:
        raise RuntimeError("No Alembic schema head found")
    return heads


def database_schema_revisions(engine: Engine) -> tuple[str, ...]:
    if "alembic_version" not in inspect(engine).get_table_names():
        return ()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    return tuple(sorted(str(row) for row in rows))


def assert_database_schema_current(engine: Engine) -> dict:
    expected = repository_schema_heads()
    actual = database_schema_revisions(engine)
    if actual != expected:
        raise RuntimeError(
            "Database schema revision mismatch: "
            f"database={list(actual) or ['UNVERSIONED']} "
            f"repository_head={list(expected)}. "
            "Run Alembic upgrade head before starting RAOS."
        )
    return {
        "authority": "ALEMBIC",
        "database_revisions": list(actual),
        "repository_heads": list(expected),
        "current": True,
    }
