import shutil

from fastapi import APIRouter

from app.config import settings
from app.core.queue import download_queue
from app.models.schemas import StatusRead
from app.services.debrid import get_debrid_client

router = APIRouter()


@router.get("/status", response_model=StatusRead)
async def get_status() -> StatusRead:
    try:
        free_bytes = shutil.disk_usage(settings.download_path).free
        disk_free_gb = round(free_bytes / 1_000_000_000, 2)
    except OSError:
        disk_free_gb = 0.0

    debrid_ok = await get_debrid_client().ping()

    return StatusRead(
        queue_size=download_queue.size,
        active=download_queue.active,
        disk_free_gb=disk_free_gb,
        debrid_ok=debrid_ok,
        debrid_provider=settings.debrid_provider,
        alldebrid_ok=debrid_ok,
    )
