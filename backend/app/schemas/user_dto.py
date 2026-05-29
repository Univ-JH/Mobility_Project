from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime

class UserProfileResponse(BaseModel):
    name: str
    email: str
    safetyScore: float
    appSettings: Dict[str, Any]

class RideHistoryItemDto(BaseModel):
    rideId: str
    startTime: datetime
    endTime: datetime
    durationMinutes: float
    alertCount: int

class RideHistoryResponse(BaseModel):
    history: List[RideHistoryItemDto]
