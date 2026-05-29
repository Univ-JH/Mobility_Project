from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, ConfigDict
import uuid

T = TypeVar("T")

class BaseEnvelope(BaseModel):
    success: bool
    code: str
    message: str
    traceId: str
    
class SuccessResponse(BaseEnvelope, Generic[T]):
    data: Optional[T] = None
    
def create_success_response(data: Any = None, message: str = "성공", code: str = "OK") -> dict:
    return {
        "success": True,
        "code": code,
        "message": message,
        "data": data,
        "traceId": str(uuid.uuid4())
    }

def create_error_response(message: str, code: str) -> dict:
    return {
        "success": False,
        "code": code,
        "message": message,
        "data": None,
        "traceId": str(uuid.uuid4())
    }
