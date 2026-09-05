import asyncio
import json
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
from app.core.exceptions import DebridAPIError, DownloadError, DownloadNotFoundError
from app.models.orm import Download, History
from app.models.schemas import DownloadCreate, WsProgressEvent
from app.scrapers.base import BaseScraper, get_scraper
from app.services.debrid import DebridClient, get_debrid_client

_SCRAPER_DOMAINS: dict[str, str] = {
    "wawacity": "wawacity",
}

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024  # 64 KB
_DB_UPDATE_INTERVAL = 2.0  # seconds between DB writes during streaming
_WS_EMIT_INTERVAL = 0.5  # seconds between WebSocket events during streaming
# No total timeout (large files), but abort if no data for 60s (stalled connection)
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=60)
_MAGNET_READY_STATUSES = {"ready", "downloaded", "completed", "complete"}
_MAGNET_ERROR_STATUSES = {"error", "dead", "failed", "magnet_error", "virus"}


async def _emit(download_id: str, event: dict) -> None:
    """Emit to the per-download channel and to the global queue channel."""
    await events.emit(download_id, event)
    await events.emit(events.QUEUE_CHANNEL, event)


class DownloadService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._debrid: DebridClient = get_debrid_client()

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
            alternative_urls=(
                json.dumps(data.alternative_urls) if data.alternative_urls else None
            ),
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
            select(Download)
            .where(
                Download.status.in_(
                    [
                        "queued",
                        "scraping",
                        "resolving",
                        "debriding",
                        "downloading",
                        "error",
                        "completed",
                        "cancelled",
                        "ready_for_client",
                    ]
                )
            )
            .order_by(Download.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    async def delete(self, download_id: str) -> bool:
        download = await self.get(download_id)
        if download is None:
            return False
        await self._session.delete(download)
        await self._session.commit()
        return True

    async def cancel(self, download_id: str) -> Download | None:
        """Persist cancellation after the queue has stopped the running job."""
        download = await self.get(download_id)
        if download is None:
            return None
        await self._set_status(
            download,
            "cancelled",
            speed_mbps=None,
            completed_at=datetime.now(UTC),
        )
        await _emit(
            download_id,
            WsProgressEvent(
                download_id=download_id,
                status="cancelled",
                progress_pct=download.progress_pct,
                filename=download.filename,
            ).model_dump(),
        )
        return download

    async def retry(self, download_id: str) -> Download | None:
        """Reset a failed download and re-enqueue it."""
        download = await self.get(download_id)
        if download is None or download.status != "error":
            return None
        download.status = "queued"
        download.error = None
        download.progress_pct = 0.0
        download.speed_mbps = None
        download.completed_at = None
        await self._session.commit()
        await self._session.refresh(download)
        return download

    # ------------------------------------------------------------------
    # Download execution
    # ------------------------------------------------------------------

    def _scraper_for_url(self, url: str) -> BaseScraper | None:
        """Return a source scraper, or None for a direct provider link."""
        netloc = urlparse(url).netloc
        for keyword, source_name in _SCRAPER_DOMAINS.items():
            if keyword in netloc:
                return get_scraper(source_name)
        return None

    async def run(self, download_id: str) -> None:
        """Scrape provider links, debrid, then download. Called by the queue worker."""
        download = await self.get(download_id)
        if download is None:
            raise DownloadNotFoundError(download_id)

        try:
            scraper = self._scraper_for_url(download.source_url)

            if scraper is not None:
                # Step 1 — scrape provider links from the source page
                await self._set_status(download, "scraping")
                await _emit(
                    download_id,
                    WsProgressEvent(
                        download_id=download_id, status="scraping", progress_pct=0.0
                    ).model_dump(),
                )

                provider_links = await scraper.get_provider_links(
                    download.source_url, []
                )

                if not provider_links:
                    raise DownloadError("No provider links found on the page")

                # Preferred providers are tried first, followed by the rest.
                _PREFERRED = ["Turbobit", "Rapidgator", "1fichier"]
                preferred = [
                    (pl.provider, url)
                    for name in _PREFERRED
                    for pl in provider_links
                    if pl.provider == name
                    for url in pl.urls
                ]
                others = [
                    (pl.provider, url)
                    for pl in provider_links
                    if pl.provider not in _PREFERRED
                    for url in pl.urls
                ]
                candidates = preferred + others

                if not candidates:
                    raise DownloadError("No usable provider link found on the page")
            else:
                # source_url is already a direct provider/dl-protect link
                scraper = None
                provider = (
                    "magnet" if download.source_url.startswith("magnet:") else "direct"
                )
                alt_urls = (
                    json.loads(download.alternative_urls)
                    if download.alternative_urls
                    else []
                )
                candidates = [(provider, download.source_url)] + [
                    ("direct", u) for u in alt_urls
                ]
                logger.info(
                    "Download %s — direct provider URL: %s (%d alternatives)",
                    download_id,
                    download.source_url,
                    len(alt_urls),
                )

            # Steps 2+3 — resolve dl-protect → debrid, with fallback on other providers
            await self._set_status(download, "resolving")
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id, status="resolving", progress_pct=0.0
                ).model_dump(),
            )

            debrid_data = None
            last_error: Exception = DownloadError("All provider links failed")
            for provider_name, dl_protect_url in candidates:
                try:
                    logger.info(
                        "Download %s — trying provider: %s url: %s",
                        download_id,
                        provider_name,
                        dl_protect_url,
                    )

                    await self._set_status(download, "debriding")
                    await _emit(
                        download_id,
                        WsProgressEvent(
                            download_id=download_id,
                            status="debriding",
                            progress_pct=0.0,
                        ).model_dump(),
                    )
                    is_magnet = provider_name == "magnet" or dl_protect_url.startswith(
                        "magnet:"
                    )
                    if is_magnet:
                        debrid_data = await self._debrid_magnet(dl_protect_url)
                    else:
                        provider_url: str | None = None
                        if hasattr(self._debrid, "redirect_link"):
                            try:
                                provider_url = await self._debrid.redirect_link(
                                    dl_protect_url
                                )
                                logger.info(
                                    "Download %s — resolved via API: %s",
                                    download_id,
                                    provider_url,
                                )
                            except Exception as exc:
                                logger.info(
                                    "Download %s — API redirect failed (%s),"
                                    " falling back to Selenium",
                                    download_id,
                                    exc,
                                )
                        if provider_url is None:
                            link_scraper = scraper or get_scraper("wawacity")
                            provider_url = await link_scraper.resolve_link(
                                dl_protect_url
                            )
                            logger.info(
                                "Download %s — resolved via Selenium: %s",
                                download_id,
                                provider_url,
                            )
                        debrid_data = await self._debrid.debrid_link(provider_url)
                    break
                except DebridAPIError as exc:
                    logger.warning(
                        "Download %s — %s rejected %s (%s): %s",
                        download_id,
                        self._debrid.display_name,
                        dl_protect_url,
                        provider_name,
                        exc,
                    )
                    last_error = exc

            if debrid_data is None:
                raise last_error

            direct_url: str | None = (
                debrid_data.get("link") or (debrid_data.get("links") or [None])[0]
            )
            if not direct_url:
                raise DownloadError(
                    f"{self._debrid.display_name} returned no direct URL"
                )

            filename: str | None = debrid_data.get("filename") or Path(direct_url).name

            # Step 4 — download or return direct URL to client
            if download.destination == "client":
                await self._set_status(
                    download,
                    "completed",
                    progress_pct=100.0,
                    filename=filename,
                    debrid_url=direct_url,
                    completed_at=datetime.now(UTC),
                )
                await self._write_history(download, filename)
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
            error_msg = str(exc) or type(exc).__name__
            await self._write_history(
                download, download.filename, status="error", error=error_msg
            )
            await self._set_status(download, "error", error=error_msg)
            await _emit(
                download_id,
                WsProgressEvent(
                    download_id=download_id,
                    status="error",
                    progress_pct=download.progress_pct,
                    error=error_msg,
                ).model_dump(),
            )
            logger.exception("Download %s failed", download_id)
            raise

    async def _debrid_magnet(self, magnet_url: str) -> dict:
        magnet_id = await self._debrid.upload_magnet(magnet_url)
        deadline = time.monotonic() + settings.magnet_poll_timeout_s

        while True:
            status_payload = await self._debrid.get_magnet_status(magnet_id)
            status = self._magnet_status(status_payload)
            if status in _MAGNET_READY_STATUSES:
                break
            if status in _MAGNET_ERROR_STATUSES:
                raise DownloadError(
                    f"{self._debrid.display_name} magnet failed with status: {status}"
                )
            if time.monotonic() >= deadline:
                raise DownloadError(f"{self._debrid.display_name} magnet timed out")
            await asyncio.sleep(settings.magnet_poll_interval_s)

        links = await self._debrid.get_magnet_files(magnet_id)
        if not links:
            raise DownloadError(f"{self._debrid.display_name} returned no magnet files")
        return {"link": links[0], "links": links}

    def _magnet_status(self, payload: dict) -> str:
        item = payload
        magnets = payload.get("magnets") or payload.get("magnet")
        if isinstance(magnets, list) and magnets:
            item = magnets[0]
        elif isinstance(magnets, dict):
            item = magnets
        return str(item.get("status", "")).lower()

    @staticmethod
    def _safe_component(name: str) -> str:
        """Sanitize a path component (filename or directory).

        Reduces to its basename and rejects path-traversal values. The
        filename comes from third-party debrid data, so it must never be
        trusted to build a path.
        """
        base = Path(name.strip()).name
        if not base or base in (".", "..") or "/" in base or "\\" in base:
            raise DownloadError(f"Unsafe filename rejected: {name!r}")
        return base

    @staticmethod
    def _jellyfin_episode_name(filename: str, show: str, season: int) -> str:
        """Rename a series file to the ``Show SxxEyy.ext`` form Jellyfin needs.

        Jellyfin only detects episodes whose filename contains ``SxxEyy``.
        French source names such as ``Show saison 1 ep1.avi`` are ignored,
        leaving the episode invisible in the library. When the episode number
        can be parsed, rebuild the name; otherwise keep the original filename.
        """
        # Already in SxxEyy form: leave it untouched so quality tags and the
        # original release name are preserved.
        if re.search(r"S\d{1,2}[. _-]*E\d{1,3}", filename, re.IGNORECASE):
            return filename
        # French source names ("... ep1", "... Episode 3") are invisible to
        # Jellyfin; rebuild them when an episode number can be parsed.
        em = re.search(
            r"(?:^|[. _-])(?:episode|ep)[. _]*(\d{1,3})",
            filename,
            re.IGNORECASE,
        )
        if not em:
            return filename
        episode = int(em.group(1))
        ext = Path(filename).suffix
        return f"{show} S{season:02d}E{episode:02d}{ext}"

    def _resolve_dest(self, media_type: str, filename: str) -> Path:
        """Return the full destination path based on media type and filename."""
        base = Path(settings.download_path)
        filename = self._safe_component(filename)
        if media_type == "films":
            dest = base / "Movies" / filename
        elif media_type in ("series", "mangas"):
            # Try to extract show title + season from filename.
            # Accept dot- or space-separated names, English or French:
            #   ShowTitle.S01E03.anything.ext  /  Show Title S01 anything.ext
            #   Show saison 1 ep1.ext          /  Show.Saison.1.Episode.3.ext
            m = re.match(
                r"^(.+?)[. _-]+(?:S(\d{1,2})|saison[. _]*(\d{1,2}))",
                filename,
                re.IGNORECASE,
            )
            if m:
                show = self._safe_component(m.group(1).replace(".", " ").strip())
                num = int(m.group(2) or m.group(3))
                season = f"S{num:02d}"  # e.g. S01
                filename = self._jellyfin_episode_name(filename, show, num)
                dest = base / "Shows" / show / f"{show} - {season}" / filename
            else:
                dest = base / "Shows" / filename
        else:
            dest = base / filename

        # Defense in depth: ensure the resolved path stays under download_path.
        resolved = dest.resolve()
        if not resolved.is_relative_to(base.resolve()):
            raise DownloadError(f"Destination escapes download path: {filename!r}")
        return dest

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

        async with aiohttp.ClientSession(timeout=_HTTP_TIMEOUT) as http:
            async with http.get(url) as response:
                if response.status != 200:
                    raise DownloadError(f"HTTP {response.status} when fetching {url}")

                total = int(response.headers.get("Content-Length", 0))
                f = await loop.run_in_executor(None, open, str(dest), "wb")
                cancelled = False
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
                except asyncio.CancelledError:
                    cancelled = True
                    raise
                finally:
                    await loop.run_in_executor(None, f.close)
                    if cancelled:
                        await asyncio.to_thread(dest.unlink, missing_ok=True)

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

    async def _write_history(
        self,
        download: Download,
        filename: str | None,
        status: str = "completed",
        error: str | None = None,
    ) -> None:
        history = History(
            title=download.title,
            source_url=download.source_url,
            filename=filename,
            media_type=download.media_type,
            source=self._debrid.name,
            destination=download.destination,
            status=status,
            error=error,
        )
        self._session.add(history)
        await self._session.commit()

    async def _set_status(self, download: Download, status: str, **kwargs) -> None:
        download.status = status
        for key, value in kwargs.items():
            setattr(download, key, value)
        await self._session.commit()
