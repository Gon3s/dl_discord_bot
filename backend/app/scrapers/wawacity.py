import asyncio
import logging
import re

import aiohttp
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import Driver, SB

from app.config import settings
from app.scrapers.base import BaseScraper, ProviderLinks, SearchResult, register

logger = logging.getLogger(__name__)

_XPATH_LINK = '//*[@id="protected-container"]/div[2]/div/ul/li/a'

_LANGUAGE_MAP: dict[str, str] = {
    "FR": "🇫🇷",
    "EN": "🇬🇧",
    "VOSTFR": "🇬🇧🇫🇷",
    "MULTI": "🇪🇺",
}

_SORT_MAP: dict[str, str] = {
    "films": "blu-ray_1080p-720p",
    "series": "vostfr-hq",
    "mangas": "vostfr-hq",
}


def _match_language(flag_class: str) -> str:
    lang = flag_class.replace("flag-", "").upper()
    return _LANGUAGE_MAP.get(lang, "🌐")


@register
class WawacityScraper(BaseScraper):
    source_name = "wawacity"

    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        params: dict[str, str | int] = {
            "search": query,
            "p": category,
            "s": _SORT_MAP.get(category, "vostfr-hq"),
        }
        if year is not None:
            params["year"] = year

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(
                    settings.wawacity_url, params=params, allow_redirects=True
                ) as resp:
                    if resp.status != 200:
                        logger.error("Wawacity search returned HTTP %d", resp.status)
                        return []
                    data = await resp.read()
        except aiohttp.ClientError as exc:
            logger.error("Wawacity search request failed: %s", exc)
            return []

        return self._parse_results(data, limit)

    def _parse_results(self, data: bytes, limit: int) -> list[SearchResult]:
        pattern = re.compile(r"^(.*?)\s\[(.*?)\]")
        results: list[SearchResult] = []
        soup = BeautifulSoup(data, "html.parser")
        base = settings.wawacity_url.rstrip("/")

        for element in soup.find_all("div", class_="wa-post-detail-item"):
            if len(results) >= limit:
                break

            post_title = element.find("div", class_="wa-sub-block-title")
            if not post_title:
                continue

            anchor = post_title.find("a")
            if not anchor:
                continue

            raw_title = anchor.text
            m = pattern.match(raw_title)
            title = m.group(1).strip() if m else raw_title.strip()
            quality = m.group(2).strip() if m else None

            href = anchor.get("href", "")
            url = href if href.startswith("http") else f"{base}{href}"

            img = element.find("img")
            poster_url: str | None = None
            if img:
                src = img.get("src", "")
                poster_url = src if src.startswith("http") else f"{base}{src}"

            year_val: int | None = None
            year_span = post_title.parent.parent.find("span", string="Année:")
            if year_span:
                b = year_span.find_next_sibling("b")
                if b:
                    try:
                        year_val = int(b.text.strip())
                    except ValueError:
                        pass

            language: str | None = None
            flag_i = post_title.find("i")
            if flag_i:
                classes = flag_i.get("class") or []
                if len(classes) > 1:
                    language = _match_language(classes[1])

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    source=self.source_name,
                    year=year_val,
                    quality=quality,
                    language=language,
                    poster_url=poster_url,
                )
            )

        return results

    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._fetch_provider_links, url, providers
        )

    def _fetch_provider_links(
        self, url: str, providers: list[str]
    ) -> list[ProviderLinks]:
        driver = Driver(uc=True, headless=True)
        try:
            driver.get(url)
            logger.debug("Loading provider page: %s", url)

            try:
                WebDriverWait(driver, 10).until(
                    presence_of_element_located((By.ID, "main-body"))
                )
            except Exception:
                logger.warning("Timed out waiting for main-body on %s", url)
                return []

            page_source = driver.page_source
        finally:
            driver.quit()

        soup = BeautifulSoup(page_source, "html.parser")
        table = soup.find("table", id="DDLLinks")
        if table is None:
            logger.warning("DDLLinks table not found on %s", url)
            return []

        grouped: dict[str, list[str]] = {}
        for tr in table.find_all("tr", class_="link-row"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            anchor = tds[0].find("a")
            if not anchor:
                continue
            provider = tds[1].text.strip()
            if providers and provider not in providers:
                continue
            grouped.setdefault(provider, []).append(anchor.get("href", ""))

        return [ProviderLinks(provider=p, urls=urls) for p, urls in grouped.items()]

    async def _resolve_dl_protect(self, url: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._dl_protect_sync, url)

    def _dl_protect_sync(self, url: str) -> str:
        with SB(uc=True, test=False) as sb:
            logger.debug("Opening dl-protect: %s", url)
            sb.driver.uc_open_with_reconnect(url, reconnect_time=20)

            try:
                sb.driver.switch_to_frame("iframe")
                sb.driver.uc_click("span")
            except Exception:
                logger.warning("Turnstile click failed, retrying")
                sb.driver.uc_open_with_reconnect(url, reconnect_time=2)
                sb.driver.switch_to_frame("iframe")
                sb.driver.uc_click("span")

            sb.highlight_click('button:contains("Continuer")')

            try:
                link = sb.find_element(By.XPATH, _XPATH_LINK)
                href = link.get_attribute("href")
                logger.debug("Resolved dl-protect → %s", href)
                return href
            except Exception as exc:
                raise RuntimeError(
                    f"dl_protect resolution failed for {url}"
                ) from exc
