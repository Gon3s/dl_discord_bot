from fastapi import APIRouter

from app.api.v1 import (
    downloads,
    episodes,
    favorites,
    history,
    notifications,
    search,
    settings,
    status,
)

router = APIRouter(prefix="/api/v1")

router.include_router(search.router)
router.include_router(episodes.router)
router.include_router(downloads.router)
router.include_router(history.router)
router.include_router(favorites.router)
router.include_router(notifications.router)
router.include_router(settings.router)
router.include_router(status.router)
