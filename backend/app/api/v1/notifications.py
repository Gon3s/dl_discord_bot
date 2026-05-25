from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.orm import Notification
from app.models.schemas import NotificationCreate, NotificationPatch, NotificationRead
from app.services.notification_service import notification_scheduler

router = APIRouter()


@router.get("/notifications", response_model=list[NotificationRead])
async def list_notifications(
    session: AsyncSession = Depends(get_db),
) -> list[NotificationRead]:
    rows = await session.execute(select(Notification).order_by(Notification.title))
    return [NotificationRead.model_validate(n) for n in rows.scalars().all()]


@router.post("/notifications", response_model=NotificationRead, status_code=201)
async def add_notification(
    body: NotificationCreate,
    session: AsyncSession = Depends(get_db),
) -> NotificationRead:
    existing = await session.execute(
        select(Notification).where(Notification.url == body.url)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already watching this URL")

    notif = Notification(**body.model_dump())
    session.add(notif)
    await session.commit()
    await session.refresh(notif)
    return NotificationRead.model_validate(notif)


@router.delete("/notifications/{notification_id}", status_code=204)
async def remove_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    notif = await session.get(Notification, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.delete(notif)
    await session.commit()


@router.post("/notifications/test-discord", status_code=204)
async def test_discord_notification() -> None:
    if not settings.bot_notify_url:
        raise HTTPException(status_code=503, detail="BOT_NOTIFY_URL not configured")

    class _FakeNotif:
        title = "Test Notification"
        url = ""
        poster_url = None
        source = "wawacity"

    await notification_scheduler._notify_discord(_FakeNotif(), new_count=2, total=12)  # type: ignore[arg-type]


@router.patch("/notifications/{notification_id}", response_model=NotificationRead)
async def patch_notification(
    notification_id: str,
    body: NotificationPatch,
    session: AsyncSession = Depends(get_db),
) -> NotificationRead:
    notif = await session.get(Notification, notification_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    if body.auto_download is not None:
        notif.auto_download = body.auto_download
    if body.discord_notify is not None:
        notif.discord_notify = body.discord_notify

    await session.commit()
    await session.refresh(notif)
    return NotificationRead.model_validate(notif)
