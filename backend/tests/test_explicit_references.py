from uuid import UUID

from sqlalchemy import select

from app.connectors.url import URLConnector, _extract_explicit_references
from app.connectors.wechat import _build_metadata
from app.models.ingestion import ParserRun
from app.models.source import Source, SourceEdge
from app.services.fingerprint import NormalizedSource
from app.services.ingestion import ingest_text, persist_normalized
from app.services.source_graph import resolve_references
from bs4 import BeautifulSoup


def test_explicit_href_extraction_is_literal_cites_not_same_event():
    html = """
    <article>
      <p>Reference material follows.</p>
      <p><a href="https://claude.com/blog/agentic-ci">Anthropic official post</a></p>
      <p><a href="/local-page">Local publisher link</a></p>
      <p><a href="#section">Jump</a></p>
      <p><a href="https://example.com/image.png">Image</a></p>
      <p><a href="https://wechat2rss.bestblogs.dev/link-proxy/?u=https%3A%2F%2Fexample.com%2Fstory">Transport self-link</a></p>
    </article>
    """
    root = BeautifulSoup(html, "lxml").find("article")
    refs = _extract_explicit_references(root, "https://example.com/story")

    assert [r["url"] for r in refs] == [
        "https://claude.com/blog/agentic-ci",
        "https://example.com/local-page",
    ]
    assert all(r["relation_hint"] == "CITES" for r in refs)
    assert all(r["evidence_kind"] == "explicit_href" for r in refs)
    assert refs[0]["anchor_text"] == "Anthropic official post"


def test_url_connector_preserves_explicit_references_in_normalized_source(monkeypatch):
    connector = URLConnector()
    html = """
    <html><head><title>Story</title></head>
    <body><article><p>Body paragraph with enough text for extraction.</p>
    <p><a href="https://anthropic.com/research/source">Original research</a></p>
    </article></body></html>
    """
    from app.connectors.base import RawSource

    parsed = connector.parse(
        RawSource(
            payload=html,
            content_type="text/html",
            origin="https://publisher.example/story",
            metadata={"final_url": "https://publisher.example/story"},
        )
    )
    normalized = connector.normalize(parsed)

    assert normalized.reference_candidates
    assert normalized.reference_candidates[0]["url"] == "https://anthropic.com/research/source"
    assert normalized.raw_metadata["reference_candidates"] == normalized.reference_candidates
def test_wechat_metadata_extracts_literal_article_links():
    html = """
    <html><body><div id="js_content">
      <p>这是一段足够长的微信公众号正文，用于确认显式外链会进入 reference candidates，而正文仍然保持正常。</p>
      <p>参考资料：</p>
      <p><a href="https://claude.com/blog/agentic-coding-ci">Claude 官方博客原文</a></p>
      <p><a href="https://x.com/example/status/123">作者公开讨论</a></p>
    </div></body></html>
    """
    text, metadata = _build_metadata(
        html,
        "https://mp.weixin.qq.com/s?__biz=x&mid=1&idx=1",
        account="新智元",
        biz="x",
        fetch_mode="wechat2rss-fallback-v1",
        feed_url="https://feed.example/x",
        direct_status=403,
    )

    urls = [r["url"] for r in metadata["reference_candidates"]]
    assert urls == [
        "https://claude.com/blog/agentic-coding-ci",
        "https://x.com/example/status/123",
    ]
    assert "参考资料" in text


def test_explicit_url_reference_persists_url_stub_and_cites_edge(db):
    normalized = NormalizedSource(
        source_type="URL",
        title="Secondary media report",
        canonical_url="https://media.example/report",
        content_text="A report explicitly links the original publisher.",
        ingestion_method="URL_FETCH",
        reference_candidates=[
            {
                "raw_text": "Anthropic official post",
                "title": "Anthropic official post",
                "url": "https://claude.com/blog/original",
                "doi": None,
                "arxiv_id": None,
                "confidence": 1.0,
                "evidence_kind": "explicit_href",
                "relation_hint": "CITES",
            }
        ],
    )
    source = persist_normalized(db, normalized)

    edge = db.execute(
        select(SourceEdge).where(SourceEdge.source_id == source.id, SourceEdge.relationship == "CITES")
    ).scalar_one()
    target = db.get(Source, edge.target_id)
    assert target.source_type == "URL"
    assert target.ingestion_method == "REFERENCE_STUB"
    assert target.canonical_url == "https://claude.com/blog/original"
    assert target.raw_metadata["reference_candidate"]["evidence_kind"] == "explicit_href"
def test_append_only_reference_parser_run_is_aggregated(db):
    source = ingest_text(db, "Historical source with no old references.", title="Historical source")
    db.add(
        ParserRun(
            source_id=source.id,
            parser_name="reference-extractor-explicit-links",
            parser_version="v1",
            output_metadata={
                "references": [
                    {
                        "raw_text": "Official source",
                        "title": "Official source",
                        "url": "https://official.example/story",
                        "doi": None,
                        "arxiv_id": None,
                        "confidence": 1.0,
                    }
                ]
            },
        )
    )
    db.flush()

    resolved = resolve_references(db, source.id)
    assert len(resolved) == 1
    target = db.get(Source, UUID(resolved[0]["resolved_source_id"]))
    assert target.source_type == "URL"
    assert target.canonical_url == "https://official.example/story"
    assert resolved[0]["relationship"] == "CITES"
