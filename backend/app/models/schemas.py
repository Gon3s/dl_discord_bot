from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    StringConstraints,
    field_validator,
)

from app.models.domain import (
    DebridProvider,
    DownloadStatus,
    HistoryMediaType,
    HistorySource,
    HistoryStatus,
    MediaType,
    ScraperSource,
    parse_media_type,
)

# --- Search ---


class SearchResult(BaseModel):
    title: str
    url: str
    year: int | None = None
    category: MediaType | None = None
    quality: str | None = None
    language: str | None = None
    source: ScraperSource
    poster_url: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    source: ScraperSource
    page: int = 1


# --- Episodes ---


class EpisodeLinkRead(BaseModel):
    provider: str
    url: str


class EpisodeRead(BaseModel):
    title: str
    number: int
    links: list[EpisodeLinkRead]


# --- Downloads ---


_MAX_URL_LENGTH = 4096
_MAX_ALTERNATIVE_URLS = 20
_DownloadUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=_MAX_URL_LENGTH),
]


def _normalize_media_type(value: object) -> object:
    if isinstance(value, str):
        return parse_media_type(value)
    return value


_CanonicalMediaType = Annotated[MediaType, BeforeValidator(_normalize_media_type)]
_HistoryMediaType = Annotated[
    HistoryMediaType, BeforeValidator(_normalize_media_type)
]


def _validate_download_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https", "magnet"}:
        raise ValueError("URL scheme must be http, https, or magnet")

    if parsed.scheme == "magnet":
        if not parse_qs(parsed.query).get("xt"):
            raise ValueError("magnet URL must contain an xt parameter")
        return value

    if not parsed.hostname:
        raise ValueError("HTTP URL must contain a hostname")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")
    if parsed.hostname.lower() == "localhost":
        raise ValueError("local URLs are not allowed")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("private or reserved IP addresses are not allowed")
    return value


class DownloadCreate(BaseModel):
    source_url: _DownloadUrl
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    media_type: _CanonicalMediaType
    destination: Literal["server", "client"] = "server"
    alternative_urls: list[_DownloadUrl] = Field(
        default_factory=list, max_length=_MAX_ALTERNATIVE_URLS
    )

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _validate_download_url(value)

    @field_validator("alternative_urls")
    @classmethod
    def validate_alternative_urls(cls, values: list[str]) -> list[str]:
        return [_validate_download_url(value) for value in values]


class DownloadRead(BaseModel):
    id: str
    title: str
    source_url: str
    media_type: _CanonicalMediaType
    destination: str
    status: DownloadStatus
    progress_pct: float
    speed_mbps: float | None
    filename: str | None
    debrid_url: str | None = None
    created_at: datetime
    completed_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}


class DownloadCreated(BaseModel):
    download_id: str
    status: DownloadStatus


class DownloadClientResult(BaseModel):
    debrid_url: str


# --- History ---


class HistoryRead(BaseModel):
    id: str
    title: str
    source_url: str
    filename: str | None
    media_type: _HistoryMediaType
    source: HistorySource
    destination: str | None = None
    status: HistoryStatus
    error: str | None
    downloaded_at: datetime

    model_config = {"from_attributes": True}


class HistoryList(BaseModel):
    items: list[HistoryRead]
    total: int
    page: int
    limit: int


# --- Settings ---


class SettingRead(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    settings: dict[str, str]


# --- Status ---


class StatusRead(BaseModel):
    queue_size: int
    active: int
    disk_free_gb: float
    debrid_ok: bool
    debrid_provider: DebridProvider
    alldebrid_ok: bool


# --- Favorites ---


class FavoriteCreate(BaseModel):
    title: str
    url: str
    category: MediaType | None = None
    year: int | None = None
    quality: str | None = None
    language: str | None = None
    source: ScraperSource
    poster_url: str | None = None


class FavoriteRead(BaseModel):
    id: str
    title: str
    url: str
    category: MediaType | None
    year: int | None
    quality: str | None
    language: str | None
    source: ScraperSource
    poster_url: str | None
    added_at: datetime

    model_config = {"from_attributes": True}


# --- Notifications ---


class NotificationCreate(BaseModel):
    title: str
    url: str
    source: ScraperSource
    poster_url: str | None = None


class NotificationRead(BaseModel):
    id: str
    title: str
    url: str
    source: ScraperSource
    poster_url: str | None
    last_episode_count: int
    last_checked_at: datetime | None
    auto_download: bool
    discord_notify: bool

    model_config = {"from_attributes": True}


class NotificationPatch(BaseModel):
    auto_download: bool | None = None
    discord_notify: bool | None = None


# --- WebSocket events ---


class WsProgressEvent(BaseModel):
    download_id: str
    status: DownloadStatus
    progress_pct: float
    speed_mbps: float | None = None
    eta_s: int | None = None
    filename: str | None = None
    debrid_url: str | None = None
    error: str | None = None
