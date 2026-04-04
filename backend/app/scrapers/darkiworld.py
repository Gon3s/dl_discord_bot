from app.scrapers.base import BaseScraper, Episode, ProviderLinks, SearchResult, register


@register
class DarkiworldScraper(BaseScraper):
    source_name = "darkiworld"

    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
        sort: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError("darkiworld: not implemented yet")

    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]:
        raise NotImplementedError("darkiworld: not implemented yet")

    async def get_episodes(
        self,
        url: str,
        providers: list[str] | None = None,
    ) -> list[Episode]:
        raise NotImplementedError("darkiworld: not implemented yet")
