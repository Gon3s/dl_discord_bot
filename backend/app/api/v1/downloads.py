from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue import download_queue
from app.database import get_db
from app.models.schemas import DownloadCreate, DownloadCreated, DownloadRead
from app.services.download_service import DownloadService

router = APIRouter()


@router.post("/downloads", response_model=DownloadCreated, status_code=201)
async def create_download(
    data: DownloadCreate,
    session: AsyncSession = Depends(get_db),
) -> DownloadCreated:
    service = DownloadService(session)
    download = await service.create(data)
    await download_queue.enqueue(download.id)
    return DownloadCreated(download_id=download.id, status=download.status)


@router.get("/downloads", response_model=list[DownloadRead])
async def list_downloads(
    session: AsyncSession = Depends(get_db),
) -> list[DownloadRead]:
    service = DownloadService(session)
    return await service.list_active()  # type: ignore[return-value]


@router.get("/downloads/{download_id}", response_model=DownloadRead)
async def get_download(
    download_id: str,
    session: AsyncSession = Depends(get_db),
) -> DownloadRead:
    service = DownloadService(session)
    download = await service.get(download_id)
    if download is None:
        raise HTTPException(status_code=404, detail="Download not found")
    return download  # type: ignore[return-value]


@router.delete("/downloads/{download_id}", status_code=204)
async def delete_download(
    download_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = DownloadService(session)
    download = await service.get(download_id)
    if download is None:
        raise HTTPException(status_code=404, detail="Download not found")

    if download.status in {"completed", "error", "cancelled", "ready_for_client"}:
        await service.delete(download_id)
        return

    download_queue.cancel(download_id)
    await service.cancel(download_id)


@router.post("/downloads/{download_id}/retry", response_model=DownloadCreated)
async def retry_download(
    download_id: str,
    session: AsyncSession = Depends(get_db),
) -> DownloadCreated:
    service = DownloadService(session)
    download = await service.retry(download_id)
    if download is None:
        raise HTTPException(
            status_code=404, detail="Download not found or not in error state"
        )
    await download_queue.enqueue(download.id)
    return DownloadCreated(download_id=download.id, status=download.status)
