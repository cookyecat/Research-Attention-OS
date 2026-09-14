from bs4 import BeautifulSoup

from app.connectors.arxiv import _abs_metadata, _paper_body_html, parse_arxiv_ref


def test_parse_arxiv_ref_accepts_abs_html_and_version():
    assert parse_arxiv_ref("https://arxiv.org/abs/2609.12035") == ("2609.12035", None)
    assert parse_arxiv_ref("https://arxiv.org/html/2609.12035v2") == ("2609.12035", "v2")
    assert parse_arxiv_ref("https://example.com/abs/2609.12035") is None


def test_abs_metadata_reads_citation_fields_and_rejects_share_logo_as_paper_visual():
    soup = BeautifulSoup("""
    <html><head>
      <meta name="citation_title" content="A Better Paper" />
      <meta name="citation_author" content="Ada Example" />
      <meta name="citation_author" content="Grace Example" />
      <meta name="citation_date" content="2026/09/10" />
      <meta name="citation_pdf_url" content="https://arxiv.org/pdf/2609.12035" />
      <meta name="citation_abstract" content="Useful abstract." />
      <meta property="og:url" content="https://arxiv.org/abs/2609.12035v3" />
      <meta property="og:image" content="/static/arxiv-logo.png" />
    </head><body>
      <span class="primary-subject">Artificial Intelligence (cs.AI)</span>
      <div class="submission-history">[v1] Thu, 10 Sep 2026</div>
    </body></html>
    """, "lxml")
    meta = _abs_metadata(soup, "2609.12035")
    assert meta["title"] == "A Better Paper"
    assert meta["authors"] == ["Ada Example", "Grace Example"]
    assert meta["abstract"] == "Useful abstract."
    assert meta["version"] == "v3"
    assert meta["primary_category"] == "Artificial Intelligence (cs.AI)"


def test_paper_body_preserves_sections_math_figures_and_bibliography(monkeypatch):
    monkeypatch.setattr("app.connectors.arxiv.cache_remote_media", lambda url: "/api/media/cached.png")
    soup = BeautifulSoup("""
    <article class="ltx_document">
      <section class="ltx_section" id="S1">
        <h2>1 Introduction</h2>
        <p>Body <math display="inline"><mi>x</mi><mo>=</mo><mn>1</mn></math>.</p>
        <figure class="ltx_figure"><img src="paper/fig1.png" alt="Figure one" /><figcaption>Figure 1: Useful diagram.</figcaption></figure>
      </section>
      <section class="ltx_section" id="S2"><h2>2 Method</h2><p>Method body.</p></section>
      <div class="ltx_bibliography"><h2>References</h2><ul><li>Reference A</li></ul></div>
    </article>
    """, "lxml")
    body, sections, figures = _paper_body_html(soup, base_url="https://arxiv.org/html/2609.12035v1")
    assert sections == [{"id": "S1", "title": "1 Introduction"}, {"id": "S2", "title": "2 Method"}]
    assert "<math" in body and "References" in body
    assert '/api/media/cached.png' in body
    assert figures[0]["url"] == "https://arxiv.org/html/paper/fig1.png"
    assert figures[0]["caption"] == "Figure 1: Useful diagram."
