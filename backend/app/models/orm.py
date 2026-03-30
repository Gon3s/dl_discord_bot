import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Download(Base):
    __tablename__ = "downloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(50))
    destination: Mapped[str] = mapped_column(String(20), default="server")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    speed_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class History(Base):
    __tablename__ = "history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(Text)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(100))
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
