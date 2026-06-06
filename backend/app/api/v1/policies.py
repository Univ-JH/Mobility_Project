from fastapi import APIRouter, Depends, HTTPException
from typing import Any, List
import uuid

from app.schemas.common import create_success_response
from app.api.deps import get_current_admin
from app.repositories.models import Policy
from pydantic import BaseModel

router = APIRouter(dependencies=[Depends(get_current_admin)])

class PolicyCreateRequest(BaseModel):
    name: str
    helmetRequired: bool
    maxSpeedKph: float
    sidewalkBrakeLevel: int

@router.post("")
async def create_policy(request: PolicyCreateRequest) -> Any:
    """Create a new policy version and make it active."""
    # Deactivate current active policies
    await Policy.find(Policy.isActive == True).update({"$set": {"isActive": False}})
    
    # Get max version
    last_policy = await Policy.find().sort(-Policy.version).first_or_none()
    new_version = last_policy.version + 1 if last_policy else 1
    
    policy_id = f"pol-{uuid.uuid4().hex[:8]}"
    new_policy = Policy(
        policyId=policy_id,
        version=new_version,
        name=request.name,
        helmetRequired=request.helmetRequired,
        maxSpeedKph=request.maxSpeedKph,
        sidewalkBrakeLevel=request.sidewalkBrakeLevel,
        isActive=True
    )
    await new_policy.insert()
    
    return create_success_response(data=new_policy.model_dump(), message="새 정책 버전이 생성 및 활성화되었습니다.")

@router.get("/active")
async def get_active_policy() -> Any:
    """Get the currently active policy."""
    policy = await Policy.find_one(Policy.isActive == True)
    if not policy:
        return create_success_response(
            data={
                "policyId": "default",
                "version": 1,
                "name": "기본 정책",
                "scope": "global",
                "priority": 100,
                "helmetRequired": True,
                "maxSpeedKph": 25.0,
                "sidewalkBrakeLevel": 2,
                "isActive": False,
                "effectiveFrom": None,
                "createdAt": None,
            },
            message="활성 정책이 없습니다. 기본값을 반환합니다.",
        )
    return create_success_response(data=policy.model_dump(), message="활성 정책 조회 성공")
