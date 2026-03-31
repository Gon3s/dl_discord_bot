import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_registry: dict[str, type["BaseScraper"]] = {}


@dataclass
class SearchResult:
    title: str
    url: str
    source: str
    year: int | None = None
    quality: str | None = None
    language: str | None = None
    poster_url: str | None = None


@dataclass
class ProviderLinks:
    provider: str
    urls: list[str] = field(default_factory=list)


def register(cls: type["BaseScraper"]) -> type["BaseScraper"]:
    _registry[cls.source_name] = cls
    logger.debug("Registered scraper: %s", cls.source_name)
    return cls


def get_scraper(source: str) -> "BaseScraper":
    if source not in _registry:
        raise KeyError(f"No scraper registered for source: {source!r}")
    return _registry[source]()


class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        category: str,
        year: int | None = None,
        limit: int = 10,
    ) -> list[SearchResult]: ...

    @abstractmethod
    async def get_provider_links(
        self,
        url: str,
        providers: list[str],
    ) -> list[ProviderLinks]: ...
