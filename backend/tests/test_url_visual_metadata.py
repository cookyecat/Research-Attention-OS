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
    assert metadata["parser"] == "url-html-v4-media-assets"


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


def test_extract_readable_preserves_embeds_and_native_video_without_poster_pollution():
    html = """
    <html><head><title>Media story</title></head><body>
      <p>Paragraph before the YouTube explainer.</p>
      <iframe src="https://www.youtube.com/embed/abc123?rel=0" title="Explainer"></iframe>
      <p>Paragraph before the native animation.</p>
      <figure>
        <img src="/fallback.jpg" aria-hidden="true" />
        <video data-poster-is-fallback="true" poster="/fallback.jpg"><source data-src="https://cdn.example.com/figure.webm#t=0.1" type="video/webm" /></video>
        <figcaption>Animated explanation.</figcaption>
      </figure>
    </body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    assert metadata["article_images"] == []
    assets = metadata["media_assets"]
    assert assets[0]["type"] == "EMBED"
    assert assets[0]["provider"] == "YOUTUBE"
    assert assets[0]["embed_url"] == "https://www.youtube.com/embed/abc123?rel=0"
    assert assets[0]["context_text"] == "Paragraph before the YouTube explainer."
    assert assets[1]["type"] == "VIDEO"
    assert assets[1]["url"] == "https://cdn.example.com/figure.webm#t=0.1"
    assert assets[1]["mime_type"] == "video/webm"
    assert assets[1]["poster_url"] is None
    assert assets[1]["caption"] == "Animated explanation."
    assert assets[1]["context_text"] == "Paragraph before the native animation."
