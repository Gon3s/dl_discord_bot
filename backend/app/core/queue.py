import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.config import settings

logger = logging.getLogger(__name__)

_Handler = Callable[[str], Awaitable[None]]


class DownloadQueue:
    """Asyncio-based download queue with a configurable worker pool."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._active_jobs: dict[str, asyncio.Task] = {}
        self._cancelled: set[str] = set()
        self._handler: _Handler | None = None
        self._active_count: int = 0
        self._stopping = False

    def set_handler(self, handler: _Handler) -> None:
        """Set the coroutine that processes each download_id."""
        self._handler = handler

    async def enqueue(self, download_id: str) -> None:
        """Add a download job to the queue."""
        self._cancelled.discard(download_id)
        await self._queue.put(download_id)
        logger.debug(
            "Enqueued download %s (queue size: %d)", download_id, self._queue.qsize()
        )

    async def _worker(self) -> None:
        while True:
            download_id = await self._queue.get()
            if download_id in self._cancelled:
                self._cancelled.discard(download_id)
                self._queue.task_done()
                continue

            worker = asyncio.current_task()
            if worker is not None:
                self._active_jobs[download_id] = worker
            self._active_count += 1
            try:
                if self._handler is not None:
                    await self._handler(download_id)
            except asyncio.CancelledError:
                if self._stopping:
                    raise
                logger.info("Cancelled download job %s", download_id)
            except Exception:
                logger.exception(
                    "Unhandled error while processing download %s", download_id
                )
            finally:
                self._active_jobs.pop(download_id, None)
                self._cancelled.discard(download_id)
                self._active_count -= 1
                self._queue.task_done()

    def cancel(self, download_id: str) -> bool:
        """Cancel an active job or mark a queued job to be skipped."""
        self._cancelled.add(download_id)
        worker = self._active_jobs.get(download_id)
        if worker is not None:
            worker.cancel()
        return worker is not None

    def start(self) -> None:
        """Spawn worker tasks. Call once from the FastAPI lifespan."""
        self._stopping = False
        n = settings.max_concurrent_downloads
        for _ in range(n):
            task = asyncio.create_task(self._worker())
            self._workers.append(task)
        logger.info("DownloadQueue started with %d worker(s)", n)

    async def stop(self) -> None:
        """Cancel all workers and wait for them to finish."""
        self._stopping = True
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._active_jobs.clear()
        logger.info("DownloadQueue stopped")

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def active(self) -> int:
        return self._active_count


download_queue = DownloadQueue()
