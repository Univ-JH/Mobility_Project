from pydantic import BaseModel, Field
from typing import Optional

class EmergencySOSRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    reason: str = Field(..., example="Accident simulated")
