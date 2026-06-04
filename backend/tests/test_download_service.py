from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DownloadError, DownloadNotFoundError
from app.models.schemas import DownloadCreate
from app.scrapers.wawacity import WawacityScraper
from app.services.download_service import DownloadService


@pytest.fixture
def service(db_session):
    return DownloadService(db_session)


@pytest.fixture
def download_create() -> DownloadCreate:
    return DownloadCreate(
        source_url="https://1fichier.com/?abc123",
        title="Test Movie",
        media_type="movie",
        destination="server",
    )


class TestCreate:
    async def test_creates_record_with_queued_status(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        download = await service.create(download_create)

        assert download.id is not None
        assert download.title == "Test Movie"
        assert download.status == "queued"
        assert download.progress_pct == 0.0
        assert download.destination == "server"

    async def test_persists_to_db(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        download = await service.create(download_create)
        fetched = await service.get(download.id)

        assert fetched is not None
        assert fetched.id == download.id


class TestGet:
    async def test_returns_none_for_unknown_id(self, service: DownloadService) -> None:
        result = await service.get("nonexistent-id")
        assert result is None

    async def test_returns_download_by_id(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        created = await service.create(download_create)
        result = await service.get(created.id)

        assert result is not None
        assert result.id == created.id


class TestDelete:
    async def test_returns_false_for_unknown_id(self, service: DownloadService) -> None:
        result = await service.delete("nonexistent-id")
        assert result is False

    async def test_deletes_existing_download(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        download = await service.create(download_create)
        result = await service.delete(download.id)

        assert result is True
        assert await service.get(download.id) is None


class TestListActive:
    async def test_returns_queued_and_downloading(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        d1 = await service.create(download_create)
        d2 = await service.create(download_create)
        await service._set_status(d2, "downloading")

        active = await service.list_active()
        ids = {d.id for d in active}

        assert d1.id in ids
        assert d2.id in ids

    async def test_includes_completed_and_error(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        d = await service.create(download_create)
        await service._set_status(d, "completed")

        active = await service.list_active()
        assert any(x.id == d.id for x in active)


class TestScraperForUrl:
    def test_returns_wawacity_scraper_for_wawacity_url(
        self, service: DownloadService
    ) -> None:
        scraper = service._scraper_for_url("https://www.wawacity.pizza?p=film&id=1")
        assert isinstance(scraper, WawacityScraper)

    def test_returns_none_for_dl_protect_url(self, service: DownloadService) -> None:
        assert service._scraper_for_url("https://dl-protect.link/abc123") is None

    def test_returns_none_for_unknown_host(self, service: DownloadService) -> None:
        assert service._scraper_for_url("https://1fichier.com/?abc") is None


def _mock_scraper(provider_url: str = "https://turbobit.net/abc123"):
    """Return a mock scraper that yields one Turbobit provider link."""
    from app.scrapers.base import ProviderLinks

    scraper = MagicMock()
    scraper.get_provider_links = AsyncMock(
        return_value=[
            ProviderLinks(provider="Turbobit", urls=["https://dl-protect.link/abc"])
        ]
    )
    scraper.resolve_link = AsyncMock(return_value=provider_url)
    return scraper


def _mock_magnet_scraper():
    """Return a mock scraper that yields one magnet provider link."""
    from app.scrapers.base import ProviderLinks

    scraper = MagicMock()
    scraper.get_provider_links = AsyncMock(
        return_value=[
            ProviderLinks(provider="magnet", urls=["magnet:?xt=urn:btih:ABC123"])
        ]
    )
    scraper.resolve_link = AsyncMock()
    return scraper


class TestRunClientDestination:
    async def test_client_destination_emits_completed_without_downloading(
        self, service: DownloadService, db_session
    ) -> None:
        data = DownloadCreate(
            source_url="https://www.wawacity.pizza?p=film&id=12345-test",
            title="Film",
            media_type="films",
            destination="client",
        )
        download = await service.create(data)

        debrid_data = {
            "link": "https://cdn.example.com/film.mkv",
            "filename": "film.mkv",
        }
        emitted: list[dict] = []

        async def capture_emit(download_id: str, event: dict) -> None:
            emitted.append(event)

        with (
            patch.object(service, "_scraper_for_url", return_value=_mock_scraper()),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(return_value=debrid_data),
            ),
            patch(
                "app.services.download_service.events.emit", side_effect=capture_emit
            ),
        ):
            await service.run(download.id)

        refreshed = await service.get(download.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.progress_pct == 100.0
        assert refreshed.filename == "film.mkv"

        completed_event = next(e for e in emitted if e["status"] == "completed")
        assert completed_event["download_id"] == download.id

    async def test_client_destination_never_writes_to_disk(
        self, service: DownloadService
    ) -> None:
        data = DownloadCreate(
            source_url="https://www.wawacity.pizza?p=film&id=12345-test",
            title="Film",
            media_type="films",
            destination="client",
        )
        download = await service.create(data)

        debrid_data = {
            "link": "https://cdn.example.com/film.mkv",
            "filename": "film.mkv",
        }

        with (
            patch.object(service, "_scraper_for_url", return_value=_mock_scraper()),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(return_value=debrid_data),
            ),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
            patch("builtins.open") as mock_open,
        ):
            await service.run(download.id)
            mock_open.assert_not_called()

    async def test_client_destination_supports_magnet_provider(
        self, service: DownloadService
    ) -> None:
        data = DownloadCreate(
            source_url="https://www.wawacity.pizza?p=film&id=1-test",
            title="Film",
            media_type="films",
            destination="client",
        )
        download = await service.create(data)
        debrid_mock = AsyncMock()

        with (
            patch.object(
                service, "_scraper_for_url", return_value=_mock_magnet_scraper()
            ),
            patch.object(
                service._debrid,
                "upload_magnet",
                new=AsyncMock(return_value=123),
            ),
            patch.object(
                service._debrid,
                "get_magnet_status",
                new=AsyncMock(return_value={"magnets": [{"status": "Ready"}]}),
            ),
            patch.object(
                service._debrid,
                "get_magnet_files",
                new=AsyncMock(return_value=["https://cdn.example.com/movie.mkv"]),
            ),
            patch.object(service._debrid, "debrid_link", new=debrid_mock),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
        ):
            await service.run(download.id)

        refreshed = await service.get(download.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        assert refreshed.filename == "movie.mkv"
        debrid_mock.assert_not_awaited()


class TestRunDirectUrl:
    """When source_url is a direct dl-protect link (episode), scraping is skipped."""

    async def test_direct_url_skips_scraping_and_completes(
        self, service: DownloadService
    ) -> None:
        data = DownloadCreate(
            source_url="https://dl-protect.link/ep1abc",
            title="Breaking Bad S01E01",
            media_type="serie",
            destination="client",
        )
        download = await service.create(data)

        debrid_data = {"link": "https://cdn.example.com/bb.mkv", "filename": "bb.mkv"}
        mock_scraper = MagicMock()
        mock_scraper.resolve_link = AsyncMock(
            return_value="https://rapidgator.net/file/abc"
        )

        with (
            patch(
                "app.services.download_service.get_scraper", return_value=mock_scraper
            ),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(return_value=debrid_data),
            ),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
        ):
            await service.run(download.id)

        refreshed = await service.get(download.id)
        assert refreshed is not None
        assert refreshed.status == "completed"
        mock_scraper.resolve_link.assert_awaited_once_with(
            "https://dl-protect.link/ep1abc"
        )

    async def test_direct_url_never_calls_get_provider_links(
        self, service: DownloadService
    ) -> None:
        data = DownloadCreate(
            source_url="https://dl-protect.link/ep1abc",
            title="Episode Test",
            media_type="serie",
            destination="client",
        )
        download = await service.create(data)

        mock_scraper = MagicMock()
        mock_scraper.resolve_link = AsyncMock(
            return_value="https://rapidgator.net/file/abc"
        )

        with (
            patch(
                "app.services.download_service.get_scraper", return_value=mock_scraper
            ),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(
                    return_value={
                        "link": "https://cdn.example.com/ep.mkv",
                        "filename": "ep.mkv",
                    }
                ),
            ),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
        ):
            await service.run(download.id)

        mock_scraper.get_provider_links.assert_not_called()


class TestRunErrors:
    async def test_raises_download_not_found_for_unknown_id(
        self, service: DownloadService
    ) -> None:
        with pytest.raises(DownloadNotFoundError):
            await service.run("nonexistent-id")

    async def test_sets_error_status_on_alldebrid_failure(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        download = await service.create(download_create)

        with (
            patch.object(service, "_scraper_for_url", return_value=_mock_scraper()),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(side_effect=DownloadError("AllDebrid failed")),
            ),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
            pytest.raises(DownloadError),
        ):
            await service.run(download.id)

        refreshed = await service.get(download.id)
        assert refreshed is not None
        assert refreshed.status == "error"
        assert "AllDebrid failed" in (refreshed.error or "")

    async def test_sets_error_when_no_direct_url(
        self, service: DownloadService, download_create: DownloadCreate
    ) -> None:
        download = await service.create(download_create)

        with (
            patch.object(service, "_scraper_for_url", return_value=_mock_scraper()),
            patch.object(
                service._debrid,
                "debrid_link",
                new=AsyncMock(return_value={"link": None, "links": []}),
            ),
            patch("app.services.download_service.events.emit", new=AsyncMock()),
            pytest.raises(DownloadError),
        ):
            await service.run(download.id)

        refreshed = await service.get(download.id)
        assert refreshed is not None
        assert refreshed.status == "error"


class TestResolveDest:
    @pytest.fixture(autouse=True)
    def _base(self, tmp_path):
        from app.services import download_service as ds

        with patch.object(ds.settings, "download_path", str(tmp_path)):
            self.base = tmp_path
            yield

    def test_film_goes_under_movies(self, service: DownloadService) -> None:
        dest = service._resolve_dest("films", "Cool.Movie.2024.mkv")
        assert dest == self.base / "Movies" / "Cool.Movie.2024.mkv"

    def test_series_dot_separated(self, service: DownloadService) -> None:
        dest = service._resolve_dest("series", "Show.Name.S01E03.x264.mkv")
        assert dest == (
            self.base
            / "Shows"
            / "Show Name"
            / "Show Name - S01"
            / "Show.Name.S01E03.x264.mkv"
        )

    def test_series_space_separated(self, service: DownloadService) -> None:
        dest = service._resolve_dest("series", "Show Name S01E03 x264.mkv")
        assert dest == (
            self.base
            / "Shows"
            / "Show Name"
            / "Show Name - S01"
            / "Show Name S01E03 x264.mkv"
        )

    @pytest.mark.parametrize(
        ("evil", "expected_name"),
        [
            ("../../etc/cron.d/x", "x"),
            ("/etc/passwd", "passwd"),
            ("foo/../../bar", "bar"),
            ("sub/dir/file.mkv", "file.mkv"),
        ],
    )
    def test_neutralizes_path_traversal_to_basename(
        self, service: DownloadService, evil: str, expected_name: str
    ) -> None:
        dest = service._resolve_dest("films", evil)
        assert dest == self.base / "Movies" / expected_name
        assert dest.resolve().is_relative_to(self.base.resolve())

    @pytest.mark.parametrize("evil", ["..", ".", ""])
    def test_rejects_unsafe_filename(self, service: DownloadService, evil: str) -> None:
        with pytest.raises(DownloadError):
            service._resolve_dest("films", evil)
