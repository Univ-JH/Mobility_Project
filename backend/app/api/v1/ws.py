from fastapi import APIRouter, WebSocket, Query
from app.services.ws_manager import ws_manager
from app.core.security import decode_access_token

router = APIRouter()


@router.websocket("/device/{device_id}")
async def device_telemetry_ws(
    device_id: str,
    websocket: WebSocket,
    token: str = Query(default=""),
) -> None:
    """
    Mobile clients connect here to receive live telemetry for a device.
    Server pushes messages; client sends pings to keep the connection alive.
    """
    try:
        payload = decode_access_token(token)
        if not payload.get("sub"):
            raise ValueError("missing sub")
    except Exception:
        await websocket.accept()
        await websocket.close(code=4001)
        return

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
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    finally:
        ws_manager.disconnect(device_id, websocket)
