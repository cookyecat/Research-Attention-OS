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
    assert metadata["article_images"] == []
    assert metadata["parser"] == "url-html-v3-visual-structure"


def test_extract_readable_preserves_semantic_article_figures_without_duplicating_hero():
    html = """
    <html><head><title>Figures</title><meta property="og:image" content="/media/hero.jpg" /></head><body>
      <p>Paragraph before the diagram.</p>
      <figure><img src="/media/diagram.png" alt="System diagram" /><figcaption>How the system works.</figcaption></figure>
      <figure><img src="/media/hero.jpg" alt="duplicate hero" /></figure>
      <p>Paragraph after the diagram.</p>
    </body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    assert metadata["article_images"] == [{
        "url": "https://example.com/media/diagram.png",
        "alt": "System diagram",
        "caption": "How the system works.",
        "context_text": "Paragraph before the diagram.",
    }]
