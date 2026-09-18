import json

import httpx

from app.connectors.wechat import WechatArticleConnector, is_wechat_challenge, wechat_url_identity
from app.services.wechat_adapters import _parse_feed, parse_wechat_account_locator


BIZ = "MzA3MzI4MjgzMw=="
ARTICLE = (
    "https://mp.weixin.qq.com/s?"
    "__biz=MzA3MzI4MjgzMw%3D%3D&mid=2651057510&idx=1&sn=abc"
)


def test_wechat_locator_and_stable_identity():
    locator = json.dumps({"account": "机器之心", "biz": BIZ, "feed_urls": ["https://example.com/feed.xml"]})
    parsed = parse_wechat_account_locator(locator)
    assert parsed["account"] == "机器之心"
    assert parsed["biz"] == BIZ
    assert wechat_url_identity(ARTICLE) == (BIZ, "2651057510", "1")


def test_wechat_feed_rejects_wrong_biz_and_keeps_full_html():
    rss = f"""<?xml version="1.0"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
      <item><title>Right article</title><link>{ARTICLE.replace("&", "&amp;")}</link>
        <pubDate>Wed, 16 Sep 2026 12:00:00 +0800</pubDate>
        <content:encoded><![CDATA[<p>完整正文第一段。</p><p>完整正文第二段。</p>]]></content:encoded>
      </item>
      <item><title>Wrong account</title>
        <link>https://mp.weixin.qq.com/s?__biz=WrongBiz&amp;mid=1&amp;idx=1</link>
        <content:encoded><![CDATA[<p>不应进入。</p>]]></content:encoded>
      </item>
    </channel></rss>"""
    rows = _parse_feed(rss.encode(), account="机器之心", biz=BIZ, feed_url="https://example.com/feed.xml")
    assert len(rows) == 1
    row = rows[0]
    assert row.title == "Right article"
    assert row.external_id == f"{BIZ}:2651057510:1"
    assert row.metadata["delivery_mode"] == "WECHAT_ARTICLE"
    assert "完整正文第二段" in row.metadata["wechat_feed_html"]
    assert row.metadata["wechat_identity_key"] == f"wechat:{BIZ}:2651057510:1"


def test_wechat_challenge_is_never_article_truth():
    html = "<html><body>环境异常 当前环境异常，完成验证后即可继续访问。去验证</body></html>"
    assert is_wechat_challenge(
        "https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha?poc_token=x", html
    ) is True


def _challenge_response(url: str):
    request = httpx.Request("GET", url)
    return httpx.Response(
        200,
        request=request,
        text="<html><body>环境异常，完成验证后即可继续访问。去验证</body></html>",
    )

def test_wechat_connector_uses_full_mirror_snapshot_without_changing_canonical_url(monkeypatch):
    monkeypatch.setattr(httpx.Client, "get", lambda self, url, **kwargs: _challenge_response(url))
    monkeypatch.setattr("app.services.media_cache.cache_remote_media", lambda url: f"/api/media/{abs(hash(url))}")

    fallback = """
    <div>
      <p>这是完整正文的第一段，足够长以通过完整性检查，并用于测试微信公众号镜像兜底。</p>
      <p style="text-align:center"><span style="font-size:16px;font-weight:bold">真正的章节标题示例</span></p>
      <p>这是章节下面的第二段正文，用于确认结构化正文不会退化成一个短摘要。微信公众号正文往往包含很多段落，因此这里继续补充测试文字，确保完整性门槛验证的是文章而不是验证页。再补充一段关于人工智能系统、模型能力和实际应用的测试内容。</p>
      <p><span>Harne</span><span>ss</span> 与 <span>1</span><span>50</span> 万小时数据不应被 span 边界插入假空格。</p>
      <h3>栏目标题<span><img src="https://wechat2rss.xlab.app/img-proxy/?k=decor&amp;u=https%3A%2F%2Fmmbiz.qpic.cn%2Fdecor.jpg" /></span></h3>
      <p><img src="https://wechat2rss.xlab.app/img-proxy/?k=x&amp;u=https%3A%2F%2Fmmbiz.qpic.cn%2Fa.jpg" /></p>
    </div>
    """
    normalized = WechatArticleConnector().ingest(
        ARTICLE,
        title="测试微信文章",
        account="机器之心",
        biz=BIZ,
        published_at=None,
        fallback_html=fallback,
        feed_url="https://example.com/feed.xml",
    )
    assert normalized.canonical_url == ARTICLE
    assert normalized.publisher == "机器之心"
    assert normalized.raw_metadata["wechat_fetch_mode"] == "wechat2rss-fallback-v1"
    assert normalized.raw_metadata["wechat_mirror_is_independent_evidence"] is False
    headings = [b for b in normalized.raw_metadata["article_blocks"] if b["type"] == "heading"]
    assert [b["text"] for b in headings] == ["真正的章节标题示例", "栏目标题"]
    image = normalized.raw_metadata["article_images"][0]
    assert image["url"] == "https://mmbiz.qpic.cn/a.jpg"
    assert image["original_url"] == "https://mmbiz.qpic.cn/a.jpg"
    assert "wechat2rss.xlab.app/img-proxy/" in image["transport_url"]
    assert image["transport"] == "wechat2rss-image-proxy"
    assert "Harness 与 150 万小时数据" in normalized.content_text
    assert "Harne ss" not in normalized.content_text
    assert normalized.raw_metadata["wechat_heading_decorative_images_dropped"] == 1
    assert all("decor.jpg" not in (x.get("url") or "") for x in normalized.raw_metadata["article_images"])

def test_wechat_direct_mpvideo_data_src_becomes_embed(monkeypatch):
    direct_html = """
    <html><body>
      <h1 id="activity-name">微信视频文章</h1><span id="js_name">机器之心</span>
      <div id="js_content">
        <p>这是一段足够长的正文，用来测试微信公众号原文直抓以及视频位置锚定。这里增加更多真实文章长度的模拟文本，确保完整性检查不会把这个 fixture 当成摘要或环境验证页面。</p>
        <p><iframe class="video_iframe"
          data-src="https://mp.weixin.qq.com/mp/readtemplate?t=pages/video_player_tmpl&amp;action=mpvideo&amp;auto=0&amp;vid=wxv_12345"
          data-mpvid="wxv_12345"></iframe></p>
        <p>视频之后还有正文，因此整个文章显然不是环境验证页。这里继续补充正文内容，模拟正常公众号文章在视频之后还有解释、结论和延伸讨论的情况。</p>
      </div>
    </body></html>
    """
    def fake_get(self, url, **kwargs):
        return httpx.Response(200, request=httpx.Request("GET", url), text=direct_html)
    monkeypatch.setattr(httpx.Client, "get", fake_get)
    normalized = WechatArticleConnector().ingest(
        ARTICLE,
        title="微信视频文章",
        account="机器之心",
        biz=BIZ,
        published_at=None,
        fallback_html=None,
        feed_url=None,
    )
    assert normalized.raw_metadata["wechat_fetch_mode"] == "direct"
    embeds = [a for a in normalized.raw_metadata["media_assets"] if a["type"] == "EMBED"]
    assert len(embeds) == 1
    assert embeds[0]["provider"] == "WECHAT_VIDEO"
    assert "vid=wxv_12345" in embeds[0]["embed_url"]
