from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/device/{device_id}")
async def device_telemetry_ws(device_id: str, websocket: WebSocket) -> None:
    """
    Mobile clients connect here to receive live telemetry for a device.
    Server pushes messages; client sends pings to keep the connection alive.
    """
    await ws_manager.connect(device_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(device_id, websocket)
    except Exception:
        ws_manager.disconnect(device_id, websocket)
