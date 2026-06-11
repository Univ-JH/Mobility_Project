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
    speedKph: float = 0.0
    roadType: str = "unknown"
    currentPolicyVersion: int = 1

class DevicePairRequest(BaseModel):
    deviceId: str = Field(..., example="dev-001")
    fwVersion: Optional[str] = None
    deviceType: Optional[str] = None

class DeviceUnlockRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None

class HeartbeatRequest(BaseModel):
    deviceId: str = Field(..., example="pi_01")

class AvailableDevice(BaseModel):
    deviceId: str
    lastSeenAt: Optional[datetime] = None

class AvailableDevicesResponse(BaseModel):
    devices: list[AvailableDevice]
