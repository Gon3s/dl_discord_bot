import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import events
from app.core.exceptions import DownloadError, DownloadNotFoundError
from app.models.orm import Download, History
from app.models.schemas import DownloadCreate, WsProgressEvent
from app.scrapers.base import BaseScraper, get_scraper
from app.services.alldebrid import AllDebridClient

_SCRAPER_DOMAINS: dict[str, str] = {
    "wawacity": "wawacity",
}

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024  # 64 KB
_DB_UPDATE_INTERVAL = 2.0  # seconds between DB writes during streaming
_WS_EMIT_INTERVAL = 0.5  # seconds between WebSocket events during streaming


async def _emit(download_id: str, event: dict) -> None:
    """Emit to the per-download channel and to the global queue channel."""
    await events.emit(download_id, event)
    await events.emit(events.QUEUE_CHANNEL, event)


class DownloadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._alldebrid = AllDebridClient()

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    async def create(self, data: DownloadCreate) -> Download:
        download = Download(
            title=data.title,
            source_url=str(data.source_url),
            media_type=data.media_type,
            destination=data.destination,
            status="queued",
        )
        self._session.add(download)
        await self._session.commit()
        await self._session.refresh(download)
        logger.info("Created download %s (%s)", download.id, download.title)
        return download

    async def get(self, download_id: str) -> Download | None:
        return await self._session.get(Download, download_id)

    async def list_active(self) -> list[Download]:
        result = await self._session.execute(
            select(Download).where(
                Download.status.in_(["queued", "scraping", "resolving", "debriding", "downloading", "error", "completed", "ready_for_client"])
            ).order_by(Download.created_at.desc()).limit(50)
        )
        return list(result.scalars().all())

    async def delete(self, download_id: str) -> bool:
        download = await self.get(download_id)
        if download is None:
            return False
        await self._session.delete(download)
        await self._session.commit()
        return True

    # ------------------------------------------------------------------
    # Download execution
    # ------------------------------------------------------------------

    def _scraper_for_url(self, url: str) -> BaseScraper:
        netloc = urlparse(url).netloc
        for keyword, source_name in _SCRAPER_DOMAINS.items():
            if keyword in netloc:
                return get_scraper(source_name)
        raise DownloadError(f"No scraper available for host: {netloc}")

    async def run(self, download_id: str) -> None:
        """Scrape provider links, debrid, then download. Called by the queue worker."""
        download = await self.get(download_id)
        if download is None:
            raise DownloadNotFoundError(download_id)

        try:
            # Step 1 — scrape provider links from the source page
            await self._set_status(download, "scraping")
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id, status="scraping", progress_pct=0.0
                ).model_dump(),
            )

            scraper = self._scraper_for_url(download.source_url)
            provider_links = await scraper.get_provider_links(download.source_url, [])

            if not provider_links:
                raise DownloadError("No provider links found on the page")

            _PREFERRED_PROVIDERS = ["Turbobit", "Rapidgator", "1fichier"]
            chosen = next(
                (pl for name in _PREFERRED_PROVIDERS for pl in provider_links if pl.provider == name and pl.urls),
                next((pl for pl in provider_links if pl.urls), None),
            )
            if chosen is None:
                raise DownloadError("No usable provider link found on the page")

            dl_protect_url = chosen.urls[0]
            logger.info(
                "Download %s — provider: %s dl-protect: %s",
                download_id,
                chosen.provider,
                dl_protect_url,
            )

            # Step 2 — resolve dl-protect intermediary to real provider URL
            await self._set_status(download, "resolving")
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id, status="resolving", progress_pct=0.0
                ).model_dump(),
            )
            provider_url = await scraper.resolve_link(dl_protect_url)
            logger.info("Download %s — resolved: %s", download_id, provider_url)

            # Step 3 — debrid the provider link
            await self._set_status(download, "debriding")
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id, status="debriding", progress_pct=0.0
                ).model_dump(),
            )

            debrid_data = await self._alldebrid.debrid_link(provider_url)
            direct_url: str | None = debrid_data.get("link") or (
                debrid_data.get("links") or [None]
            )[0]
            if not direct_url:
                raise DownloadError("AllDebrid returned no direct URL")

            filename: str | None = debrid_data.get("filename") or Path(direct_url).name

            # Step 4 — download or return direct URL to client
            if download.destination == "client":
                await self._set_status(
                    download,
                    "completed",
                    progress_pct=100.0,
                    filename=filename,
                    completed_at=datetime.now(UTC),
                )
                await _emit(
                    download_id,
                    WsProgressEvent(
                        download_id=download_id,
                        status="completed",
                        progress_pct=100.0,
                        filename=filename,
                        debrid_url=direct_url,
                    ).model_dump(),
                )
                return

            await self._set_status(download, "downloading")
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id, status="downloading", progress_pct=0.0
                ).model_dump(),
            )
            await self._stream_to_disk(download, direct_url, filename)
            await self._write_history(download, filename)

        except Exception as exc:
            await self._set_status(download, "error", error=str(exc))
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id,
                    status="error",
                    progress_pct=download.progress_pct,
                ).model_dump(),
            )
            logger.exception("Download %s failed", download_id)
            raise

    def _resolve_dest(self, media_type: str, filename: str) -> Path:
        """Return the full destination path based on media type and filename."""
        base = Path(settings.download_path)
        if media_type == "films":
            return base / "Movies" / filename
        if media_type in ("series", "mangas"):
            # Try to extract show title + season from filename
            # Pattern: ShowTitle.S01E03.anything.ext  or  ShowTitle.S01.anything.ext
            m = re.match(
                r"^(.+?)\.(S\d{1,2})(?:E\d+)?(?:\.|$)",
                filename,
                re.IGNORECASE,
            )
            if m:
                show = m.group(1).replace(".", " ")
                season = m.group(2).upper()  # e.g. S01
                return base / "Shows" / show / f"{show} - {season}" / filename
            return base / "Shows" / filename
        return base / filename

    async def _stream_to_disk(
        self, download: Download, url: str, filename: str
    ) -> None:
        dest = self._resolve_dest(download.media_type, filename)
        dest.parent.mkdir(parents=True, exist_ok=True)

        download_id = download.id
        loop = asyncio.get_event_loop()
        start = time.monotonic()
        downloaded = 0
        last_db_update = start
        last_ws_emit = start

        async with aiohttp.ClientSession() as http:
            async with http.get(url) as response:
                if response.status != 200:
                    raise DownloadError(f"HTTP {response.status} when fetching {url}")

                total = int(response.headers.get("Content-Length", 0))
                f = await loop.run_in_executor(None, open, str(dest), "wb")
                try:
                    async for chunk in response.content.iter_chunked(_CHUNK_SIZE):
                        await loop.run_in_executor(None, f.write, chunk)
                        downloaded += len(chunk)

                        now = time.monotonic()
                        elapsed = now - start
                        speed_bps = downloaded / elapsed if elapsed > 0 else 0.0
                        progress = (downloaded / total * 100.0) if total else 0.0
                        speed_mbps = speed_bps / 1_000_000
                        eta_s = (
                            int((total - downloaded) / speed_bps)
                            if speed_bps and total
                            else None
                        )

                        if now - last_ws_emit >= _WS_EMIT_INTERVAL:
                            await _emit(
                                download_id,
                                WsProgressEvent(
                                    download_id=download_id,
                                    status="downloading",
                                    progress_pct=progress,
                                    speed_mbps=speed_mbps,
                                    eta_s=eta_s,
                                    filename=filename,
                                ).model_dump(),
                            )
                            last_ws_emit = now

                        if now - last_db_update >= _DB_UPDATE_INTERVAL:
                            await self._set_status(
                                download,
                                "downloading",
                                progress_pct=progress,
                                speed_mbps=speed_mbps,
                                filename=filename,
                            )
                            last_db_update = now
                finally:
                    await loop.run_in_executor(None, f.close)

        await self._set_status(
            download,
            "completed",
            progress_pct=100.0,
            filename=filename,
            completed_at=datetime.now(UTC),
        )
        await _emit(
            download_id,
            WsProgressEvent(
                download_id=download_id,
                status="completed",
                progress_pct=100.0,
                filename=filename,
            ).model_dump(),
        )
        logger.info("Download %s completed → %s", download_id, dest)

    async def _write_history(self, download: Download, filename: str | None) -> None:
        history = History(
            title=download.title,
            source_url=download.source_url,
            filename=filename,
            media_type=download.media_type,
            source="alldebrid",
        )
        self._session.add(history)
        await self._session.commit()

    async def _set_status(self, download: Download, status: str, **kwargs) -> None:
        download.status = status
        for key, value in kwargs.items():
            setattr(download, key, value)
        await self._session.commit()
