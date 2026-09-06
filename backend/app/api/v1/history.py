from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain import HistorySource, HistoryStatus
from app.models.orm import History
from app.models.schemas import HistoryList, HistoryRead

router = APIRouter()


@router.get("/history", response_model=HistoryList)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Filter by title"),
    status: HistoryStatus | None = Query(None, description="Filter by status"),
    provider: HistorySource | None = Query(
        None, description="Filter by source/provider"
    ),
    session: AsyncSession = Depends(get_db),
) -> HistoryList:
    base_query = select(History)
    if q:
        base_query = base_query.where(History.title.ilike(f"%{q}%"))
    if status:
        base_query = base_query.where(History.status == status)
    if provider:
        base_query = base_query.where(History.source == provider)

    count_result = await session.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    rows = await session.execute(
        base_query.order_by(History.downloaded_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list(rows.scalars().all())

    return HistoryList(
        items=[HistoryRead.model_validate(h) for h in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.delete("/history/{history_id}", status_code=204)
async def delete_history(
    history_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    entry = await session.get(History, history_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="History entry not found")
    await session.delete(entry)
    await session.commit()
