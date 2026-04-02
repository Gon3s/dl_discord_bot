import asyncio

import pytest

from app.core import events


@pytest.fixture(autouse=True)
def clear_subscribers():
    events._subscribers.clear()
    yield
    events._subscribers.clear()


class TestEvents:
    async def test_subscribe_returns_queue(self) -> None:
        q = events.subscribe("dl-1")
        assert isinstance(q, asyncio.Queue)

    async def test_emit_delivers_to_subscriber(self) -> None:
        q = events.subscribe("dl-1")
        await events.emit("dl-1", {"status": "downloading"})
        event = q.get_nowait()
        assert event["status"] == "downloading"

    async def test_emit_delivers_to_multiple_subscribers(self) -> None:
        q1 = events.subscribe("dl-1")
        q2 = events.subscribe("dl-1")
        await events.emit("dl-1", {"status": "completed"})
        assert q1.get_nowait()["status"] == "completed"
        assert q2.get_nowait()["status"] == "completed"

    async def test_emit_does_not_deliver_to_other_download(self) -> None:
        q = events.subscribe("dl-2")
        await events.emit("dl-1", {"status": "downloading"})
        assert q.empty()

    async def test_unsubscribe_removes_queue(self) -> None:
        q = events.subscribe("dl-1")
        events.unsubscribe("dl-1", q)
        await events.emit("dl-1", {"status": "completed"})
        assert q.empty()

    async def test_unsubscribe_cleans_up_empty_entry(self) -> None:
        q = events.subscribe("dl-1")
        events.unsubscribe("dl-1", q)
        assert "dl-1" not in events._subscribers

    async def test_unsubscribe_tolerates_unknown_queue(self) -> None:
        q: asyncio.Queue = asyncio.Queue()
        events.unsubscribe("nonexistent", q)  # must not raise
