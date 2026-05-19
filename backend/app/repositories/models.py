from typing import Optional, Any, Dict
from datetime import datetime, timezone
import pymongo
from beanie import Document, Indexed
from pydantic import Field

from app.domain.states import DeviceState
from pydantic import BaseModel, Field

class Location(BaseModel):
    lat: float
    lng: float

class User(Document):
    userId: Indexed(str, unique=True)
    email: str
    name: str
    safetyScore: float = 100.0
    appSettings: Dict[str, Any] = {}
    
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"

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
    lastLocation: Optional[Location] = None
    
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
        # Compound index for idempotency (unique constraint)
        indexes = [
            pymongo.IndexModel([("deviceId", pymongo.ASCENDING), ("rideId", pymongo.ASCENDING), ("seq", pymongo.ASCENDING)], unique=True)
        ]

class ControlCommandLog(Document):
    commandId: Indexed(str, unique=True)
    deviceId: Indexed(str)
    rideId: Optional[str] = None
    command: str
    params: Dict[str, Any] = {}
    reason: str
    
    issuedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ackAt: Optional[datetime] = None
    result: Optional[str] = None
    status: str = "PENDING"  # PENDING, ACKED, FAILED
    
    timeoutMs: int = 5000
    retryCount: int = 0
    
    class Settings:
        name = "control_command_logs"

class EmergencyCase(Document):
    caseId: Indexed(str, unique=True)
    deviceId: Indexed(str)
    rideId: Optional[str] = None
    
    openedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Indexed(str) = "OPEN" # OPEN, ACKED, RESOLVED, FALSE_ALARM
    
    ackBy: Optional[str] = None
    ackAt: Optional[datetime] = None
    resolvedAt: Optional[datetime] = None
    resolutionType: Optional[str] = None
    note: Optional[str] = None
    
    class Settings:
        name = "emergency_cases"
