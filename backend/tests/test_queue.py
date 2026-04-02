import asyncio

import pytest

from app.core.queue import DownloadQueue


class TestDownloadQueue:
    async def test_enqueue_increments_size(self) -> None:
        q = DownloadQueue()
        await q.enqueue("dl-1")
        await q.enqueue("dl-2")
        assert q.size == 2

    async def test_worker_calls_handler(self) -> None:
        q = DownloadQueue()
        processed: list[str] = []

        async def handler(download_id: str) -> None:
            processed.append(download_id)

        q.set_handler(handler)
        q.start()

        await q.enqueue("dl-abc")
        await asyncio.sleep(0.05)

        assert "dl-abc" in processed

        await q.stop()

    async def test_stop_cancels_workers(self) -> None:
        q = DownloadQueue()
        q.start()
        assert q.active > 0
        await q.stop()
        assert q.active == 0

    async def test_handler_exception_does_not_kill_worker(self) -> None:
        q = DownloadQueue()
        processed: list[str] = []

        async def handler(download_id: str) -> None:
            if download_id == "bad":
                raise RuntimeError("intentional error")
            processed.append(download_id)

        q.set_handler(handler)
        q.start()

        await q.enqueue("bad")
        await q.enqueue("good")
        await asyncio.sleep(0.1)

        assert "good" in processed

        await q.stop()
