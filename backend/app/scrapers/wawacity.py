import asyncio
import logging
import re
import time

import aiohttp
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.wait import WebDriverWait
from seleniumbase import SB, Driver

from app.config import settings
from app.scrapers.base import (
    BaseScraper,
    Episode,
    ProviderLinks,
    SearchResult,
    register,
)

logger = logging.getLogger(__name__)

# Selenium ne supporte pas plusieurs sessions Chrome simultanées —
# on sérialise les appels _dl_protect_sync avec un semaphore à 1 slot.
_dl_protect_sem = asyncio.Semaphore(1)

_XPATH_LINK = '//*[@id="protected-container"]/div[2]/div/ul/li/a'

_LANGUAGE_MAP: dict[str, str] = {
    "FR": "🇫🇷",
    "EN": "🇬🇧",
    "VOSTFR": "🇬🇧🇫🇷",
    "MULTI": "🇪🇺",
}

_CATEGORY_MAP: dict[str, str] = {
    "film": "films",
    "serie": "series",
    "manga": "mangas",
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
        sort: str | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        wawa_category = _CATEGORY_MAP.get(category, category)
        params: dict[str, str | int] = {
            "search": query,
            "p": wawa_category,
            "s": sort or _SORT_MAP.get(wawa_category, "vostfr-hq"),
        }
        if year is not None:
            params["year"] = year
        if page > 1:
            params["page"] = page

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
        async with _dl_protect_sem:
            return await loop.run_in_executor(
                None, self._fetch_provider_links, url, providers
            )

    async def get_episodes(
        self,
        url: str,
        providers: list[str] | None = None,
    ) -> list[Episode]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        logger.error("Wawacity episodes returned HTTP %d", resp.status)
                        return []
                    data = await resp.read()
        except aiohttp.ClientError as exc:
            logger.error("Wawacity episodes request failed: %s", exc)
            return []

        return self._parse_episodes(
            data.decode("utf-8", errors="replace"), providers or []
        )

    def _parse_episodes(self, html: str, providers: list[str]) -> list[Episode]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="DDLLinks")
        if table is None:
            logger.warning("DDLLinks table not found on episode page")
            return []

        episodes: list[Episode] = []
        current_title: str | None = None
        current_number: int = 0
        current_links: dict[str, list[str]] = {}

        for tr in table.find_all("tr"):
            classes = tr.get("class", [])

            if "episode-title" in classes:
                # Save the previous episode group
                if current_title is not None:
                    episodes.append(
                        Episode(
                            title=current_title,
                            number=current_number,
                            provider_links=[
                                ProviderLinks(provider=p, urls=urls)
                                for p, urls in current_links.items()
                            ],
                        )
                    )
                # Parse the new episode title
                td = tr.find("td")
                text = td.get_text(strip=True) if td else ""
                text = re.sub(
                    r"\s*en\s+t[eé]l[eé]chargement.*$", "", text, flags=re.IGNORECASE
                ).strip()
                m = re.search(r"[ÉéEe]pisode\s+(\d+)", text)
                current_number = int(m.group(1)) if m else len(episodes) + 1
                current_title = f"Épisode {current_number}"
                current_links = {}

            elif "link-row" in classes and current_title is not None:
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                a = tds[0].find("a", href=True)
                provider_name = tds[1].get_text(strip=True)
                if not a or not provider_name:
                    continue
                if providers and provider_name not in providers:
                    continue
                current_links.setdefault(provider_name, []).append(a["href"])

        # Save the last episode group
        if current_title is not None:
            episodes.append(
                Episode(
                    title=current_title,
                    number=current_number,
                    provider_links=[
                        ProviderLinks(provider=p, urls=urls)
                        for p, urls in current_links.items()
                    ],
                )
            )

        return episodes

    async def resolve_link(self, url: str) -> str:
        """Resolve dl-protect intermediary pages to the actual provider URL."""
        if "dl-protect" in url:
            return await self._resolve_dl_protect(url)
        return url

    def _fetch_provider_links(
        self, url: str, providers: list[str]
    ) -> list[ProviderLinks]:
        driver = Driver(
            uc=True,
            headless=True,
            binary_location=settings.selenium_binary_location or None,
            chromium_arg="--no-sandbox --disable-dev-shm-usage",
        )
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
        async with _dl_protect_sem:
            return await loop.run_in_executor(None, self._dl_protect_sync, url)

    def _dl_protect_sync(self, url: str) -> str:
        binary_location = settings.selenium_binary_location or None
        with SB(
            uc=True,
            test=False,
            binary_location=binary_location,
            chromium_arg="--no-sandbox --disable-dev-shm-usage",
        ) as sb:
            logger.debug("Opening dl-protect: %s", url)
            sb.driver.uc_open_with_reconnect(url, reconnect_time=20)

            # Attendre que le Turnstile auto-résolve et active #subButton (jusqu'à 20s)
            for _ in range(40):
                try:
                    present = sb.is_element_present("#subButton")
                    btn_ready = present and sb.is_element_enabled("#subButton")
                    if btn_ready:
                        logger.debug("Turnstile auto-solved, button enabled")
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            else:
                # Turnstile pas résolu auto → tenter GUI click (nécessite Xvfb)
                logger.debug("Turnstile not auto-solved after 20s, trying GUI click")
                try:
                    sb.uc_gui_click_captcha()
                    time.sleep(3)
                except Exception as e:
                    logger.debug("GUI captcha click failed: %s", e)

            # Cliquer le bouton si activé, sinon soumettre via JS
            sub_present = sb.is_element_present("#subButton")
            btn_ok = sub_present and sb.is_element_enabled("#subButton")
            if btn_ok:
                sb.highlight_click("#subButton")
                logger.debug("Clicked #subButton (enabled)")
            elif sub_present:
                logger.warning("Button present but disabled after Turnstile, using JS")
                sb.js_click("#subButton")
            else:
                logger.warning(
                    "Button not found on page, skipping click"
                    " and searching for links directly"
                )

            # Chercher le lien résultant avec plusieurs stratégies
            try:
                sb.wait_for_element_present("#protected-container", timeout=15)
            except Exception:
                logger.warning(
                    "No #protected-container found after submit (page: %s)",
                    sb.driver.current_url,
                )

            # XPATH principal
            try:
                link = sb.find_element(By.XPATH, _XPATH_LINK)
                href = link.get_attribute("href")
                logger.debug("Resolved dl-protect → %s", href)
                return href
            except Exception:
                pass

            # Fallback : n'importe quel lien externe sur la page
            # (hors dl-protect lui-même) — dl-protect peut rediriger vers un
            # intermédiaire (ex: trbt.cc) qu'AllDebrid sait résoudre.
            try:
                all_links = sb.find_elements(By.XPATH, "//a[@href]")
                for a in all_links:
                    href = a.get_attribute("href") or ""
                    if href.startswith("http") and "dl-protect" not in href:
                        logger.info("Resolved dl-protect via broad fallback → %s", href)
                        return href
            except Exception:
                pass

            raise RuntimeError(f"dl_protect resolution failed for {url}")
