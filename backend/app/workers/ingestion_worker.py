import traceback
from typing import Dict, Any
from pydantic import ValidationError

from app.schemas.mqtt_payloads import TelemetryPayload, EventPayload
from app.repositories.event_repo import save_event_idempotent
from app.repositories.device_repo import update_device_status
from app.domain.states import DeviceState

async def handle_mqtt_message(topic: str, payload: Dict[str, Any]):
    """
    Validates payload using Pydantic, normalizes it, and saves to MongoDB.
    """
    try:
        if topic.endswith("/telemetry"):
            data = TelemetryPayload(**payload)
            await process_telemetry(data)
            
        elif topic.endswith("/event"):
            data = EventPayload(**payload)
            await process_event(data)
            
    except ValidationError as e:
        print(f"Schema Validation Error on topic {topic}: {e}")
    except Exception as e:
        print(f"Error handling message on {topic}: {e}")
        traceback.print_exc()

async def process_telemetry(data: TelemetryPayload):
    helmet_worn = data.helmet.worn if data.helmet else False
    ble_connected = data.health.bleConnected if data.health else False
    speed_kph = data.speedKph or 0.0
    road_type = data.vision.surfaceClass if data.vision else "unknown"

    from app.repositories.device_repo import get_device
    device = await get_device(data.deviceId)
    if not device:
        print(f"[Telemetry Dropped] Unknown device: {data.deviceId}")
    else:
        await update_device_status(
            device_id=data.deviceId,
            state=device.currentState,
            helmet_worn=helmet_worn,
            ble_connected=ble_connected,
            event_timestamp=data.timestamp,
            lat=data.latitude or 0.0,
            lng=data.longitude or 0.0,
            speed_kph=speed_kph,
            road_type=road_type,
        )

    from app.services.ws_manager import ws_manager
    await ws_manager.broadcast(data.deviceId, {
        "type": "telemetry_update",
        "deviceId": data.deviceId,
        "speedKph": speed_kph,
        "roadType": road_type,
        "helmetWorn": helmet_worn,
        "bleConnected": ble_connected,
        "timestamp": data.timestamp.isoformat(),
    })

    from app.services.policy_engine import evaluate_telemetry_policy
    await evaluate_telemetry_policy(data)

async def process_event(data: EventPayload):
    # 멱등성 검사가 내장된 저장 메서드 호출
    anomaly = False
    
    event_doc = await save_event_idempotent(payload=data, anomaly=anomaly)
    
    if event_doc:
        print(f"[Event Ingested] {data.deviceId} -> {data.eventType} (seq {data.seq})")
        from app.services.ws_manager import ws_manager
        await ws_manager.broadcast(data.deviceId, {
            "type": "event_notification",
            "deviceId": data.deviceId,
            "eventType": data.eventType,
            "severity": data.severity,
            "reason": data.reason,
            "confidence": data.confidence,
            "timestamp": data.timestamp.isoformat(),
        })
        from app.services.policy_engine import evaluate_event_policy
        await evaluate_event_policy(data)
    else:
        print(f"[Duplicate/Ignored] {data.deviceId} seq {data.seq}")
