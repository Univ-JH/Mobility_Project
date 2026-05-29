from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.domain.states import DeviceState

class DeviceCreate(BaseModel):
    deviceId: str = Field(..., example="dev-001")
    deviceType: str = Field(..., example="scooter")
    fwVersion: str = Field(..., example="1.0.0")
    ownerUserId: str = Field(..., example="user-123")

class DeviceStatusResponse(BaseModel):
    state: DeviceState
    lastSeenAt: Optional[datetime] = None
    helmetWorn: bool = False
    bleConnected: bool = False
    currentPolicyVersion: int = 1

class DevicePairRequest(BaseModel):
    deviceId: str = Field(..., example="dev-001")
    fwVersion: Optional[str] = None
    deviceType: Optional[str] = None

class DeviceUnlockRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
