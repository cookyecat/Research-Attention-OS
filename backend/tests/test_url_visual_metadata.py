from app.connectors.url import _extract_readable, _insert_missing_dom_images


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
    assert metadata["article_structure_version"] == "structured-blocks-v3-tables"
    assert metadata["parser"] == "url-html-v9-publisher-adapters"


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


def test_extract_readable_preserves_headings_lists_and_images_outside_figures():
    html = """
    <html><head><title>Structured story</title></head><body>
      <article><div class="entry-content">
        <p>Intro paragraph.</p>
        <ul><li>First result</li><li>Second result</li></ul>
        <h2>Important Section</h2>
        <p>Section paragraph.</p>
        <figure><img src="/media/chart-one.jpg" /><figcaption>Chart one.</figcaption></figure>
        <p><img src="/media/chart-two.jpg" /></p>
      </div></article>
      <aside><img src="/media/sidebar.jpg" /></aside>
    </body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    assert [image["url"] for image in metadata["article_images"]] == [
        "https://example.com/media/chart-one.jpg",
        "https://example.com/media/chart-two.jpg",
    ]
    assert metadata["article_blocks"] == [
        {"type": "paragraph", "text": "Intro paragraph."},
        {"type": "list", "ordered": False, "items": [
            {"text": "First result", "lead": None},
            {"text": "Second result", "lead": None},
        ]},
        {"type": "heading", "level": 2, "text": "Important Section"},
        {"type": "paragraph", "text": "Section paragraph."},
        {"type": "image", "url": "https://example.com/media/chart-one.jpg", "alt": None, "caption": "Chart one.", "context_text": "Section paragraph."},
        {"type": "image", "url": "https://example.com/media/chart-two.jpg", "alt": None, "caption": None, "context_text": "Section paragraph."},
    ]


def test_structured_blocks_drop_publisher_chrome():
    html = """
    <html><body><article>
      <p>Real opening paragraph.</p>
      <div class="newsletter"><p>Subscribe to our newsletter.</p></div>
      <div class="duet--article--article-byline"><img src="/author.jpg?w=96" alt="Author" /></div>
      <h2>Real Section</h2>
      <p>Real body paragraph.</p>
      <div class="duet--article--related"><h3>Related</h3><ul><li>Another story</li></ul></div>
      <p><img src="/body.jpg" alt="Body evidence" /></p>
    </article></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    rendered = " ".join(
        block.get("text", "")
        for block in metadata["article_blocks"]
        if block.get("type") in {"paragraph", "heading"}
    )
    assert "Real opening paragraph." in rendered
    assert "Real Section" in rendered
    assert "Real body paragraph." in rendered
    assert "Subscribe to our newsletter." not in rendered
    assert "Related" not in rendered
    assert [image["url"] for image in metadata["article_images"]] == ["https://example.com/body.jpg"]


def test_extract_readable_anchors_embed_inside_empty_paragraph_to_nearby_semantic_text():
    html = """
    <html><body><article><div class="entry-content">
      <p>Intro paragraph.</p>
      <h2>Gameplay section</h2>
      <p><iframe src="https://www.youtube.com/embed/example" title="Gameplay trailer"></iframe></p>
      <p>Paragraph after the video.</p>
    </div></article></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    embeds = [asset for asset in metadata["media_assets"] if asset["type"] == "EMBED"]
    assert len(embeds) == 1
    assert embeds[0]["title"] == "Gameplay trailer"
    assert embeds[0]["context_text"] == "Gameplay section"


def test_explicit_article_body_wins_over_outer_page_chrome():
    html = """
    <html><body>
      <p>Browser compatibility warning outside the article.</p>
      <article><div class="c-article-body main-content">
        <p>Real opening.</p>
        <h2>Real section</h2>
        <p>Real body.</p>
        <div class="app-access-wall"><h2>Log in to continue</h2><p>Subscribe now.</p></div>
      </div></article>
    </body></html>
    """
    _, text, metadata = _extract_readable(html, "https://example.com/story")
    assert text == "Real opening.\nReal section\nReal body."
    assert [block["type"] for block in metadata["article_blocks"]] == ["paragraph", "heading", "paragraph"]
    assert "compatibility" not in text.lower()
    assert "log in" not in text.lower()


def test_extract_readable_preserves_semantic_tables():
    html = """
    <html><body><main>
      <p>Before table.</p>
      <table><tbody>
        <tr><td>Signal</td><td>Question it answers</td></tr>
        <tr><td>Profiler</td><td>Where does time go?</td></tr>
        <tr><td>Verdict</td><td>Did this help?</td></tr>
      </tbody></table>
      <p>After table.</p>
    </main></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    tables = [block for block in metadata["article_blocks"] if block["type"] == "table"]
    assert len(tables) == 1
    assert tables[0]["headers"] == ["Signal", "Question it answers"]
    assert tables[0]["rows"] == [["Profiler", "Where does time go?"], ["Verdict", "Did this help?"]]


