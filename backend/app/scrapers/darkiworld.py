from app.scrapers.base import BaseScraper, ProviderLinks, SearchResult, register


@register
class DarkiworldScraper(BaseScraper):
    source_name = "darkiworld"

    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        raise NotImplementedError("darkiworld: not implemented yet")

    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]:
        raise NotImplementedError("darkiworld: not implemented yet")
