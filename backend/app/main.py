import csv
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from app.api.v1.router import router as api_v1_router
from app.api.v1.settings import RUNTIME_SETTINGS, _runtime_value
from app.api.ws import router as ws_router
from app.config import settings as app_settings
from app.core.queue import download_queue
from app.database import AsyncSessionLocal, Base, engine
from app.models.orm import Download, History, Setting
from app.services.download_service import DownloadService
from app.services.notification_service import notification_scheduler

logger = logging.getLogger(__name__)


async def _run_download(download_id: str) -> None:
    async with AsyncSessionLocal() as session:
        service = DownloadService(session)
        await service.run(download_id)


async def _migrate_csv_if_needed() -> None:
    """Importe history.csv dans la table history si elle est vide."""
    csv_path = Path(__file__).resolve().parents[3] / "history.csv"
    if not csv_path.exists():
        return

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(History))
        if count and count > 0:
            return

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return

        now = datetime.now(UTC)
        entries = [
            History(
                id=str(uuid.uuid4()),
                title=row["title"].strip(),
                source_url=row["url"].strip(),
                filename=row["title"].strip(),
                media_type="unknown",
                source="wawacity",
                downloaded_at=now,
            )
            for row in rows
            if row.get("title", "").strip() and row.get("url", "").strip()
        ]

        session.add_all(entries)
        await session.commit()


async def _seed_settings() -> None:
    """Populate settings table from .env values for keys not yet in DB."""
    defaults = {
        "download_path": app_settings.download_path,
        "max_concurrent_downloads": str(app_settings.max_concurrent_downloads),
        "wawacity_url": app_settings.wawacity_url,
        "debrid_provider": app_settings.debrid_provider,
        "alldebrid_api_key": app_settings.alldebrid_api_key,
        "realdebrid_api_token": app_settings.realdebrid_api_token,
        "bot_notify_url": app_settings.bot_notify_url,
        "app_public_url": app_settings.app_public_url,
        "notification_enabled": str(app_settings.notification_enabled),
        "notification_interval_hours": str(app_settings.notification_interval_hours),
    }
    async with AsyncSessionLocal() as session:
        for key, value in defaults.items():
            existing = await session.get(Setting, key)
            if existing is None:
                session.add(Setting(key=key, value=value))
        await session.commit()


async def _load_runtime_settings() -> None:
    """Apply persisted runtime settings after seeding defaults from .env."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting).where(Setting.key.in_(RUNTIME_SETTINGS))
        )
        for setting in result.scalars().all():
            if hasattr(app_settings, setting.key):
                setattr(
                    app_settings,
                    setting.key,
                    _runtime_value(setting.key, setting.value),
                )


async def _resume_pending_downloads() -> None:
    """Reload pending downloads from database and enqueue them."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Download.id).where(Download.status == "queued")
        )
        pending_ids = result.scalars().all()
        for download_id in pending_ids:
            await download_queue.enqueue(download_id)
            logger.info("Resumed pending download: %s", download_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_csv_if_needed()
    await _seed_settings()
    await _load_runtime_settings()
    download_queue.set_handler(_run_download)
    download_queue.start()
    await _resume_pending_downloads()
    notification_scheduler.start()
    yield
    await notification_scheduler.stop()
    await download_queue.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="dl_discord_bot API",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router)
    app.include_router(ws_router)

    _mount_frontend(app)

    return app


def _mount_frontend(app: FastAPI) -> None:
    """Monte le build Angular en fichiers statiques si disponible.

    Doit être appelé en dernier dans create_app() pour que les routes API
    soient prioritaires sur le catch-all SPA.
    """
    frontend_dist = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "dist"
        / "frontend"
        / "browser"
    ).resolve()

    if not frontend_dist.exists():
        return

    index_html = frontend_dist / "index.html"

    # Catch-all SPA : sert les fichiers statiques Angular si présents,
    # sinon index.html pour que le router Angular gère la route.
    # Les routes /api/ et /ws/ ne sont pas interceptées (404 natif FastAPI).
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith(("api/", "ws/")):
            raise HTTPException(status_code=404)
        candidate = frontend_dist / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_html)


app = create_app()
