from unittest.mock import AsyncMock, MagicMock, patch

from app.models.orm import Download, History
from app.scrapers.base import Episode, ProviderLinks
from app.scrapers.base import SearchResult as ScraperSearchResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_download(db_session, **kwargs) -> Download:
    defaults = dict(
        title="Test Film",
        source_url="https://1fichier.com/?abc",
        media_type="movie",
        destination="server",
        status="queued",
        progress_pct=0.0,
    )
    defaults.update(kwargs)
    d = Download(**defaults)
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


async def _seed_history(db_session, **kwargs) -> History:
    defaults = dict(
        title="Old Movie",
        source_url="https://1fichier.com/?xyz",
        media_type="movie",
        source="alldebrid",
    )
    defaults.update(kwargs)
    h = History(**defaults)
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)
    return h


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    async def test_returns_results(self, client) -> None:
        fake_result = ScraperSearchResult(
            title="Dune",
            url="https://wawacity.city/dune",
            source="wawacity",
            year=2021,
            quality="1080p",
        )

        with patch("app.api.v1.search.get_scraper") as mock_get:
            mock_scraper = MagicMock()
            mock_scraper.search = AsyncMock(return_value=[fake_result])
            mock_get.return_value = mock_scraper

            resp = await client.get("/api/v1/search?q=dune")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["results"][0]["title"] == "Dune"

    async def test_unknown_source_returns_400(self, client) -> None:
        resp = await client.get("/api/v1/search?q=dune&source=unknown")
        assert resp.status_code == 400

    async def test_empty_query_returns_422(self, client) -> None:
        resp = await client.get("/api/v1/search?q=")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------


