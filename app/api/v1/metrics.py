from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.services import stash, prowlarr

router = APIRouter(prefix="/metrics", tags=["metrics"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Gather real-time stats
            stats = {
                "stash": {},
                "redis": "connected",
                "torbox": "connected"
            }
            try:
                s_stats = stash.stats().get("data", {}).get("stats", {})
                stats["stash"] = s_stats
            except:
                pass
                
            await websocket.send_json(stats)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
