from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import pytest
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.main import app


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client(engine) -> TestClient:
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        seeded = test_client.post("/kernel/seed")
        assert seeded.status_code == 200
        yield test_client
    app.dependency_overrides.clear()


def kernel_index(client: TestClient) -> dict[str, dict]:
    data = client.get("/kernel").json()
    index = {}
    for _typ, nodes in data.items():
        for node in nodes:
            title = node.get("title") or ""
            if title.startswith("Build better embodied"):
                index["G1"] = node
            elif title == "Motor Intelligence":
                index["P1"] = node
            elif "latency" in title.lower() and "energy" in title.lower():
                index["BT1"] = node
            elif title.startswith("Should high-frequency"):
                index["Q1"] = node
            elif "unsuitable for the fastest" in title:
                index["B1"] = node
            elif "partially separable" in title:
                index["M1"] = node
            elif title == "Collective Intelligence":
                index["P2"] = node
            elif "shared world models" in title.lower():
                index["Q2"] = node
            elif "swarm-style" in title.lower():
                index["B2"] = node
            elif "equity terms" in title.lower():
                index["D1"] = node
    return index


def add_text(client: TestClient, text: str, title: str | None = None) -> dict:
    r = client.post("/sources", json={"source_type": "TEXT", "title": title, "content_text": text})
    assert r.status_code == 200, r.text
    return r.json()


def add_observation(client: TestClient, text: str, title: str | None = None) -> dict:
    r = client.post("/sources", json={"source_type": "MANUAL_OBSERVATION", "title": title, "content_text": text})
    assert r.status_code == 200, r.text
    return r.json()


def analyze(client: TestClient, source_id: str, extra_ids: list[str] | None = None, persist_watches: bool = False) -> dict:
    r = client.post(
        "/analysis/extract",
        json={
            "source_id": source_id,
            "extra_source_ids": extra_ids or [],
            "persist_suggested_watches": persist_watches,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def matched_codes(result: dict, index: dict[str, dict]) -> set[str]:
    ids = {m["node_id"] for m in result["kernel_matches"]}
    return {code for code, node in index.items() if node["id"] in ids}
