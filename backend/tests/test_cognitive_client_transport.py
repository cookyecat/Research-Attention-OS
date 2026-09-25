from app.cognitive.client import _httpx_client_kwargs


def test_private_embedding_endpoint_bypasses_environment_proxy():
    kwargs = _httpx_client_kwargs(
        "http://192.168.50.114:8001/v1/embeddings",
        30.0,
    )
    assert kwargs == {"timeout": 30.0, "trust_env": False}


def test_loopback_and_local_hosts_bypass_environment_proxy():
    assert _httpx_client_kwargs("http://localhost:8001/v1", 5.0)["trust_env"] is False
    assert _httpx_client_kwargs("http://jetson.local:8001/v1", 5.0)["trust_env"] is False


def test_public_endpoint_preserves_environment_proxy_behavior():
    kwargs = _httpx_client_kwargs(
        "https://api.deepseek.com/v1/chat/completions",
        45.0,
    )
    assert kwargs == {"timeout": 45.0}
