from datetime import datetime
from typing import Literal

from pydantic import BaseModel, HttpUrl


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
    alldebrid_ok: bool


# --- WebSocket events ---


class WsProgressEvent(BaseModel):
    download_id: str
    status: str
    progress_pct: float
    speed_mbps: float | None = None
    eta_s: int | None = None
    filename: str | None = None
    debrid_url: str | None = None
