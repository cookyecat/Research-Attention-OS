from fastapi.testclient import TestClient


def test_bootstrap_propose_does_not_commit(client: TestClient):
    before = client.get("/kernel").json()
    count_before = sum(len(v) for v in before.values())
    r = client.post(
        "/kernel/bootstrap/propose",
        json={"text": "I work on motor intelligence, latency-energy evaluation, and swarm world models."},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kernel_patches"]
    assert all(p["status"] == "PROPOSED" for p in body["kernel_patches"])
    after = client.get("/kernel").json()
    assert sum(len(v) for v in after.values()) == count_before
    pid = body["kernel_patches"][0]["id"]
    acc = client.post(f"/kernel/patches/{pid}/accept")
    assert acc.status_code == 200
    committed = client.get("/kernel").json()
    assert sum(len(v) for v in committed.values()) >= count_before
