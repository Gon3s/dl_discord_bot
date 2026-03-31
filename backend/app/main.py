from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.queue import download_queue
from app.database import Base, AsyncSessionLocal, engine
from app.services.download_service import DownloadService


async def _run_download(download_id: str) -> None:
    async with AsyncSessionLocal() as session:
        service = DownloadService(session)
        await service.run(download_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    download_queue.set_handler(_run_download)
    download_queue.start()
    yield
    await download_queue.stop()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="dl_discord_bot API",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
