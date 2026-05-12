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
    
    event = Event(
        deviceId=f"user-app-{user_id}",
        rideId=str(uuid.uuid4()),  # Generates a pseudo ride ID if none active
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
    
    # Here we would also trigger a push notification to admin or emergency contacts
    
    return create_success_response(data={"eventId": str(event.id)}, message="긴급 구조 신호(SOS) 전송 완료")
