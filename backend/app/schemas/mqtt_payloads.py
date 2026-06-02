from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class HelmetData(BaseModel):
    worn: bool
    pressureAvg: Optional[float] = None
    pressureLeft: Optional[float] = None
    pressureRight: Optional[float] = None

class MotionData(BaseModel):
    accelX: float
    accelY: float
    accelZ: Optional[float] = None
    tiltRoll: float
    tiltPitch: float
    harshEvent: Optional[str] = None

class VisionData(BaseModel):
    surfaceClass: str = "unknown" # sidewalk, road, unknown
    sidewalkProb: float = 0.0
    frameCount: Optional[int] = None
    windowConsensus: Optional[float] = None

class HealthData(BaseModel):
    bleConnected: bool
    batteryPct: int
    bleRssi: Optional[int] = None
    cpuTempC: Optional[float] = None

class TelemetryPayload(BaseModel):
    schemaVersion: int = 1
    deviceId: str
    timestamp: datetime
    seq: int
    rideId: str
    helmet: Optional[HelmetData] = None
    motion: Optional[MotionData] = None
    vision: Optional[VisionData] = None
    health: Optional[HealthData] = None
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0

class EventContext(BaseModel):
    speedKph: float
    sidewalkProb: float
    helmetWorn: bool
    bleRssi: Optional[int] = None

class EventPayload(BaseModel):
    schemaVersion: int = 1
    deviceId: str
    timestamp: datetime
    seq: int
    rideId: str
    eventType: str
    severity: str # high, medium, low
    confidence: float
    reason: str
    context: EventContext
