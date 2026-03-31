import pytest

import app.scrapers  # noqa: F401 — triggers @register decorators
from app.scrapers.base import ProviderLinks, SearchResult, get_scraper
from app.scrapers.darkiworld import DarkiworldScraper
from app.scrapers.wawacity import WawacityScraper

# ---------------------------------------------------------------------------
# Minimal HTML fixture that matches the wawacity page structure
# ---------------------------------------------------------------------------

_WAWACITY_HTML = """
<html><body>
<div class="wa-post-detail-item">
  <img src="/img/inception.jpg">
  <div class="wa-sub-block">
    <div>
      <div class="wa-sub-block-title">
        <a href="/?p=films&amp;id=1-inception">Inception [BLU-RAY 1080p]
          <i class="flag-icon flag-fr"></i>
        </a>
      </div>
      <span>Ann\u00e9e:</span><b>2010</b>
    </div>
  </div>
</div>
<div class="wa-post-detail-item">
  <img src="/img/dune.jpg">
  <div class="wa-sub-block">
    <div>
      <div class="wa-sub-block-title">
        <a href="/?p=films&amp;id=2-dune">Dune [WEB-DL 4K]
          <i class="flag-icon flag-multi"></i>
        </a>
      </div>
      <span>Ann\u00e9e:</span><b>2021</b>
    </div>
  </div>
</div>
</body></html>
""".encode("utf-8")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_get_scraper_wawacity():
    scraper = get_scraper("wawacity")
    assert isinstance(scraper, WawacityScraper)


def test_get_scraper_darkiworld():
    scraper = get_scraper("darkiworld")
    assert isinstance(scraper, DarkiworldScraper)


def test_get_scraper_unknown_raises():
    with pytest.raises(KeyError, match="unknown_source"):
        get_scraper("unknown_source")


# ---------------------------------------------------------------------------
# WawacityScraper._parse_results
# ---------------------------------------------------------------------------


def test_parse_results_returns_search_results():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=10)

    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)


def test_parse_results_extracts_title_and_quality():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=10)

    assert results[0].title == "Inception"
    assert results[0].quality == "BLU-RAY 1080p"
    assert results[1].title == "Dune"
    assert results[1].quality == "WEB-DL 4K"


def test_parse_results_extracts_year():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=10)

    assert results[0].year == 2010
    assert results[1].year == 2021


def test_parse_results_extracts_language():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=10)

    assert results[0].language == "🇫🇷"
    assert results[1].language == "🇪🇺"


def test_parse_results_sets_source():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=10)

    assert all(r.source == "wawacity" for r in results)


def test_parse_results_respects_limit():
    scraper = WawacityScraper()
    results = scraper._parse_results(_WAWACITY_HTML, limit=1)

    assert len(results) == 1


def test_parse_results_empty_html():
    scraper = WawacityScraper()
    results = scraper._parse_results("<html><body></body></html>".encode(), limit=10)

    assert results == []


# ---------------------------------------------------------------------------
# WawacityScraper.search — mock aiohttp
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_results(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 200

        async def read(self):
            return _WAWACITY_HTML

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    scraper = WawacityScraper()
    results = await scraper.search("inception", "films", limit=10)

    assert len(results) == 2
    assert results[0].title == "Inception"


@pytest.mark.asyncio
async def test_search_returns_empty_on_http_error(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 503

        async def read(self):
            return b""

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def get(self, *args, **kwargs):
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    scraper = WawacityScraper()
    results = await scraper.search("inception", "films")

    assert results == []


# ---------------------------------------------------------------------------
# DarkiworldScraper stubs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_darkiworld_search_raises_not_implemented():
    scraper = DarkiworldScraper()
    with pytest.raises(NotImplementedError):
        await scraper.search("test", "films")


@pytest.mark.asyncio
async def test_darkiworld_get_provider_links_raises_not_implemented():
    scraper = DarkiworldScraper()
    with pytest.raises(NotImplementedError):
        await scraper.get_provider_links("https://example.com", [])
