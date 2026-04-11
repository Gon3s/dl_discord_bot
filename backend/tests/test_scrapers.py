import pytest

import app.scrapers  # noqa: F401 — triggers @register decorators
from app.scrapers.base import Episode, ProviderLinks, SearchResult, get_scraper
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
# DarkiworldScraper — JSON fixtures
# ---------------------------------------------------------------------------

_DW_SEARCH_JSON = {
    "pagination": {
        "current_page": 1,
        "data": [
            {
                "id": 42,
                "name": "Inception",
                "slug": "inception-2010",
                "type": "movie",
                "year": 2010,
                "poster": "images/inception.jpg",
                "language": "fr",
            },
            {
                "id": 43,
                "name": "Interstellar",
                "slug": "interstellar-2014",
                "type": "movie",
                "year": 2014,
                "poster": "https://cdn.example.com/interstellar.jpg",
                "language": "multi",
            },
        ],
        "next_page": None,
        "per_page": 15,
    }
}

_DW_SEASONS_JSON = {
    "pagination": {
        "data": [
            {"id": 10, "number": 1},
            {"id": 11, "number": 2},
        ]
    }
}

_DW_EPISODES_JSON = {
    "pagination": {
        "data": [
            {"episode_number": 1, "name": "Pilot"},
            {"episode_number": 2, "name": "Second Episode"},
        ]
    }
}


# ---------------------------------------------------------------------------
# DarkiworldScraper._parse_search_response
# ---------------------------------------------------------------------------


def test_dw_parse_search_returns_results():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)


def test_dw_parse_search_extracts_title_and_year():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert results[0].title == "Inception"
    assert results[0].year == 2010
    assert results[1].title == "Interstellar"
    assert results[1].year == 2014


def test_dw_parse_search_builds_url_with_id():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert "/titles/42/" in results[0].url
    assert "/titles/43/" in results[1].url


def test_dw_parse_search_poster_relative_prefixed():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert results[0].poster_url is not None
    assert results[0].poster_url.startswith("http")
    assert "images/inception.jpg" in results[0].poster_url


def test_dw_parse_search_poster_absolute_kept():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert results[1].poster_url == "https://cdn.example.com/interstellar.jpg"


def test_dw_parse_search_respects_limit():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=1)
    assert len(results) == 1


def test_dw_parse_search_sets_source():
    scraper = DarkiworldScraper()
    results = scraper._parse_search_response(_DW_SEARCH_JSON, limit=10)
    assert all(r.source == "darkiworld" for r in results)


# ---------------------------------------------------------------------------
# DarkiworldScraper.get_episodes — mock aiohttp (seasons + episodes)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dw_get_episodes_returns_episodes(monkeypatch):
    import aiohttp

    call_count = 0

    class FakeResponse:
        def __init__(self, data):
            self._data = data
            self.status = 200
            self.content_type = "application/json"

        async def json(self):
            return self._data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "/seasons" in url and "/episodes" not in url:
                return FakeResponse(_DW_SEASONS_JSON)
            return FakeResponse(_DW_EPISODES_JSON)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    scraper = DarkiworldScraper()
    DarkiworldScraper._cookies = {"laravel_session": "fake"}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    episodes = await scraper.get_episodes("https://dd.darkiworld16.com/titles/999/show")
    assert len(episodes) == 4  # 2 seasons × 2 episodes each
    assert episodes[0].number == 1
    assert "S01E01" in episodes[0].title
    assert "Pilot" in episodes[0].title

    DarkiworldScraper._cookies = None


