from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orm import Setting
from app.models.schemas import SettingRead, SettingsUpdate

router = APIRouter()


@router.get("/settings", response_model=list[SettingRead])
async def get_settings(
    session: AsyncSession = Depends(get_db),
) -> list[SettingRead]:
    result = await session.execute(select(Setting).order_by(Setting.key))
    return [SettingRead.model_validate(s) for s in result.scalars().all()]


@router.put("/settings", response_model=list[SettingRead])
async def update_settings(
    data: SettingsUpdate,
    session: AsyncSession = Depends(get_db),
) -> list[SettingRead]:
    for key, value in data.settings.items():
        existing = await session.get(Setting, key)
        if existing is None:
            existing = Setting(key=key, value=value)
            session.add(existing)
        else:
            existing.value = value
    await session.commit()

    result = await session.execute(select(Setting).order_by(Setting.key))
    return [SettingRead.model_validate(s) for s in result.scalars().all()]
