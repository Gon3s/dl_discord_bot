import asyncio
import logging
import re
from urllib.parse import unquote

import aiohttp
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located, url_changes
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver

from app.config import settings
from app.scrapers.base import BaseScraper, Episode, ProviderLinks, SearchResult, register

logger = logging.getLogger(__name__)

_LOGIN_SEM = asyncio.Semaphore(1)

_CATEGORY_TO_TYPE: dict[str, str] = {
    "films": "movie",
    "series": "series",
    "mangas": "anime",
    "animes": "anime",
}


def _base_url() -> str:
    return settings.darkiworld_url.rstrip("/")


def _extract_id(url: str) -> str | None:
    """Extract numeric title ID from /titles/123 or /titles/123/slug."""
    m = re.search(r"/titles/(\d+)", url)
    return m.group(1) if m else None


@register
class DarkiworldScraper(BaseScraper):
    source_name = "darkiworld"

    # Class-level cookie cache — shared across instances.
    _cookies: dict[str, str] | None = None

    # ---------------------------------------------------------------------------
    # Session management
    # ---------------------------------------------------------------------------

    async def _get_cookies(self) -> dict[str, str]:
        if DarkiworldScraper._cookies is not None:
            return DarkiworldScraper._cookies
        async with _LOGIN_SEM:
            if DarkiworldScraper._cookies is None:
                loop = asyncio.get_running_loop()
                DarkiworldScraper._cookies = await loop.run_in_executor(
                    None, self._login_sync
                )
        return DarkiworldScraper._cookies

    def _login_sync(self) -> dict[str, str]:
        base = _base_url()
        driver = Driver(uc=True, headless=True)
        try:
            driver.get(f"{base}/login")
            wait = WebDriverWait(driver, 20)

            # React renders asynchronously — wait for the email input.
            email_input = wait.until(
                presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.send_keys(settings.darkiworld_email)
            driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(
                settings.darkiworld_password
            )
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

            # Wait until the browser leaves the /login page.
            wait.until(url_changes(f"{base}/login"))

            return {c["name"]: c["value"] for c in driver.get_cookies()}
        finally:
            driver.quit()

    def _build_headers(self, cookies: dict[str, str]) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        # Laravel Sanctum: pass the XSRF token as a header too.
        if "XSRF-TOKEN" in cookies:
            headers["X-XSRF-TOKEN"] = unquote(cookies["XSRF-TOKEN"])
        return headers

    def _invalidate_session(self) -> None:
        DarkiworldScraper._cookies = None

    # ---------------------------------------------------------------------------
    # search()
    # ---------------------------------------------------------------------------

    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
        sort: str | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        cookies = await self._get_cookies()
        dw_type = _CATEGORY_TO_TYPE.get(category, "movie")
        params: dict[str, str | int] = {
            "query": query,
            "type": dw_type,
            "perPage": limit,
        }
        if year is not None:
            params["year"] = year
        if page > 1:
            params["page"] = page

        try:
            async with aiohttp.ClientSession(
                cookies=cookies, headers=self._build_headers(cookies)
            ) as session:
                async with session.get(
                    f"{_base_url()}/api/titles", params=params
                ) as resp:
                    if "application/json" not in resp.content_type:
                        logger.warning(
                            "DarkiWorld search: non-JSON response (session expired?)"
                        )
                        self._invalidate_session()
                        return []
                    if resp.status != 200:
                        logger.error("DarkiWorld search returned HTTP %d", resp.status)
                        return []
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            logger.error("DarkiWorld search request failed: %s", exc)
            return []

        return self._parse_search_response(data, limit)

    def _parse_search_response(self, data: dict, limit: int) -> list[SearchResult]:
        items = (
            data.get("pagination", {}).get("data")
            or data.get("data")
            or []
        )
        base = _base_url()
        results: list[SearchResult] = []
        for item in items[:limit]:
            title_id = item.get("id")
            slug = item.get("slug", "")
            url = (
                f"{base}/titles/{title_id}/{slug}"
                if slug
                else f"{base}/titles/{title_id}"
            )

            poster = item.get("poster")
            poster_url: str | None = None
            if poster:
                poster_url = (
                    poster if poster.startswith("http") else f"{base}/storage/{poster}"
                )

            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=url,
                    source=self.source_name,
                    year=item.get("year"),
                    quality=None,
                    language=item.get("language"),
                    poster_url=poster_url,
                )
            )
        return results

    # ---------------------------------------------------------------------------
    # get_provider_links()
    # ---------------------------------------------------------------------------

    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]:
        title_id = _extract_id(url)
        if not title_id:
            logger.error("DarkiWorld: cannot extract title ID from URL %r", url)
            return []

        cookies = await self._get_cookies()
        try:
            async with aiohttp.ClientSession(
                cookies=cookies, headers=self._build_headers(cookies)
            ) as session:
                async with session.get(
                    f"{_base_url()}/api/titles/{title_id}/videos"
                ) as resp:
                    if "application/json" not in resp.content_type:
                        logger.warning(
                            "DarkiWorld get_provider_links: non-JSON (session expired?)"
                        )
                        self._invalidate_session()
                        return []
                    if resp.status != 200:
                        logger.error("DarkiWorld /videos returned HTTP %d", resp.status)
                        return []
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            logger.error("DarkiWorld get_provider_links request failed: %s", exc)
            return []

        return self._parse_provider_links(data, providers)

    def _parse_provider_links(
        self, data: dict | list, providers: list[str]
    ) -> list[ProviderLinks]:
        videos = (
            data
            if isinstance(data, list)
            else data.get("videos") or data.get("data") or []
        )
        grouped: dict[str, list[str]] = {}
        for video in videos:
            for link in video.get("links", []):
                host = link.get("host", {})
                provider = (
                    host.get("name") if isinstance(host, dict) else str(host)
                )
                link_url = link.get("url", "")
                if not provider or not link_url:
                    continue
                if providers and provider not in providers:
                    continue
                grouped.setdefault(provider, []).append(link_url)
        return [ProviderLinks(provider=p, urls=urls) for p, urls in grouped.items()]

    # ---------------------------------------------------------------------------
    # get_episodes()
    # ---------------------------------------------------------------------------

    async def get_episodes(
        self,
        url: str,
        providers: list[str] | None = None,
    ) -> list[Episode]:
        title_id = _extract_id(url)
        if not title_id:
            logger.error("DarkiWorld: cannot extract title ID from URL %r", url)
            return []

        cookies = await self._get_cookies()
        try:
            async with aiohttp.ClientSession(
                cookies=cookies, headers=self._build_headers(cookies)
            ) as session:
                async with session.get(
                    f"{_base_url()}/api/titles/{title_id}/seasons"
                ) as resp:
                    if "application/json" not in resp.content_type:
                        logger.warning(
                            "DarkiWorld get_episodes: non-JSON (session expired?)"
                        )
                        self._invalidate_session()
                        return []
                    if resp.status != 200:
                        logger.error("DarkiWorld /seasons returned HTTP %d", resp.status)
                        return []
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            logger.error("DarkiWorld get_episodes request failed: %s", exc)
            return []

        return self._parse_seasons(data, providers or [])

    def _parse_seasons(
        self, data: dict | list, providers: list[str]
    ) -> list[Episode]:
        seasons = (
            data
            if isinstance(data, list)
            else data.get("seasons") or data.get("data") or []
        )
        episodes: list[Episode] = []
        for season in seasons:
            season_num = season.get("number", 1)
            for ep in season.get("episodes", []):
                ep_num = ep.get("episode_number") or ep.get("number") or (
                    len(episodes) + 1
                )
                ep_name = ep.get("name", f"S{season_num:02d}E{ep_num:02d}")
                provider_links = self._parse_provider_links(
                    {"videos": ep.get("videos", [])}, providers
                )
                episodes.append(
                    Episode(
                        title=f"S{season_num:02d}E{ep_num:02d} — {ep_name}",
                        number=ep_num,
                        provider_links=provider_links,
                    )
                )
        return episodes
