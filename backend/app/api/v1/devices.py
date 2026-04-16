from fastapi import APIRouter, HTTPException
from typing import Any

from app.schemas.common import create_success_response
from app.schemas.device_dto import DeviceCreate, DeviceStatusResponse
from app.repositories.device_repo import create_or_update_device, get_device

router = APIRouter()

@router.post("")
async def register_device(device_in: DeviceCreate) -> Any:
    """Register a new device."""
    device = await create_or_update_device(device_in)
    return create_success_response(
        data={"deviceId": device.deviceId, "currentPolicyVersion": device.currentPolicyVersion},
        message="장치 등록 성공"
    )

@router.get("/{device_id}/status")
async def read_device_status(device_id: str) -> Any:
    """Read current status of a device."""
    device = await get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        
    return create_success_response(
        data=DeviceStatusResponse(
            state=device.currentState,
            lastSeenAt=device.lastSeenAt,
            helmetWorn=device.helmetWorn,
            bleConnected=device.bleConnected,
            currentPolicyVersion=device.currentPolicyVersion
        ).model_dump()
    )
