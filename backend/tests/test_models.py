from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.orm import Download, History, Setting


class TestDownloadModel:
    async def test_create_with_defaults(self, db_session):
        dl = Download(title="Inception", source_url="https://example.com", media_type="film")
        db_session.add(dl)
        await db_session.commit()
        await db_session.refresh(dl)

        assert dl.id is not None
        assert dl.status == "queued"
        assert dl.progress_pct == 0.0
        assert dl.destination == "server"
        assert dl.speed_mbps is None
        assert dl.filename is None
        assert dl.completed_at is None
        assert dl.error is None
        assert isinstance(dl.created_at, datetime)

    async def test_create_multiple(self, db_session):
        for i in range(3):
            db_session.add(
                Download(title=f"Film {i}", source_url="https://example.com", media_type="film")
            )
        await db_session.commit()

        result = await db_session.execute(select(Download))
        downloads = result.scalars().all()
        assert len(downloads) == 3

    async def test_update_status(self, db_session):
        dl = Download(title="Test", source_url="https://example.com", media_type="serie")
        db_session.add(dl)
        await db_session.commit()

        dl.status = "downloading"
        dl.progress_pct = 42.5
        dl.speed_mbps = 5.2
        await db_session.commit()
        await db_session.refresh(dl)

        assert dl.status == "downloading"
        assert dl.progress_pct == 42.5
        assert dl.speed_mbps == 5.2

    async def test_ids_are_unique(self, db_session):
        d1 = Download(title="A", source_url="https://a.com", media_type="film")
        d2 = Download(title="B", source_url="https://b.com", media_type="film")
        db_session.add_all([d1, d2])
        await db_session.commit()
        assert d1.id != d2.id


class TestHistoryModel:
    async def test_create(self, db_session):
        hist = History(
            title="The Matrix",
            source_url="https://example.com",
            media_type="film",
            source="wawacity",
        )
        db_session.add(hist)
        await db_session.commit()
        await db_session.refresh(hist)

        assert hist.id is not None
        assert hist.title == "The Matrix"
        assert hist.source == "wawacity"
        assert hist.filename is None
        assert isinstance(hist.downloaded_at, datetime)

    async def test_query_by_source(self, db_session):
        db_session.add(History(title="A", source_url="https://a.com", media_type="film", source="wawacity"))
        db_session.add(History(title="B", source_url="https://b.com", media_type="serie", source="darkiworld"))
        await db_session.commit()

        result = await db_session.execute(select(History).where(History.source == "wawacity"))
        items = result.scalars().all()
        assert len(items) == 1
        assert items[0].title == "A"


class TestSettingModel:
    async def test_create_and_read(self, db_session):
        db_session.add(Setting(key="download_path", value="/data/media"))
        await db_session.commit()

        result = await db_session.execute(select(Setting).where(Setting.key == "download_path"))
        setting = result.scalar_one()
        assert setting.value == "/data/media"

    async def test_update_value(self, db_session):
        db_session.add(Setting(key="max_concurrent", value="2"))
        await db_session.commit()

        result = await db_session.execute(select(Setting).where(Setting.key == "max_concurrent"))
        setting = result.scalar_one()
        setting.value = "4"
        await db_session.commit()
        await db_session.refresh(setting)
        assert setting.value == "4"
