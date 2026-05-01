import logging
import re
from urllib.parse import quote, urljoin

import aiohttp
from bs4 import BeautifulSoup

from app.config import settings
from app.scrapers.base import (
    BaseScraper,
    Episode,
    ProviderLinks,
    SearchResult,
    register,
)

logger = logging.getLogger(__name__)

_CATEGORY_MAP: dict[str, str] = {
    "film": "Movies",
    "films": "Movies",
    "serie": "TV",
    "series": "TV",
    "manga": "Anime",
    "mangas": "Anime",
}

_QUALITY_RE = re.compile(
    r"\b(2160p|1080p|720p|480p|4k|uhd|bluray|blu-ray|"
    r"web[-_. ]?dl|webrip|brrip|dvdrip)\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")


def _base_url() -> str:
    return settings.url_1337x.rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }


def _parse_int(text: str) -> int:
    try:
        return int(text.strip().replace(",", ""))
    except ValueError:
        return 0


@register
class Scraper1337x(BaseScraper):
    source_name = "1337x"

    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
        sort: str | None = None,
        page: int = 1,
    ) -> list[SearchResult]:
        del sort
        cat = _CATEGORY_MAP.get(category, category)
        url = f"{_base_url()}/category-search/{quote(query)}/{cat}/{page}/"

        try:
            async with aiohttp.ClientSession(headers=_headers()) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"1337x search returned HTTP {resp.status}")
                    data = await resp.read()
        except aiohttp.ClientError as exc:
            raise RuntimeError(f"1337x search request failed for {url}: {exc}") from exc

        results = self._parse_results(data, limit)
        if year is not None:
            results = [result for result in results if result.year == year]
        return results

    def _parse_results(self, data: bytes, limit: int) -> list[SearchResult]:
        soup = BeautifulSoup(data, "html.parser")
        results: list[SearchResult] = []
        base = _base_url()

        for row in soup.select(".table-list tbody tr"):
            if len(results) >= limit:
                break

            seeds_cell = row.select_one(".coll-2.seeds")
            if seeds_cell is None or _parse_int(seeds_cell.get_text()) <= 0:
                continue

            name_cell = row.select_one(".coll-1.name")
            if name_cell is None:
                continue
            anchors = name_cell.find_all("a", href=True)
            if not anchors:
                continue

            anchor = anchors[-1]
            title = anchor.get_text(strip=True)
            href = anchor["href"]
            url = href if href.startswith("http") else urljoin(f"{base}/", href)

            quality_match = _QUALITY_RE.search(title)
            year_match = _YEAR_RE.search(title)

            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    source=self.source_name,
                    year=int(year_match.group(1)) if year_match else None,
                    quality=quality_match.group(1) if quality_match else None,
                    language=None,
                )
            )

        return results

    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]:
        if providers and "magnet" not in providers:
            return []

        try:
            async with aiohttp.ClientSession(headers=_headers()) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"1337x detail returned HTTP {resp.status}")
                    html = (await resp.read()).decode("utf-8", errors="replace")
        except aiohttp.ClientError as exc:
            raise RuntimeError(f"1337x detail request failed for {url}: {exc}") from exc

        magnet = self._parse_magnet(html)
        if magnet is None:
            return []
        return [ProviderLinks(provider="magnet", urls=[magnet])]

    def _parse_magnet(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        anchor = soup.find("a", href=lambda href: href and href.startswith("magnet:"))
        return anchor["href"] if anchor else None

    async def get_episodes(
        self,
        url: str,
        providers: list[str] | None = None,
    ) -> list[Episode]:
        provider_links = await self.get_provider_links(url, providers or [])
        if not provider_links:
            return []
        return [
            Episode(
                title="Torrent",
                number=1,
                provider_links=provider_links,
            )
        ]
