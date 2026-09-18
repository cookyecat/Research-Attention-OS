from app.connectors.base import DiscoveredItem
from app.connectors.base import DiscoveredItem
from app.connectors.url import URLConnector


class FakeResponse:
    def __init__(self, *, status_code, url, text, content_type="text/html"):
        self.status_code = status_code
        self.url = url
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            request = httpx.Request("GET", str(self.url))
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("fetch failed", request=request, response=response)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_openai_403_uses_rendered_fallback_with_explicit_provenance(monkeypatch):
    original = "https://openai.com/index/example/"
    rendered_html = """
    <html><body><article>
      <p data-article-hero-copy-region="subhead">Summary.</p>
      <div data-toc-content><h2>Section</h2><p>Body.</p></div>
    </article></body></html>
    """
    fake = FakeClient([
        FakeResponse(status_code=403, url=original, text="Enable JavaScript and cookies to continue"),
        FakeResponse(status_code=200, url=f"https://r.jina.ai/{original}", text=rendered_html),
    ])
    monkeypatch.setattr("app.connectors.url.httpx.Client", lambda **_: fake)
    monkeypatch.setattr("app.connectors.url.validate_public_url", lambda value: value)

    raw = URLConnector().fetch(DiscoveredItem(ref=original, metadata={}))
    assert b"data-toc-content" in raw.payload
    assert raw.origin == original
    assert raw.metadata["publisher_fetch_mode"] == "openai-rendered-fallback-v1"
    assert raw.metadata["publisher_direct_status"] == 403
    assert raw.metadata["publisher_direct_blocked"] is True
    assert raw.metadata["publisher_fallback_provider"] == "jina-reader"
    assert raw.metadata["publisher_fallback_attempts"] == 1
    assert fake.calls[1][0] == f"https://r.jina.ai/{original}"

    parsed = URLConnector().parse(raw)
    assert parsed.metadata["publisher_dynamic_media_status"] == "unverified_from_rendered_fallback"


def test_openai_rendered_fallback_retries_challenge_before_accepting_semantic_article(monkeypatch):
    original = "https://openai.com/index/retry-example/"
    challenge = "<html><body>Enable JavaScript and cookies to continue</body></html>"
    rendered_html = """
    <html><body><article><div data-toc-content>
      <h2>Recovered section</h2><p>Recovered body.</p>
    </div></article></body></html>
    """
    fake = FakeClient([
        FakeResponse(status_code=403, url=original, text=challenge),
        FakeResponse(status_code=200, url=f"https://r.jina.ai/{original}", text=challenge),
        FakeResponse(status_code=200, url=f"https://r.jina.ai/{original}", text=rendered_html),
    ])
    monkeypatch.setattr("app.connectors.url.httpx.Client", lambda **_: fake)
    monkeypatch.setattr("app.connectors.url.validate_public_url", lambda value: value)
    monkeypatch.setattr("app.connectors.url.time.sleep", lambda *_: None)

    raw = URLConnector().fetch(DiscoveredItem(ref=original, metadata={}))
    assert b"Recovered section" in raw.payload
    assert raw.metadata["publisher_fallback_attempts"] == 2
    assert len(fake.calls) == 3
