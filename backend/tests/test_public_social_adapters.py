import json

from app.services.social_adapters import parse_weibo_cards, parse_x_syndication_html


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