@pytest.mark.asyncio
async def test_dw_get_episodes_returns_empty_on_http_error(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 503
        content_type = "application/json"

        async def json(self):
            return {}

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

    scraper = DarkiworldScraper()
    DarkiworldScraper._cookies = {"laravel_session": "fake"}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    episodes = await scraper.get_episodes("https://dd.darkiworld16.com/titles/999/show")
    assert episodes == []

    DarkiworldScraper._cookies = None


@pytest.mark.asyncio
async def test_dw_get_episodes_returns_empty_for_bad_url():
    scraper = DarkiworldScraper()
    episodes = await scraper.get_episodes("https://dd.darkiworld16.com/not-a-title")
    assert episodes == []


# ---------------------------------------------------------------------------
# DarkiworldScraper.search — mock aiohttp
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dw_search_returns_results(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 200
        content_type = "application/json"

        async def json(self):
            return _DW_SEARCH_JSON

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

    scraper = DarkiworldScraper()
    DarkiworldScraper._cookies = {"laravel_session": "fake"}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    results = await scraper.search("inception", "films", limit=10)
    assert len(results) == 2
    assert results[0].title == "Inception"

    DarkiworldScraper._cookies = None


@pytest.mark.asyncio
async def test_dw_search_returns_empty_on_http_error(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 503
        content_type = "application/json"

        async def json(self):
            return {}

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

    scraper = DarkiworldScraper()
    DarkiworldScraper._cookies = {"laravel_session": "fake"}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    results = await scraper.search("inception", "films")
    assert results == []

    DarkiworldScraper._cookies = None


@pytest.mark.asyncio
async def test_dw_search_invalidates_session_on_html_response(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 200
        content_type = "text/html"

        async def json(self):
            return {}

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

    scraper = DarkiworldScraper()
    DarkiworldScraper._cookies = {"laravel_session": "expired"}
    monkeypatch.setattr(aiohttp, "ClientSession", lambda **kwargs: FakeSession())

    results = await scraper.search("inception", "films")
    assert results == []
    assert DarkiworldScraper._cookies is None


# ---------------------------------------------------------------------------
# WawacityScraper._parse_episodes
# ---------------------------------------------------------------------------

_DDLLINKS_HTML = """
<html><body>
<table id="DDLLinks">
  <tr class="link-row">
    <td><a href="https://dl-protect.link/season-pack">Lien premium</a></td>
    <td class="text-center">Anonyme</td><td class="text-center">1 Go</td><td></td>
  </tr>
  <tr class="title episode-title active">
    <td colspan="6"><p>Breaking Bad - Saison 1<i> - VOSTFR HD</i> - Épisode 1en téléchargement sur wawa city</p></td>
  </tr>
  <tr class="link-row">
    <td><a href="https://dl-protect.link/ep1-rapid">Lien 1:Télécharger</a></td>
    <td class="text-center">Rapidgator</td><td class="text-center">250 Mo</td><td></td>
  </tr>
  <tr class="link-row">
    <td><a href="https://dl-protect.link/ep1-nitro">Lien 2:Télécharger</a></td>
    <td class="text-center">Nitroflare</td><td class="text-center">250 Mo</td><td></td>
  </tr>
  <tr class="title episode-title active">
    <td colspan="6"><p>Breaking Bad - Saison 1<i> - VOSTFR HD</i> - Épisode 2en téléchargement sur wawa city</p></td>
  </tr>
  <tr class="link-row">
    <td><a href="https://dl-protect.link/ep2-rapid">Lien 1:Télécharger</a></td>
    <td class="text-center">Rapidgator</td><td class="text-center">250 Mo</td><td></td>
  </tr>
</table>
</body></html>
"""


def test_parse_episodes_returns_two_episodes():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    assert len(episodes) == 2


def test_parse_episodes_correct_numbers():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    assert episodes[0].number == 1
    assert episodes[1].number == 2


def test_parse_episodes_correct_titles():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    assert episodes[0].title == "Épisode 1"
    assert episodes[1].title == "Épisode 2"


def test_parse_episodes_provider_links():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    providers = [pl.provider for pl in episodes[0].provider_links]
    assert "Rapidgator" in providers
    assert "Nitroflare" in providers


def test_parse_episodes_dl_protect_urls():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    rapid = next(pl for pl in episodes[0].provider_links if pl.provider == "Rapidgator")
    assert rapid.urls[0] == "https://dl-protect.link/ep1-rapid"


def test_parse_episodes_filters_providers():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, ["Rapidgator"])
    for ep in episodes:
        assert all(pl.provider == "Rapidgator" for pl in ep.provider_links)


def test_parse_episodes_skips_pre_episode_link_row():
    """The first link-row (before any episode-title) is the season pack — must be skipped."""
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes(_DDLLINKS_HTML, [])
    all_urls = [pl.urls[0] for ep in episodes for pl in ep.provider_links]
    assert "https://dl-protect.link/season-pack" not in all_urls


def test_parse_episodes_empty_html():
    scraper = WawacityScraper()
    episodes = scraper._parse_episodes("<html><body></body></html>", [])
    assert episodes == []


@pytest.mark.asyncio
async def test_get_episodes_returns_episodes(monkeypatch):
    import aiohttp

    class FakeResponse:
        status = 200

        async def read(self):
            return _DDLLINKS_HTML.encode()

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
    episodes = await scraper.get_episodes("https://www.wawacity.pizza?p=serie&id=1")

    assert len(episodes) == 2
    assert all(isinstance(ep, Episode) for ep in episodes)


@pytest.mark.asyncio
async def test_get_episodes_returns_empty_on_http_error(monkeypatch):
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
    episodes = await scraper.get_episodes("https://www.wawacity.pizza?p=serie&id=1")

    assert episodes == []
