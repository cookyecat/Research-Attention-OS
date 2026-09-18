import json

from app.services.social_adapters import _weibo_preview_needs_hydration, parse_weibo_cards, parse_x_syndication_html


def test_parse_x_public_syndication_payload():
    payload = {
        "props": {"pageProps": {"timeline": {"entries": [
            {"type": "tweet", "content": {"tweet": {
                "id_str": "123", "full_text": "Hello &gt; world",
                "created_at": "Mon Sep 14 10:00:00 +0000 2026",
                "favorite_count": 4, "retweet_count": 2, "reply_count": 1, "quote_count": 0,
                "entities": {"media": []},
            }}}
        ]}}}
    }
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'
    rows = parse_x_syndication_html(html, handle="example")
    assert len(rows) == 1
    assert rows[0].external_id == "123"
    assert rows[0].metadata["content_text"] == "Hello > world"
    assert rows[0].ref == "https://x.com/example/status/123"


def test_parse_weibo_public_cards():
    data = {"data": {"cards": [{"mblog": {
        "id": "456", "bid": "AbCd", "text": "<b>公开</b> 微博",
        "created_at": "Mon Sep 14 20:00:00 +0800 2026",
        "user": {"screen_name": "测试用户"}, "attitudes_count": 7,
        "reposts_count": 2, "comments_count": 3, "pics": [],
    }}]}}
    rows = parse_weibo_cards(data, uid="1912085257")
    assert len(rows) == 1
    assert rows[0].metadata["social_author"] == "测试用户"
    assert rows[0].metadata["content_text"] == "公开 微博"
    assert rows[0].ref == "https://weibo.com/1912085257/AbCd"

def test_parse_weibo_public_long_text_prefers_hydrated_body_and_preserves_paragraphs():
    data = {"data": {"cards": [{"mblog": {
        "id": "789", "bid": "Long1",
        "text": "预览 ...<a href=\"/status/789\">全文</a>",
        "textLength": 120, "isLongText": True,
        "created_at": "Mon Sep 14 20:00:00 +0800 2026",
        "user": {"screen_name": "长文用户"}, "pics": [],
    }}]}}
    long_texts = {"789": "第一段<br /><br />第二段 <b>完整正文</b>"}
    rows = parse_weibo_cards(data, uid="1912085257", long_texts=long_texts)
    assert len(rows) == 1
    assert rows[0].metadata["content_text"] == "第一段\n\n第二段 完整正文"
    assert rows[0].metadata["weibo_is_long_text"] is True
    assert rows[0].metadata["weibo_long_text_hydrated"] is True
    assert "全文" not in rows[0].metadata["content_text"]



def test_parse_weibo_public_media_gallery_from_hydrated_status():
    data = {"data": {"cards": [{"mblog": {
        "id": "900", "bid": "Media1", "text": "多图微博",
        "created_at": "Mon Sep 14 20:00:00 +0800 2026",
        "user": {"screen_name": "媒体用户"},
        "pics": [{"pid": "p1", "large": {"url": "https://wx1.sinaimg.cn/mw2000/p1.jpg"}}],
    }}]}}
    media_details = {"900": {
        "id": "900",
        "pics": [
            {"pid": "p1", "large": {"url": "https://wx1.sinaimg.cn/mw2000/p1.jpg", "geo": {"width": "1000", "height": "1600"}}},
            {"pid": "p2", "large": {"url": "https://wx2.sinaimg.cn/mw2000/p2.jpg", "geo": {"width": "1200", "height": "900"}}},
        ],
    }}
    rows = parse_weibo_cards(data, uid="1912085257", media_details=media_details)
    assets = rows[0].metadata["media_assets"]
    assert [asset["type"] for asset in assets] == ["IMAGE", "IMAGE"]
    assert [asset["media_id"] for asset in assets] == ["p1", "p2"]
    assert rows[0].metadata["hero_image_url"].endswith("/p1.jpg")
    assert rows[0].metadata["weibo_media_hydrated"] is True


def test_parse_weibo_public_video_prefers_higher_quality_candidate():
    data = {"data": {"cards": [{"mblog": {
        "id": "901", "bid": "Video1", "text": "视频微博",
        "created_at": "Mon Sep 14 20:00:00 +0800 2026",
        "user": {"screen_name": "视频用户"}, "page_info": {"type": "video"},
    }}]}}
    media_details = {"901": {
        "id": "901",
        "page_info": {
            "object_id": "video-901",
            "media_info": {
                "media_id": "m901",
                "urls": {
                    "mp4_720p_mp4": "https://f.video.weibocdn.com/a/video_720.mp4",
                    "mp4_1080p_mp4": "https://f.video.weibocdn.com/a/video_1080.mp4",
                },
            },
        },
    }}
    rows = parse_weibo_cards(data, uid="1912085257", media_details=media_details)
    assets = rows[0].metadata["media_assets"]
    assert len(assets) == 1
    assert assets[0]["type"] == "VIDEO"
    assert "1080" in assets[0]["url"]


def test_weibo_preview_full_text_marker_triggers_hydration_without_flag():
    mblog = {"text": "一段被截断的内容 ... <a href='/status/x'>全文</a>", "isLongText": False}
    assert _weibo_preview_needs_hydration(mblog) is True


def test_weibo_preview_without_truncation_does_not_force_detail_fetch():
    mblog = {"text": "这是一条完整的普通微博。", "isLongText": False}
    assert _weibo_preview_needs_hydration(mblog) is False
