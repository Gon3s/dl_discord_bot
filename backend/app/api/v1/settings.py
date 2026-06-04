from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.orm import Setting
from app.models.schemas import SettingRead, SettingsUpdate

router = APIRouter()

RUNTIME_SETTINGS = {
    "alldebrid_api_key",
    "app_public_url",
    "bot_notify_url",
    "debrid_provider",
    "max_concurrent_downloads",
    "notification_enabled",
    "notification_interval_hours",
    "realdebrid_api_token",
    "wawacity_url",
}

# Secrets never returned in clear. GET masks a non-empty value with MASK_VALUE;
# a PUT carrying MASK_VALUE is ignored so the client round-trip can't overwrite
# the real secret with the mask.
SENSITIVE_KEYS = {"alldebrid_api_key", "realdebrid_api_token"}
MASK_VALUE = "********"


def _masked(setting: Setting) -> SettingRead:
    value = setting.value
    if setting.key in SENSITIVE_KEYS and value:
        value = MASK_VALUE
    return SettingRead(key=setting.key, value=value)


def _runtime_value(key: str, value: str) -> str | int | bool:
    if key in ("max_concurrent_downloads", "notification_interval_hours"):
        return int(value)
    if key == "notification_enabled":
        return value.lower() in ("true", "1", "yes")
    if key == "debrid_provider":
        return value.lower()
    return value


@router.get("/settings", response_model=list[SettingRead])
async def get_settings(
    session: AsyncSession = Depends(get_db),
) -> list[SettingRead]:
    result = await session.execute(select(Setting).order_by(Setting.key))
    return [_masked(s) for s in result.scalars().all()]


@router.put("/settings", response_model=list[SettingRead])
async def update_settings(
    data: SettingsUpdate,
    session: AsyncSession = Depends(get_db),
) -> list[SettingRead]:
    for key, value in data.settings.items():
        # Ignore a masked secret echoed back by the client: keep the stored one.
        if key in SENSITIVE_KEYS and value == MASK_VALUE:
            continue
        existing = await session.get(Setting, key)
        if existing is None:
            existing = Setting(key=key, value=value)
            session.add(existing)
        else:
            existing.value = value
        if key in RUNTIME_SETTINGS and hasattr(settings, key):
            setattr(settings, key, _runtime_value(key, value))
    await session.commit()

    result = await session.execute(select(Setting).order_by(Setting.key))
    return [_masked(s) for s in result.scalars().all()]
