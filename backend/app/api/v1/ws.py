from fastapi import APIRouter, WebSocket
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
        # Send current DB state synchronously before entering receive loop.
        # Wrapped in try/except so any DB failure never closes the connection.
        try:
            from app.repositories.device_repo import get_device
            device = await get_device(device_id)
            if device:
                await websocket.send_json({
                    "type": "telemetry_update",
                    "deviceId": device_id,
                    "speedKph": device.speedKph,
                    "roadType": device.currentRoadType,
                    "helmetWorn": device.helmetWorn,
                    "bleConnected": device.bleConnected,
                    "state": device.currentState.value,
                    "timestamp": device.lastSeenAt.isoformat() if device.lastSeenAt else None,
                })
        except Exception:
            pass
        while True:
            await websocket.receive_text()
    finally:
        ws_manager.disconnect(device_id, websocket)
