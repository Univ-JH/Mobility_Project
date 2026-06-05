from collections import defaultdict
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[device_id].add(websocket)

    def disconnect(self, device_id: str, websocket: WebSocket) -> None:
        self._connections[device_id].discard(websocket)

    async def broadcast(self, device_id: str, message: dict) -> None:
        dead: Set[WebSocket] = set()
        for ws in list(self._connections.get(device_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections[device_id] -= dead


ws_manager = ConnectionManager()
