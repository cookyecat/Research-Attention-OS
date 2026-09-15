from app.deployment_scope import deployment_contract


def test_deployment_contract_fails_closed_to_single_user_dogfood() -> None:
    contract = deployment_contract()
    assert contract["scope"] == "SINGLE_USER_DOGFOOD"
    assert contract["authenticated_user_identity"] is False
    assert contract["multi_user_isolation"] is False
    assert contract["state_ownership_boundary"] == "DEFINED_NOT_TENANTIZED"


def test_health_and_agent_capabilities_expose_same_scope(client) -> None:
    health = client.get("/health")
    capabilities = client.get("/agent/v1/capabilities")
    assert health.status_code == 200
    assert capabilities.status_code == 200
    assert health.json()["deployment"] == capabilities.json()["deployment"]
    assert health.json()["deployment"]["multi_user_isolation"] is False
