from fastapi import APIRouter, Depends
from typing import Any
from datetime import datetime, timezone
import uuid

from app.schemas.common import create_success_response
from app.schemas.event_dto import EmergencySOSRequest
from app.api.deps import get_current_user
from app.repositories.models import Event

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/emergency")
async def trigger_emergency(
    request: EmergencySOSRequest,
    user_id: str = Depends(get_current_user)
) -> Any:
    """Trigger an emergency SOS from the mobile app."""
    
    # In a real scenario, we would link this to the user's active ride/device.
    # For MVP, we insert a generic user_sos event.
    device_id = f"user-app-{user_id}"
    ride_id = str(uuid.uuid4())
    
    event = Event(
        deviceId=device_id,
        rideId=ride_id,
        seq=1,
        eventType="user_sos",
        severity="critical",
        confidence=1.0,
        payload={
            "reason": request.reason,
            "lat": request.lat,
            "lng": request.lng,
            "source": "mobile_app"
        },
        eventAt=datetime.now(timezone.utc)
    )
    await event.insert()
    
    from app.repositories.models import EmergencyCase
    from app.services.mqtt_service import publish_control_command
    
    # 1. Create EmergencyCase
    case_id = str(uuid.uuid4())
    emergency = EmergencyCase(
        caseId=case_id,
        deviceId=device_id,
        rideId=ride_id,
        status="OPEN"
    )
    await emergency.insert()
    
    # 2. Trigger push notification/Siren via MQTT
    await publish_control_command(
        device_id=device_id,
        action="set_idle_mode",
        params={"siren": True, "brakeLevel": 3},
        reason="User requested SOS via Mobile App"
    )
    
    return create_success_response(data={"eventId": str(event.id), "caseId": case_id}, message="긴급 구조 신호(SOS) 전송 및 제어 명령 발송 완료")
