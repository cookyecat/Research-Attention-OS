from app.connectors.url import _extract_readable


def test_extract_readable_preserves_standard_hero_image_metadata():
    html = """
    <html><head>
      <title>Example story</title>
      <link rel="canonical" href="/story" />
      <meta property="og:image" content="/media/hero.jpg" />
      <meta property="og:image:alt" content="A useful visual description." />
    </head><body><p>Readable article body.</p></body></html>
    """

    title, text, metadata = _extract_readable(html, "https://example.com/original")

    assert title == "Example story"
    assert "Readable article body" in text
    assert metadata["hero_image_url"] == "https://example.com/media/hero.jpg"
    assert metadata["hero_image_alt"] == "A useful visual description."
    assert metadata["parser"] == "url-html-v2-visual-metadata"
