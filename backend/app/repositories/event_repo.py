from datetime import datetime, timezone
from typing import Optional
from pymongo.errors import DuplicateKeyError

from app.repositories.models import Event
from app.domain.states import DeviceState
from app.schemas.mqtt_payloads import EventPayload

async def save_event_idempotent(payload: EventPayload, anomaly: bool = False, state_from: Optional[DeviceState] = None, state_to: Optional[DeviceState] = None) -> Optional[Event]:
    """
    Saves an event ensuring idempotency using the constraint.
    Returns the created Event or None if it was a duplicate.
    """
    # 멱등성 검증 (deviceId, rideId, seq)
    existing = await Event.find_one(
        Event.deviceId == payload.deviceId,
        Event.rideId == payload.rideId,
        Event.seq == payload.seq
    )
    
    if existing:
        return None # Duplicate ignored
        
    event_doc = Event(
        deviceId=payload.deviceId,
        rideId=payload.rideId,
        seq=payload.seq,
        eventType=payload.eventType,
        severity=payload.severity,
        confidence=payload.confidence,
        stateFrom=state_from,
        stateTo=state_to,
        payload=payload.model_dump(),
        eventAt=payload.timestamp,
        ingestedAt=datetime.now(timezone.utc),
        anomaly=anomaly
    )
    
    try:
        await event_doc.insert()
        return event_doc
    except DuplicateKeyError:
        # DB 레벨에서 방어된 경우
        return None
