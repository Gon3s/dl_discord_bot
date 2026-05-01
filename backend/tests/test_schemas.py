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

    def test_valid_client_destination(self):
        data = DownloadCreate(
            source_url="https://example.com",
            title="Test",
            media_type="serie",
            destination="client",
        )
        assert data.destination == "client"

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
