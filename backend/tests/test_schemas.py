from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    DownloadCreate,
    DownloadRead,
    SearchResult,
    SettingsUpdate,
    WsProgressEvent,
)


class TestDownloadCreate:
    def test_valid_server_destination(self):
        data = DownloadCreate(
            source_url="https://example.com",
            title="Inception",
            media_type="film",
            destination="server",
        )
        assert data.destination == "server"
        assert data.media_type == "films"

    def test_valid_client_destination(self):
        data = DownloadCreate(
            source_url="https://example.com",
            title="Test",
            media_type="serie",
            destination="client",
        )
        assert data.destination == "client"
        assert data.media_type == "series"

    def test_default_destination_is_server(self):
        data = DownloadCreate(
            source_url="https://example.com", title="Test", media_type="film"
        )
        assert data.destination == "server"

    def test_invalid_destination_rejected(self):
        with pytest.raises(ValidationError):
            DownloadCreate(
                source_url="https://example.com",
                title="Test",
                media_type="film",
                destination="ftp",
            )

    @pytest.mark.parametrize(
        ("alias", "expected"),
        [
            ("film", "films"),
            ("movie", "films"),
            ("serie", "series"),
            ("manga", "mangas"),
        ],
    )
    def test_media_type_aliases_are_normalized(self, alias, expected):
        data = DownloadCreate(
            source_url="https://example.com/file", title="Test", media_type=alias
        )
        assert data.media_type == expected

    def test_invalid_media_type_rejected(self):
        with pytest.raises(ValidationError):
            DownloadCreate(
                source_url="https://example.com/file",
                title="Test",
                media_type="music",
            )

    @pytest.mark.parametrize(
        "source_url",
        [
            "ftp://example.com/file",
            "https:///missing-host",
            "http://localhost/file",
            "http://127.0.0.1/file",
            "https://user:password@example.com/file",
            "magnet:?dn=missing-info-hash",
        ],
    )
    def test_invalid_source_url_rejected(self, source_url):
        with pytest.raises(ValidationError):
            DownloadCreate(source_url=source_url, title="Test", media_type="films")

    def test_valid_magnet_url_accepted(self):
        data = DownloadCreate(
            source_url="magnet:?xt=urn:btih:abc123&dn=Test",
            title="Test",
            media_type="films",
        )
        assert data.source_url.startswith("magnet:")

    def test_alternative_urls_are_validated(self):
        with pytest.raises(ValidationError):
            DownloadCreate(
                source_url="https://example.com/file",
                title="Test",
                media_type="films",
                alternative_urls=["file:///etc/passwd"],
            )

    def test_alternative_urls_are_limited(self):
        with pytest.raises(ValidationError):
            DownloadCreate(
                source_url="https://example.com/file",
                title="Test",
                media_type="films",
                alternative_urls=[
                    f"https://example.com/file-{index}" for index in range(21)
                ],
            )

    def test_blank_title_rejected(self):
        with pytest.raises(ValidationError):
            DownloadCreate(
                source_url="https://example.com/file",
                title="   ",
                media_type="films",
            )


class TestDownloadRead:
    def test_from_orm_attributes(self):
        now = datetime.now(UTC)
        data = DownloadRead(
            id="abc-123",
            title="Film",
            source_url="https://example.com",
            media_type="film",
            destination="server",
            status="queued",
            progress_pct=0.0,
            speed_mbps=None,
            filename=None,
            created_at=now,
            completed_at=None,
            error=None,
        )
        assert data.id == "abc-123"
        assert data.status == "queued"


class TestSearchResult:
    def test_minimal(self):
        r = SearchResult(
            title="Inception", url="https://example.com", source="wawacity"
        )
        assert r.year is None
        assert r.poster_url is None

    def test_full(self):
        r = SearchResult(
            title="Inception",
            url="https://example.com",
            year=2010,
            category="films",
            quality="1080p",
            language="fr",
            source="wawacity",
            poster_url="https://example.com/poster.jpg",
        )
        assert r.year == 2010
        assert r.quality == "1080p"


class TestSettingsUpdate:
    def test_valid(self):
        s = SettingsUpdate(settings={"download_path": "/data", "max_concurrent": "4"})
        assert s.settings["download_path"] == "/data"

    def test_empty(self):
        s = SettingsUpdate(settings={})
        assert s.settings == {}


class TestWsProgressEvent:
    def test_minimal(self):
        e = WsProgressEvent(download_id="abc", status="downloading", progress_pct=50.0)
        assert e.speed_mbps is None
        assert e.eta_s is None
        assert e.filename is None

    def test_full(self):
        e = WsProgressEvent(
            download_id="abc",
            status="downloading",
            progress_pct=75.0,
            speed_mbps=12.5,
            eta_s=30,
            filename="inception.mkv",
        )
        assert e.speed_mbps == 12.5
        assert e.filename == "inception.mkv"