class TestEpisodes:
    async def test_returns_episodes(self, client) -> None:
        fake_ep = Episode(
            title="Épisode 1",
            number=1,
            provider_links=[
                ProviderLinks(
                    provider="Rapidgator", urls=["https://dl-protect.link/ep1"]
                )
            ],
        )

        with patch("app.api.v1.episodes.get_scraper") as mock_get:
            mock_scraper = MagicMock()
            mock_scraper.get_episodes = AsyncMock(return_value=[fake_ep])
            mock_get.return_value = mock_scraper

            resp = await client.get(
                "/api/v1/episodes?url=https://wawacity.pizza?p=serie%26id=1"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["number"] == 1
        assert body[0]["title"] == "Épisode 1"
        assert body[0]["links"][0]["provider"] == "Rapidgator"
        assert body[0]["links"][0]["url"] == "https://dl-protect.link/ep1"

    async def test_unknown_source_returns_400(self, client) -> None:
        resp = await client.get(
            "/api/v1/episodes?url=https://example.com&source=unknown"
        )
        assert resp.status_code == 400

    async def test_not_implemented_returns_501(self, client) -> None:
        with patch("app.api.v1.episodes.get_scraper") as mock_get:
            mock_scraper = MagicMock()
            mock_scraper.get_episodes = AsyncMock(side_effect=NotImplementedError)
            mock_get.return_value = mock_scraper

            resp = await client.get(
                "/api/v1/episodes?url=https://www.wawacity.city/?p=serie&id=1&source=wawacity"
            )

        assert resp.status_code == 501

    async def test_missing_url_returns_422(self, client) -> None:
        resp = await client.get("/api/v1/episodes")
        assert resp.status_code == 422

    async def test_provider_filter_forwarded(self, client) -> None:
        with patch("app.api.v1.episodes.get_scraper") as mock_get:
            mock_scraper = MagicMock()
            mock_scraper.get_episodes = AsyncMock(return_value=[])
            mock_get.return_value = mock_scraper

            await client.get(
                "/api/v1/episodes?url=https://wawacity.pizza?p=serie%26id=1&providers=Rapidgator"
            )

        mock_scraper.get_episodes.assert_awaited_once_with(
            "https://wawacity.pizza?p=serie&id=1", ["Rapidgator"]
        )


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


class TestDownloads:
    async def test_create_download_returns_201(self, client) -> None:
        with patch("app.api.v1.downloads.download_queue") as mock_queue:
            mock_queue.enqueue = AsyncMock()
            resp = await client.post(
                "/api/v1/downloads",
                json={
                    "source_url": "https://1fichier.com/?abc",
                    "title": "My Film",
                    "media_type": "movie",
                },
            )

        assert resp.status_code == 201
        body = resp.json()
        assert "download_id" in body
        assert body["status"] == "queued"
        mock_queue.enqueue.assert_awaited_once()

    async def test_list_downloads_empty(self, client) -> None:
        resp = await client.get("/api/v1/downloads")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_downloads_includes_active(self, client, db_session) -> None:
        await _seed_download(db_session, status="downloading")
        resp = await client.get("/api/v1/downloads")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_download_returns_404_for_unknown(self, client) -> None:
        resp = await client.get("/api/v1/downloads/nonexistent")
        assert resp.status_code == 404

    async def test_get_download_returns_200(self, client, db_session) -> None:
        d = await _seed_download(db_session)
        resp = await client.get(f"/api/v1/downloads/{d.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == d.id

    async def test_delete_download_returns_204(self, client, db_session) -> None:
        d = await _seed_download(db_session)
        resp = await client.delete(f"/api/v1/downloads/{d.id}")
        assert resp.status_code == 204

    async def test_delete_download_returns_404_for_unknown(self, client) -> None:
        resp = await client.delete("/api/v1/downloads/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


class TestHistory:
    async def test_list_history_empty(self, client) -> None:
        resp = await client.get("/api/v1/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_history_returns_entries(self, client, db_session) -> None:
        await _seed_history(db_session, title="Inception")
        await _seed_history(db_session, title="Interstellar")
        resp = await client.get("/api/v1/history")
        assert resp.json()["total"] == 2

    async def test_list_history_search_filter(self, client, db_session) -> None:
        await _seed_history(db_session, title="Inception")
        await _seed_history(db_session, title="Interstellar")
        resp = await client.get("/api/v1/history?q=Inception")
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["title"] == "Inception"

    async def test_list_history_pagination(self, client, db_session) -> None:
        for i in range(5):
            await _seed_history(db_session, title=f"Film {i}")
        resp = await client.get("/api/v1/history?page=2&limit=2")
        body = resp.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["page"] == 2

    async def test_delete_history_returns_204(self, client, db_session) -> None:
        h = await _seed_history(db_session)
        resp = await client.delete(f"/api/v1/history/{h.id}")
        assert resp.status_code == 204

    async def test_delete_history_returns_404_for_unknown(self, client) -> None:
        resp = await client.delete("/api/v1/history/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class TestSettings:
    async def test_get_settings_empty(self, client) -> None:
        resp = await client.get("/api/v1/settings")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_put_settings_creates_entries(self, client) -> None:
        resp = await client.put(
            "/api/v1/settings",
            json={"settings": {"theme": "dark", "language": "fr"}},
        )
        assert resp.status_code == 200
        keys = {s["key"] for s in resp.json()}
        assert keys == {"theme", "language"}

    async def test_put_settings_updates_existing(self, client) -> None:
        await client.put("/api/v1/settings", json={"settings": {"theme": "dark"}})
        resp = await client.put(
            "/api/v1/settings", json={"settings": {"theme": "light"}}
        )
        assert resp.status_code == 200
        settings = {s["key"]: s["value"] for s in resp.json()}
        assert settings["theme"] == "light"

    async def test_get_settings_returns_persisted(self, client) -> None:
        await client.put("/api/v1/settings", json={"settings": {"foo": "bar"}})
        resp = await client.get("/api/v1/settings")
        settings = {s["key"]: s["value"] for s in resp.json()}
        assert settings["foo"] == "bar"

    async def test_put_settings_updates_runtime_settings(self, client) -> None:
        with patch("app.api.v1.settings.settings") as mock_settings:
            mock_settings.debrid_provider = "alldebrid"
            resp = await client.put(
                "/api/v1/settings",
                json={
                    "settings": {
                        "debrid_provider": "RealDebrid",
                        "max_concurrent_downloads": "3",
                    }
                },
            )

        assert resp.status_code == 200
        assert mock_settings.debrid_provider == "realdebrid"
        assert mock_settings.max_concurrent_downloads == 3


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestStatus:
    async def test_get_status_returns_200(self, client) -> None:
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=True)
        with patch("app.api.v1.status.get_debrid_client", return_value=mock_client):
            resp = await client.get("/api/v1/status")

        assert resp.status_code == 200
        body = resp.json()
        assert "queue_size" in body
        assert "active" in body
        assert "disk_free_gb" in body
        assert body["debrid_ok"] is True
        assert "debrid_provider" in body
        assert body["alldebrid_ok"] is True

    async def test_get_status_debrid_down(self, client) -> None:
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(return_value=False)
        with patch("app.api.v1.status.get_debrid_client", return_value=mock_client):
            resp = await client.get("/api/v1/status")

        assert resp.status_code == 200
        assert resp.json()["debrid_ok"] is False
        assert resp.json()["alldebrid_ok"] is False
