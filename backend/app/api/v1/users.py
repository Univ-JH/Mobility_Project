from fastapi import APIRouter, Depends
from typing import Any

from app.schemas.common import create_success_response
from app.services import user_service
from app.api.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/profile")
async def read_user_profile(user_id: str = Depends(get_current_user)) -> Any:
    profile = await user_service.get_user_profile(user_id)
    return create_success_response(data=profile.model_dump(), message="프로필 조회 성공")

@router.get("/history")
async def read_user_history(user_id: str = Depends(get_current_user)) -> Any:
    history = await user_service.get_ride_history(user_id)
    return create_success_response(data=history.model_dump(), message="주행 이력 조회 성공")