def test_structured_blocks_trim_publisher_recirculation_tail():
    html = """
    <html><body><main>
      <p>Article body.</p>
      <h2>Related Content</h2>
      <p>Another story that should not enter the reader.</p>
    </main></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    rendered = " ".join(str(block.get("text") or "") for block in metadata["article_blocks"])
    assert "Article body." in rendered
    assert "Related Content" not in rendered
    assert "Another story" not in rendered


def test_structured_blocks_ignore_image_modal_duplicates():
    html = """
    <html><body><main>
      <p>Real article paragraph.</p>
      <p><img src="/media/chart.width-1250.png" alt="Real chart" /></p>
      <div class="image-modal"><div class="modal-slide">
        <img src="/media/chart.png" alt="Zoom copy" />
      </div></div>
    </main></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    urls = [image["url"] for image in metadata["article_images"]]
    assert urls == ["https://example.com/media/chart.width-1250.png"]
    assert sum(1 for block in metadata["article_blocks"] if block.get("type") == "image") == 1


def test_missing_dom_image_uses_high_similarity_context_instead_of_article_tail():
    blocks = [
        {"type": "paragraph", "text": "Opening paragraph."},
        {"type": "paragraph", "text": "In ToolGrad, we introduce an alternative solution paradigm with an answer-first workflow."},
        {"type": "paragraph", "text": "Closing paragraph."},
    ]
    image = {
        "url": "https://example.com/toolgrad.png",
        "context_text": "In  ToolGrad , we introduce an alternative solution paradigm with an answer-first workflow.",
    }
    out, images = _insert_missing_dom_images(list(blocks), [], [image])
    assert [block["type"] for block in out] == ["paragraph", "paragraph", "image", "paragraph"]
    assert images == [image]


def test_visible_title_hero_outranks_social_card_image():
    html = """
    <html><head><meta property="og:image" content="/social-card.jpg" /></head><body>
      <section class="basic-hero"><h1>Article title</h1><img src="/actual-hero.png" alt="Actual article hero" /></section>
      <main><p>Article body.</p></main>
    </body></html>
    """
    _, _, metadata = _extract_readable(html, "https://example.com/story")
    assert metadata["hero_image_url"] == "https://example.com/actual-hero.png"
    assert metadata["hero_image_alt"] == "Actual article hero"
    assert all(image["url"] != metadata["hero_image_url"] for image in metadata["article_images"])


def test_layout_with_sidebar_does_not_erase_semantic_article_headings():
    html = """
    <html><body>
      <article class="post-with-sidebar grid grid-cols-4">
        <div class="nvidia-content"><div class="entry-content">
          <p>Opening paragraph.</p>
          <h2>From Custom Silicon to Rack-Scale Deployment</h2>
          <p>Body paragraph.</p>
          <h2>NVLink Fusion Integrates XPUs Into AI Factories</h2>
          <p>Closing paragraph.</p>
        </div></div>
        <aside class="nvidia-sidebar"><h3>Recent News</h3></aside>
      </article>
    </body></html>
    """
    _, _, metadata = _extract_readable(html, "https://blogs.nvidia.com/blog/example/")
    headings = [block["text"] for block in metadata["article_blocks"] if block["type"] == "heading"]
    assert headings == [
        "From Custom Silicon to Rack-Scale Deployment",
        "NVLink Fusion Integrates XPUs Into AI Factories",
    ]
    rendered = " ".join(str(block.get("text") or "") for block in metadata["article_blocks"])
    assert "Recent News" not in rendered


def test_openai_publisher_body_preserves_toc_headings_and_excludes_page_tail():
    html = """
    <html><head><title>OpenAI story | OpenAI</title></head><body>
      <article>
        <p data-article-hero-copy-region="subhead">Hero summary.</p>
        <div data-toc-content>
          <p>Opening paragraph.</p>
          <h2>First section</h2>
          <p>First section body.</p>
          <h2>Second section</h2>
          <h3>Nested section</h3>
          <ul><li>One result</li><li>Two results</li></ul>
        </div>
        <section><h2>Author</h2><p>OpenAI</p></section>
        <div><h2>Keep reading</h2><img src="/related.png" /></div>
      </article>
    </body></html>
    """
    _, text, metadata = _extract_readable(html, "https://openai.com/index/example/")
    headings = [block for block in metadata["article_blocks"] if block["type"] == "heading"]
    assert [(block["level"], block["text"]) for block in headings] == [
        (2, "First section"), (2, "Second section"), (3, "Nested section")
    ]
    assert metadata["article_blocks"][0] == {"type": "paragraph", "text": "Hero summary."}
    assert "Author" not in text
    assert "Keep reading" not in text
    assert metadata["article_images"] == []


def test_openai_publisher_body_keeps_native_video_when_present():
    html = """
    <html><body><article>
      <div data-toc-content>
        <h2>Demo</h2>
        <p>Watch the workflow.</p>
        <video poster="/poster.jpg"><source src="https://cdn.example.com/demo.mp4" type="video/mp4" /></video>
      </div>
      <div><h2>Keep reading</h2></div>
    </article></body></html>
    """
    _, _, metadata = _extract_readable(html, "https://openai.com/index/example/")
    videos = [asset for asset in metadata["media_assets"] if asset["type"] == "VIDEO"]
    assert len(videos) == 1
    assert videos[0]["url"] == "https://cdn.example.com/demo.mp4"
    assert videos[0]["poster_url"] == "https://openai.com/poster.jpg"
    assert videos[0]["context_text"] == "Watch the workflow."
