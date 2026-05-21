from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from datetime import datetime, timezone

from app.schemas.common import create_success_response
from app.api.deps import get_current_admin, get_current_user
from app.repositories.models import EmergencyCase
from pydantic import BaseModel

router = APIRouter(dependencies=[Depends(get_current_admin)])

class EmergencyResolveRequest(BaseModel):
    resolutionType: str
    note: str

@router.get("")
async def get_active_emergencies() -> Any:
    """Get all active emergencies (OPEN or ACKED)."""
    cases = await EmergencyCase.find({"status": {"$in": ["OPEN", "ACKED"]}}).sort(-EmergencyCase.openedAt).to_list()
    return create_success_response(data=[case.model_dump() for case in cases], message="활성 응급 케이스 조회 성공")

@router.post("/{case_id}/ack")
async def ack_emergency(case_id: str, admin_id: str = Depends(get_current_admin)) -> Any:
    """Acknowledge an emergency case."""
    case = await EmergencyCase.find_one(EmergencyCase.caseId == case_id)
    if not case:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        
    case.status = "ACKED"
    case.ackBy = admin_id
    case.ackAt = datetime.now(timezone.utc)
    await case.save()
    
    return create_success_response(data=case.model_dump(), message="응급 상황을 인지(ACK) 처리했습니다.")

@router.post("/{case_id}/resolve")
async def resolve_emergency(case_id: str, request: EmergencyResolveRequest) -> Any:
    """Resolve an emergency case."""
    case = await EmergencyCase.find_one(EmergencyCase.caseId == case_id)
    if not case:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        
    case.status = "RESOLVED"
    case.resolutionType = request.resolutionType
    case.note = request.note
    case.resolvedAt = datetime.now(timezone.utc)
    await case.save()
    
    return create_success_response(data=case.model_dump(), message="응급 상황을 종결(RESOLVED) 처리했습니다.")
