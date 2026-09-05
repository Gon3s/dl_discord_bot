from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, Field, StringConstraints, field_validator

# --- Search ---


class SearchResult(BaseModel):
    title: str
    url: str
    year: int | None = None
    category: str | None = None
    quality: str | None = None
    language: str | None = None
    source: str
    poster_url: str | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    source: str
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


MediaType = Literal["films", "series", "mangas"]

_MEDIA_TYPE_ALIASES: dict[str, MediaType] = {
    "film": "films",
    "films": "films",
    "movie": "films",
    "serie": "series",
    "series": "series",
    "manga": "mangas",
    "mangas": "mangas",
}
_MAX_URL_LENGTH = 4096
_MAX_ALTERNATIVE_URLS = 20
_DownloadUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=_MAX_URL_LENGTH),
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
    media_type: MediaType
    destination: Literal["server", "client"] = "server"
    alternative_urls: list[_DownloadUrl] = Field(
        default_factory=list, max_length=_MAX_ALTERNATIVE_URLS
    )

    @field_validator("media_type", mode="before")
    @classmethod
    def normalize_media_type(cls, value: object) -> object:
        if isinstance(value, str):
            return _MEDIA_TYPE_ALIASES.get(value.lower(), value.lower())
        return value

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
    media_type: str
    destination: str
    status: str
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
    status: str


class DownloadClientResult(BaseModel):
    debrid_url: str


# --- History ---


class HistoryRead(BaseModel):
    id: str
    title: str
    source_url: str
    filename: str | None
    media_type: str
    source: str
    destination: str | None = None
    status: str
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
    debrid_provider: str
    alldebrid_ok: bool


# --- Favorites ---


class FavoriteCreate(BaseModel):
    title: str
    url: str
    category: str | None = None
    year: int | None = None
    quality: str | None = None
    language: str | None = None
    source: str
    poster_url: str | None = None


class FavoriteRead(BaseModel):
    id: str
    title: str
    url: str
    category: str | None
    year: int | None
    quality: str | None
    language: str | None
    source: str
    poster_url: str | None
    added_at: datetime

    model_config = {"from_attributes": True}


# --- Notifications ---


class NotificationCreate(BaseModel):
    title: str
    url: str
    source: str
    poster_url: str | None = None


class NotificationRead(BaseModel):
    id: str
    title: str
    url: str
    source: str
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
    status: str
    progress_pct: float
    speed_mbps: float | None = None
    eta_s: int | None = None
    filename: str | None = None
    debrid_url: str | None = None
    error: str | None = None
