import asyncio
import json
import logging
import re
import time
from urllib.parse import unquote

import aiohttp
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import SB

from app.config import settings
from app.scrapers.base import (
    BaseScraper,
    Episode,
    ProviderLinks,
    SearchResult,
    register,
)

logger = logging.getLogger(__name__)

_LOGIN_SEM = asyncio.Semaphore(1)
_SELENIUM_SEM = asyncio.Semaphore(1)

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

        with SB(uc=True, test=False, headless=True) as sb:
            sb.driver.uc_open_with_reconnect(f"{base}/login", reconnect_time=4)
            sb.wait_for_element("input[type='email']", timeout=15)
            sb.type("input[type='email']", settings.darkiworld_email)
            sb.type("input[type='password']", settings.darkiworld_password)

            # Cloudflare Turnstile s'auto-vérifie — attendre le champ caché.
            WebDriverWait(sb.driver, 30).until(
                lambda d: (
                    d.find_element(By.NAME, "cf-turnstile-response").get_attribute(
                        "value"
                    )
                    != ""
                )
            )
            logger.debug("DarkiWorld login: Turnstile vérifié")

            sb.click("button[type='submit']")

            WebDriverWait(sb.driver, 20).until(lambda d: "/login" not in d.current_url)

            return {c["name"]: c["value"] for c in sb.driver.get_cookies()}

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
        if "XSRF-TOKEN" in cookies:
            headers["X-XSRF-TOKEN"] = unquote(cookies["XSRF-TOKEN"])
        return headers

    def _invalidate_session(self) -> None:
        DarkiworldScraper._cookies = None

    def _inject_into_browser(self, sb: SB, cookies: dict[str, str]) -> None:
        """Inject session cookies into a Selenium browser instance."""
        base = _base_url()
        domain = re.sub(r"https?://", "", base)
        # Cloudflare cookies need the root domain (.darkiworld16.com)
        root_domain = "." + ".".join(domain.split(".")[-2:])
        for name, value in cookies.items():
            try:
                sb.driver.add_cookie(
                    {
                        "name": name,
                        "value": value,
                        "domain": root_domain,
                        "path": "/",
                    }
                )
            except Exception:
                pass

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
                    f"{_base_url()}/api/v1/titles", params=params
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
        items = data.get("pagination", {}).get("data") or data.get("data") or []
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
        loop = asyncio.get_running_loop()

        async with _SELENIUM_SEM:
            result = await loop.run_in_executor(
                None,
                self._get_links_sync,
                title_id,
                cookies,
                providers,
                season=None,
                episode=None,
            )
        return result

    def _get_links_sync(
        self,
        title_id: str,
        cookies: dict[str, str],
        providers: list[str],
        season: int | None,
        episode: int | None,
    ) -> list[ProviderLinks]:
        """
        Navigate to the download page, click each host button (Turnstile is handled
        automatically by SeleniumBase), capture the darki.zone URL from the XHR
        response, then resolve it to the actual provider URL.
        """
        base = _base_url()

        # Build the download page URL (episode-specific if needed)
        if season is not None and episode is not None:
            page_url = (
                f"{base}/titles/{title_id}/download?saison={season}&episode={episode}"
            )
        else:
            page_url = f"{base}/titles/{title_id}/download"

        with SB(uc=True, test=False, headless=True) as sb:
            # Inject cookies so we don't need a new login
            sb.driver.uc_open_with_reconnect(base, reconnect_time=3)
            time.sleep(2)
            self._inject_into_browser(sb, cookies)

            # Navigate to the download page
            sb.driver.uc_open_with_reconnect(page_url, reconnect_time=3)
            time.sleep(4)

            # Verify session is valid
            if "/login" in sb.driver.current_url:
                logger.warning("DarkiWorld: session expired during get_links_sync")
                self._invalidate_session()
                return []

            # Inject XHR interceptor to capture POST /liens/{id}/download responses
            sb.driver.execute_script("""
            window._dw_responses = [];
            const OrigXHR = window.XMLHttpRequest;
            function PatchedXHR() {
                const xhr = new OrigXHR();
                const origOpen = xhr.open.bind(xhr);
                xhr.open = function(method, url) {
                    this._dw_url = url;
                    this._dw_method = method;
                    return origOpen(method, url);
                };
                const origSend = xhr.send.bind(xhr);
                xhr.send = function(body) {
                    const self = this;
                    this.addEventListener('load', function() {
                        if (self._dw_url &&
                            self._dw_url.includes('/liens/') &&
                            self._dw_url.includes('/download') &&
                            self._dw_method === 'POST') {
                            window._dw_responses.push({
                                url: self._dw_url,
                                status: self.status,
                                body: self.responseText || ''
                            });
                        }
                    });
                    return origSend(body);
                };
                return xhr;
            }
            PatchedXHR.prototype = OrigXHR.prototype;
            window.XMLHttpRequest = PatchedXHR;
            """)

            # Find all download buttons
            btns = sb.driver.find_elements(
                By.CSS_SELECTOR, 'button[aria-label*="Download"]'
            )
            if not btns:
                logger.warning("DarkiWorld: no download buttons found on %s", page_url)
                return []

            grouped: dict[str, list[str]] = {}

            for btn in btns:
                # Identify the host from the button's img alt attribute
                imgs = btn.find_elements(By.TAG_NAME, "img")
                host_domain = imgs[0].get_attribute("alt") if imgs else ""
                host_name = host_domain.split(".")[0] if host_domain else "unknown"

                # Filter by requested providers (if any)
                if providers:
                    match = any(
                        p.lower() in host_name.lower() or host_name.lower() in p.lower()
                        for p in providers
                    )
                    if not match:
                        continue

                # Clear previous responses
                sb.driver.execute_script("window._dw_responses = []")

                # Click the button — SeleniumBase handles the Turnstile auto-solve
                try:
                    btn.click()
                except Exception as exc:
                    logger.debug(
                        "DarkiWorld: click failed for host %s: %s", host_name, exc
                    )
                    continue

                # Wait for XHR response (Turnstile may take a few seconds)
                deadline = time.time() + 15
                darki_url: str | None = None
                while time.time() < deadline:
                    time.sleep(1)
                    responses = json.loads(
                        sb.driver.execute_script(
                            "return JSON.stringify(window._dw_responses)"
                        )
                    )
                    if responses:
                        try:
                            resp_data = json.loads(responses[-1]["body"])
                            darki_url = resp_data.get("lien", {}).get(
                                "lien"
                            ) or resp_data.get("url")
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        break

                if not darki_url:
                    logger.debug(
                        "DarkiWorld: no darki.zone URL from button (host=%s)", host_name
                    )
                    continue

                # Close popup if open (click outside or close button)
                try:
                    _close_sel = (
                        '[role="dialog"] button[aria-label*="lose"],'
                        ' [role="dialog"] button[aria-label*="ermer"]'
                    )
                    close_btn = sb.driver.find_element(By.CSS_SELECTOR, _close_sel)
                    close_btn.click()
                    time.sleep(0.5)
                except Exception:
                    pass

                # Resolve darki.zone → actual provider URL
                final_url = self._resolve_darkizone_sync(sb, darki_url)
                if final_url:
                    grouped.setdefault(host_name, []).append(final_url)
                else:
                    logger.warning(
                        "DarkiWorld: could not resolve darki.zone URL for host %s",
                        host_name,
                    )

        return [ProviderLinks(provider=p, urls=urls) for p, urls in grouped.items()]

    def _resolve_darkizone_sync(self, sb: SB, darki_url: str) -> str | None:
        """
        Navigate to a darki.zone URL, click 'Continuer', and return the actual
        file-hosting URL (1fichier, darkibox, etc.).
        """
        try:
            sb.driver.get(darki_url)
            time.sleep(3)

            # Look for "Continuer" / "Continue" / "Accéder" button
            continuer = None
            for xpath in [
                "//button[contains(., 'Continuer')]",
                "//a[contains(., 'Continuer')]",
                "//button[contains(., 'Continue')]",
                "//a[contains(., 'Accéder')]",
            ]:
                try:
                    continuer = sb.driver.find_element(By.XPATH, xpath)
                    break
                except Exception:
                    pass

            if continuer:
                continuer.click()
                time.sleep(3)

            # Collect external URLs from the page (not darki.zone / darkiworld)
            links = sb.driver.find_elements(By.CSS_SELECTOR, "a[href]")
            for link in links:
                href = link.get_attribute("href") or ""
                if (
                    href.startswith("http")
                    and "darki" not in href
                    and "darkiworld" not in href
                ):
                    return href

            # Fallback: check current URL after redirect
            current = sb.driver.current_url
            if current and "darki" not in current and "darkiworld" not in current:
                return current

        except Exception as exc:
            logger.debug("DarkiWorld: darki.zone resolution failed: %s", exc)

        return None

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
                # Fetch seasons
                async with session.get(
                    f"{_base_url()}/api/v1/titles/{title_id}/seasons"
                ) as resp:
                    if "application/json" not in resp.content_type:
                        logger.warning(
                            "DarkiWorld get_episodes: non-JSON (session expired?)"
                        )
                        self._invalidate_session()
                        return []
                    if resp.status != 200:
                        logger.error(
                            "DarkiWorld /seasons returned HTTP %d", resp.status
                        )
                        return []
                    seasons_data = await resp.json()

                seasons = (
                    seasons_data
                    if isinstance(seasons_data, list)
                    else (
                        seasons_data.get("pagination", {}).get("data")
                        or seasons_data.get("data")
                        or []
                    )
                )

                episodes: list[Episode] = []
                for season in seasons:
                    season_id = season.get("id")
                    season_num = season.get("number", 1)
                    if not season_id:
                        continue

                    # Fetch episodes for this season
                    async with session.get(
                        f"{_base_url()}/api/v1/titles/{title_id}/seasons/{season_id}/episodes",
                        params={"perPage": 200},
                    ) as ep_resp:
                        if ep_resp.status != 200:
                            logger.warning(
                                "DarkiWorld /episodes returned HTTP %d for season %s",
                                ep_resp.status,
                                season_id,
                            )
                            continue
                        ep_data = await ep_resp.json()

                    ep_list = (
                        ep_data
                        if isinstance(ep_data, list)
                        else (
                            ep_data.get("pagination", {}).get("data")
                            or ep_data.get("data")
                            or []
                        )
                    )

                    for ep in ep_list:
                        ep_num = (
                            ep.get("episode_number")
                            or ep.get("number")
                            or (len(episodes) + 1)
                        )
                        ep_name = ep.get("name") or f"S{season_num:02d}E{ep_num:02d}"

                        # Provider links are fetched on demand via
                        # get_provider_links(season=, episode=).
                        episodes.append(
                            Episode(
                                title=f"S{season_num:02d}E{ep_num:02d} — {ep_name}",
                                number=ep_num,
                                provider_links=[],
                            )
                        )

        except aiohttp.ClientError as exc:
            logger.error("DarkiWorld get_episodes request failed: %s", exc)
            return []

        return episodes
