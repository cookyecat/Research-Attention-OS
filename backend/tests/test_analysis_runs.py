from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import add_observation, add_text, analyze


def test_extract_is_idempotent(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="idem")
    first = analyze(client, src["id"])
    second = analyze(client, src["id"])
    assert first["analysis_run"]["id"] == second["analysis_run"]["id"]
    assert {c["id"] for c in first["claims"]} == {c["id"] for c in second["claims"]}
    assert {p["id"] for p in first["kernel_patches"]} == {p["id"] for p in second["kernel_patches"]}
    got = client.get(f"/analysis/by-source/{src['id']}")
    assert got.status_code == 200
    assert got.json()["analysis_run"]["id"] == first["analysis_run"]["id"]


def test_reprocess_creates_new_run(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="reprocess")
    first = analyze(client, src["id"])
    again = client.post("/analysis/reprocess", json={"source_id": src["id"]})
    assert again.status_code == 200, again.text
    body = again.json()
    assert body["analysis_run"]["id"] != first["analysis_run"]["id"]
    latest = client.get(f"/analysis/by-source/{src['id']}").json()
    assert latest["analysis_run"]["id"] == body["analysis_run"]["id"]


def test_analysis_run_records_versions(client: TestClient):
    src = add_text(client, "Motor intelligence latency paper.", title="versions")
    result = analyze(client, src["id"])
    run = result["analysis_run"]
    for key in (
        "extractor_version",
        "matcher_version",
        "evidence_reasoner_version",
        "delta_version",
        "scheduler_version",
        "prompt_version",
        "provider_version",
        "embedding_model_version",
        "pipeline_version",
        "provider_type",
        "input_hash",
        "kernel_snapshot_hash",
    ):
        assert run.get(key), key
    assert run["provider_type"] in {"rule", "model", "model+rule-fallback"}


def test_refresh_after_accept_does_not_rerun(client: TestClient):
    src = add_text(
        client,
        "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently.",
        title="admit",
    )
    result = analyze(client, src["id"])
    run_id = result["analysis_run"]["id"]
    patches = result["kernel_patches"]
    if patches:
        acc = client.post(f"/kernel/patches/{patches[0]['id']}/accept")
        assert acc.status_code == 200
    refreshed = client.get(f"/analysis/by-source/{src['id']}").json()
    assert refreshed["analysis_run"]["id"] == run_id
    if patches:
        statuses = {p["status"] for p in refreshed["kernel_patches"]}
        assert "ACCEPTED" in statuses or "MODIFIED" in statuses
