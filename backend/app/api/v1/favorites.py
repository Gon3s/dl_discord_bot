from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orm import Favorite
from app.models.schemas import FavoriteCreate, FavoriteRead

router = APIRouter()


@router.get("/favorites", response_model=list[FavoriteRead])
async def list_favorites(session: AsyncSession = Depends(get_db)) -> list[FavoriteRead]:
    rows = await session.execute(select(Favorite).order_by(Favorite.added_at.desc()))
    return [FavoriteRead.model_validate(f) for f in rows.scalars().all()]


@router.post("/favorites", response_model=FavoriteRead, status_code=201)
async def add_favorite(
    body: FavoriteCreate,
    session: AsyncSession = Depends(get_db),
) -> FavoriteRead:
    existing = await session.execute(select(Favorite).where(Favorite.url == body.url))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already in favorites")

    fav = Favorite(**body.model_dump())
    session.add(fav)
    await session.commit()
    await session.refresh(fav)
    return FavoriteRead.model_validate(fav)


@router.delete("/favorites/{favorite_id}", status_code=204)
async def remove_favorite(
    favorite_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    fav = await session.get(Favorite, favorite_id)
    if fav is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await session.delete(fav)
    await session.commit()
