from datetime import datetime
from typing import Literal

from pydantic import BaseModel

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


class DownloadCreate(BaseModel):
    source_url: str
    title: str
    media_type: str
    destination: Literal["server", "client"] = "server"
    alternative_urls: list[str] = []


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
