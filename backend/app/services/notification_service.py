import asyncio
import logging
from datetime import UTC, datetime

import aiohttp
from sqlalchemy import select

from app.config import settings
from app.core.queue import download_queue
from app.database import AsyncSessionLocal
from app.models.orm import Notification
from app.models.schemas import DownloadCreate
from app.scrapers.base import get_scraper
from app.services.download_service import DownloadService

logger = logging.getLogger(__name__)

_PROVIDER_PRIORITY = ["turbobit", "rapidgator", "1fichier"]


def _pick_url(provider_links: list) -> str | None:
    for preferred in _PROVIDER_PRIORITY:
        for pl in provider_links:
            if preferred in pl.provider.lower():
                urls = pl.urls if hasattr(pl, "urls") else []
                if urls:
                    return urls[0]
    for pl in provider_links:
        urls = pl.urls if hasattr(pl, "urls") else []
        if urls:
            return urls[0]
    return None


class NotificationScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            interval_h = int(settings.notification_interval_hours)
            try:
                if settings.notification_enabled:
                    await self._check_all()
            except Exception:
                logger.exception("Notification check failed")
            await asyncio.sleep(interval_h * 3600)

    async def _check_all(self) -> None:
        async with AsyncSessionLocal() as session:
            rows = await session.execute(select(Notification))
            notifications = rows.scalars().all()

        for notif in notifications:
            try:
                await self._check_one(notif)
            except Exception:
                logger.exception(
                    "Failed to check notification %s (%s)", notif.id, notif.title
                )

    async def _check_one(self, notif: Notification) -> None:
        try:
            scraper = get_scraper(notif.source)
        except KeyError:
            logger.warning(
                "No scraper for source %r, skipping notification %s",
                notif.source,
                notif.id,
            )
            return

        episodes = await scraper.get_episodes(notif.url)
        if episodes is None:
            episodes = []

        now = datetime.now(UTC)
        new_count = len(episodes)

        if new_count <= notif.last_episode_count:
            async with AsyncSessionLocal() as session:
                row = await session.get(Notification, notif.id)
                if row:
                    row.last_checked_at = now
                    await session.commit()
            return

        # Première vérification (last_episode_count == 0) : initialisation seulement,
        # pas de téléchargement pour éviter d'enqueuer toute la série existante.
        is_first_check = notif.last_episode_count == 0
        # Trier par numéro d'épisode pour garantir un ordre stable (croissant)
        # indépendamment de l'ordre retourné par le scraper (HTML document order
        # ou ordre API). new_episodes = épisodes au-delà du dernier count connu.
        episodes_sorted = sorted(episodes, key=lambda ep: ep.number)
        new_episodes = episodes_sorted[notif.last_episode_count :]

        if is_first_check:
            logger.info(
                "Notification %s: initialisation à %d épisodes pour %s",
                notif.id,
                new_count,
                notif.title,
            )
        else:
            logger.info(
                "Notification %s: %d new episode(s) detected for %s",
                notif.id,
                len(new_episodes),
                notif.title,
            )

        if not is_first_check and notif.auto_download:
            await self._enqueue_new_episodes(notif, new_episodes)

        if not is_first_check and notif.discord_notify and settings.bot_notify_url:
            await self._notify_discord(notif, len(new_episodes), new_count)

        async with AsyncSessionLocal() as session:
            row = await session.get(Notification, notif.id)
            if row:
                row.last_episode_count = new_count
                row.last_checked_at = now
                await session.commit()

    async def _enqueue_new_episodes(
        self, notif: Notification, new_episodes: list
    ) -> None:
        async with AsyncSessionLocal() as session:
            service = DownloadService(session)
            for ep in new_episodes:
                url = _pick_url(ep.provider_links)
                if not url:
                    logger.warning(
                        "No downloadable URL for episode %s of %s",
                        ep.number,
                        notif.title,
                    )
                    continue
                alt_urls: list[str] = []
                for pl in ep.provider_links:
                    for u in pl.urls if hasattr(pl, "urls") else []:
                        if u != url:
                            alt_urls.append(u)
                data = DownloadCreate(
                    source_url=url,
                    title=f"{notif.title} — {ep.title}",
                    media_type="series",
                    destination="server",
                    alternative_urls=alt_urls,
                )
                download = await service.create(data)
                await download_queue.enqueue(download.id)
                logger.info(
                    "Enqueued episode %s of %s (download %s)",
                    ep.number,
                    notif.title,
                    download.id,
                )

    async def _notify_discord(
        self, notif: Notification, new_count: int, total: int
    ) -> None:
        from urllib.parse import quote

        app_url = ""
        if settings.app_public_url:
            app_url = (
                f"{settings.app_public_url.rstrip('/')}/search"
                f"?q={quote(notif.title)}&source={notif.source}&category=series"
            )

        payload = {
            "title": notif.title,
            "url": notif.url,
            "app_url": app_url,
            "new_count": new_count,
            "total": total,
            "poster_url": notif.poster_url,
        }
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession() as http:
                async with http.post(
                    settings.bot_notify_url, json=payload, timeout=timeout
                ) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            "Bot notify returned %d for %s",
                            resp.status,
                            notif.title,
                        )
        except Exception:
            logger.exception("Failed to send Discord notification for %s", notif.title)


notification_scheduler = NotificationScheduler()
