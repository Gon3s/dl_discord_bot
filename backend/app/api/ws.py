import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core import events

router = APIRouter()

_PING_INTERVAL = 30.0  # seconds


@router.websocket("/ws/downloads/{download_id}")
async def ws_download_progress(websocket: WebSocket, download_id: str) -> None:
    """Stream progress events for a specific download."""
    await websocket.accept()
    q = events.subscribe(download_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=_PING_INTERVAL)
                await websocket.send_json(event)
                if event.get("status") in ("completed", "error", "cancelled"):
                    break
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(download_id, q)


@router.websocket("/ws/queue")
async def ws_queue(websocket: WebSocket) -> None:
    """Stream progress events for all downloads (queue overview)."""
    await websocket.accept()
    q = events.subscribe(events.QUEUE_CHANNEL)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=_PING_INTERVAL)
                await websocket.send_json(event)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        events.unsubscribe(events.QUEUE_CHANNEL, q)
