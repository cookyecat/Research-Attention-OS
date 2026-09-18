from collections.abc import Generator
import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 60.0}
    return kwargs


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _connection_record) -> None:
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        # Local dogfood runs backend, acquisition and delivery as separate
        # processes against one SQLite file. WAL keeps readers concurrent with
        # a cognition writer; busy_timeout turns short writer collisions into
        # bounded waiting instead of user-visible 500s.
        cursor.execute("PRAGMA busy_timeout=60000")
        # WAL is persistent at the database-file level. Avoid reissuing the
        # mode change on every connection because changing journal mode itself
        # needs an exclusive lock. The first clean startup upgrades the file;
        # later connections simply observe WAL.
        try:
            current_mode = str(cursor.execute("PRAGMA journal_mode").fetchone()[0]).lower()
            if current_mode != "wal":
                cursor.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # A pre-existing process may still own the old-mode writer lock.
            # Do not make a connection unusable solely because the one-time
            # mode upgrade could not happen at this instant.
            pass
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
