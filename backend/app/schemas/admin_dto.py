from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class AdminStatsResponse(BaseModel):
    activeDevices: int
    emergenciesToday: int
    helmetCompliance: float
    avgBattery: float

class DeviceLocationDto(BaseModel):
    deviceId: str
    lat: float
    lng: float
    state: str

class AlertsTimelineBucket(BaseModel):
    time: str
    count: int

class AlertsTimelineResponse(BaseModel):
    timeline: List[AlertsTimelineBucket]

class EnvironmentStatsResponse(BaseModel):
    sidewalkRatio: float
    roadRatio: float

class EventLogDto(BaseModel):
    eventId: str
    deviceId: str
    eventType: str
    severity: str
    reason: str
    confidence: float
    eventAt: datetime

class EventLogPaginatedResponse(BaseModel):
    items: List[EventLogDto]
    totalCount: int
    page: int
    size: int

class LocationDto(BaseModel):
    lat: float
    lng: float

class DeviceListItemDto(BaseModel):
    deviceId: str
    deviceType: str
    currentState: str
    lastSeenAt: Optional[datetime]
    lastHeartbeatAt: Optional[datetime]
    helmetWorn: bool
    bleConnected: bool
    lastLocation: Optional[LocationDto]
    fwVersion: str
    currentPolicyVersion: int
