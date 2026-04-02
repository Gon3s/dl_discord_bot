import asyncio
from collections import defaultdict

QUEUE_CHANNEL = "__queue__"

_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


def subscribe(download_id: str) -> asyncio.Queue:
    """Register a new listener for a download and return its queue."""
    q: asyncio.Queue = asyncio.Queue()
    _subscribers[download_id].append(q)
    return q


def unsubscribe(download_id: str, queue: asyncio.Queue) -> None:
    """Remove a listener. Cleans up the entry when no listeners remain."""
    try:
        _subscribers[download_id].remove(queue)
    except ValueError:
        pass
    if not _subscribers[download_id]:
        _subscribers.pop(download_id, None)


async def emit(download_id: str, event: dict) -> None:
    """Push an event to all listeners subscribed to this download."""
    for q in list(_subscribers.get(download_id, [])):
        await q.put(event)
