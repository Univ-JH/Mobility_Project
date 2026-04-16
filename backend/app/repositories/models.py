from typing import Optional, Any, Dict
from datetime import datetime, timezone
import pymongo
from beanie import Document, Indexed
from pydantic import Field

from app.domain.states import DeviceState

class Device(Document):
    deviceId: Indexed(str, unique=True)
    deviceType: str
    ownerUserId: str
    fwVersion: str
    
    currentState: DeviceState = DeviceState.IDLE
    lastSeenAt: Optional[datetime] = None
    helmetWorn: bool = False
    bleConnected: bool = False
    currentPolicyVersion: int = 1
    
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "devices"

class Event(Document):
    deviceId: Indexed(str)
    rideId: str
    seq: int
    eventType: Indexed(str)
    severity: Indexed(str)
    confidence: float
    
    stateFrom: Optional[DeviceState] = None
    stateTo: Optional[DeviceState] = None
    
    payload: Dict[str, Any]
    
    eventAt: Indexed(datetime)
    ingestedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    anomaly: bool = False

    class Settings:
        name = "events"
        # Compound index for idempotency
        indexes = [
            [("deviceId", pymongo.ASCENDING), ("rideId", pymongo.ASCENDING), ("seq", pymongo.ASCENDING)]
        ]
