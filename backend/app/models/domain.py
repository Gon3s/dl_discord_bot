from enum import StrEnum
from typing import Literal


class MediaType(StrEnum):
    FILMS = "films"
    SERIES = "series"
    MANGAS = "mangas"


MEDIA_TYPE_ALIASES: dict[str, MediaType] = {
    "film": MediaType.FILMS,
    "films": MediaType.FILMS,
    "movie": MediaType.FILMS,
    "serie": MediaType.SERIES,
    "series": MediaType.SERIES,
    "manga": MediaType.MANGAS,
    "mangas": MediaType.MANGAS,
}


def parse_media_type(value: str | MediaType) -> MediaType:
    normalized = MEDIA_TYPE_ALIASES.get(value.lower(), value.lower())
    return MediaType(normalized)


type HistoryMediaType = MediaType | Literal["unknown"]


class DownloadStatus(StrEnum):
    QUEUED = "queued"
    SCRAPING = "scraping"
    RESOLVING = "resolving"
    DEBRIDING = "debriding"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    # Kept for rows and clients created before client downloads used "completed".
    READY_FOR_CLIENT = "ready_for_client"


class HistoryStatus(StrEnum):
    COMPLETED = "completed"
    ERROR = "error"


class ScraperSource(StrEnum):
    WAWACITY = "wawacity"


class DebridProvider(StrEnum):
    ALLDEBRID = "alldebrid"
    REALDEBRID = "realdebrid"


type HistorySource = ScraperSource | DebridProvider


TERMINAL_DOWNLOAD_STATUSES = frozenset(
    {
        DownloadStatus.COMPLETED,
        DownloadStatus.ERROR,
        DownloadStatus.CANCELLED,
        DownloadStatus.READY_FOR_CLIENT,
    }
)
