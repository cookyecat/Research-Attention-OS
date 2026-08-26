from fastapi.testclient import TestClient

from app.connectors.url import SSRFBlocked, validate_public_url
from app.services.extraction import extract_from_text, observation_is_forbidden_inference
from app.services.fingerprint import NormalizedSource, content_hash, fingerprint
from tests.conftest import add_text, analyze, kernel_index


def test_ssrf_blocks_localhost():
    for url in ("http://127.0.0.1/", "http://localhost:8000/secret", "http://10.0.0.1/"):
        try:
            validate_public_url(url)
            raise AssertionError(f"should block {url}")
        except SSRFBlocked:
            pass


def test_fingerprint_priority_doi():
    n = NormalizedSource(
        source_type="PAPER",
        canonical_url="https://example.com/x",
        content_text="hello",
        external_ids={"doi": "10.1/abc"},
        ingestion_method="PDF_UPLOAD",
    )
    assert fingerprint(n).startswith("fp-v1:doi:")


def test_claim_cannot_become_observation():
    result = extract_from_text(
        "The founder says the robot generalizes zero-shot. In the video, it succeeds once. This probably means the system is robust."
    )
    assert any("zero-shot" in c.text.lower() for c in result.claims)
    assert any("succeeds once" in o.text.lower() for o in result.observations)
    assert any("robust" in c.text.lower() or "probably" in c.text.lower() for c in result.claims)
    assert not any("robust" in o.text.lower() for o in result.observations)
    assert not any(observation_is_forbidden_inference(o.text) for o in result.observations)
    assert not any(i.author_type == "AI" and "probably means the system is robust" in i.text.lower() for i in result.inferences)


def test_inference_requires_source_object(client: TestClient):
    src = add_text(client, "The founder says the robot generalizes zero-shot. This probably means the system is robust.")
    result = analyze(client, src["id"])
    assert any("robust" in c["text"].lower() or "probably" in c["text"].lower() for c in result["claims"])
    assert not any("robust" in o["text"].lower() for o in result["observations"])
    for inf in result["inferences"]:
        assert inf["author_type"] == "AI"
        assert "probably means the system is robust" not in inf["text"].lower()
    got = client.get(f"/sources/{src['id']}")
    assert got.status_code == 200


def test_soft_delete_sources_not_hard_deleted(client: TestClient):
    src = add_text(client, "Keep provenance.", title="prov")
    row = client.get(f"/sources/{src['id']}").json()
    assert row["deleted_at"] is None
    assert row["fingerprint"]
    assert row["ingestion_method"]


def test_kernel_versions_append_only(client: TestClient):
    index = kernel_index(client)
    created = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "BELIEF",
            "target_object_id": index["B1"]["id"],
            "change_type": "REVISE",
            "current_state": index["B1"],
            "proposed_state": {"status": "CONTESTED", "payload": index["B1"]["payload"], "title": index["B1"]["title"]},
            "reasoning": "test",
        },
    )
    patch_id = created.json()["id"]
    client.post(f"/kernel/patches/{patch_id}/accept")
    versions = client.get(f"/kernel/nodes/{index['B1']['id']}/versions").json()
    nums = [v["version"] for v in versions]
    assert nums == sorted(nums)
    # cannot overwrite by posting another accept
    again = client.post(f"/kernel/patches/{patch_id}/accept")
    assert again.status_code == 409


def test_api_minimum_capabilities(client: TestClient):
    src = add_text(client, "A technical paper about motor intelligence latency.", title="api")
    assert client.get(f"/sources/{src['id']}").status_code == 200
    assert client.post("/analysis/extract", json={"source_id": src["id"]}).status_code == 200
    assert client.post("/scheduler/plan", json={"source_id": src["id"]}).status_code == 200
    assert client.get("/kernel").status_code == 200
    patch = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "QUESTION",
            "change_type": "CREATE",
            "proposed_state": {"title": "Q?", "status": "OPEN", "payload": {"text": "Q?"}},
            "reasoning": "user",
            "proposed_by": "USER",
        },
    )
    pid = patch.json()["id"]
    assert client.post(f"/kernel/patches/{pid}/reject").status_code == 200
    w = client.post(
        "/watches",
        json={
            "target_type": "PAPER",
            "target_ref": "x",
            "created_reason": "test",
            "triggers": ["PAPER_RELEASE"],
        },
    )
    assert w.status_code == 200
    assert client.get("/watches").status_code == 200
    assert client.get(f"/sources/{src['id']}/references").status_code == 200


def test_modify_and_reject_patches(client: TestClient):
    index = kernel_index(client)
    created = client.post(
        "/kernel/patches",
        json={
            "target_object_type": "BELIEF",
            "target_object_id": index["B1"]["id"],
            "change_type": "REVISE",
            "proposed_state": {"status": "CONTESTED", "title": index["B1"]["title"], "payload": index["B1"]["payload"]},
            "reasoning": "x",
        },
    )
    pid = created.json()["id"]
    modified = client.post(
        f"/kernel/patches/{pid}/modify",
        json={"modified_state": {"status": "ACTIVE", "payload": {**index["B1"]["payload"], "confidence": 0.5}}},
    )
    assert modified.status_code == 200
    assert modified.json()["status"] == "MODIFIED"
    b1 = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert b1["payload"]["confidence"] == 0.5
