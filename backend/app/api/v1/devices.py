from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from app.schemas.common import create_success_response
from app.schemas.device_dto import DeviceCreate, DeviceStatusResponse, DevicePairRequest, DeviceUnlockRequest
from app.repositories.device_repo import create_or_update_device, get_device
from app.domain.states import DeviceState
from app.services.mqtt_service import publish_control_command
from app.api.deps import get_current_user

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

@router.post("/pair")
async def pair_device(
    request: DevicePairRequest, 
    user_id: str = Depends(get_current_user)
) -> Any:
    """Pair a detected BLE device with the current user."""
    device = await get_device(request.deviceId)
    if not device:
        # Create it if it doesn't exist
        device_in = DeviceCreate(
            deviceId=request.deviceId,
            deviceType=request.deviceType or "scooter",
            fwVersion=request.fwVersion or "1.0.0",
            ownerUserId=user_id
        )
        device = await create_or_update_device(device_in)
    else:
        # Update owner
        device.ownerUserId = user_id
        await device.save()
        
    return create_success_response(data={"deviceId": device.deviceId}, message="기기 페어링 완료")

@router.post("/{device_id}/unlock")
async def unlock_device(
    device_id: str,
    request: DeviceUnlockRequest,
    user_id: str = Depends(get_current_user)
) -> Any:
    """Unlock device from mobile app."""
    device = await get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        
    if device.ownerUserId != user_id:
        raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")
        
    # Send unlock command via MQTT
    await publish_control_command(device_id, "unlock", {"lat": request.lat, "lng": request.lng})
    
    # Optimistically set state to READY/RUNNING
    device.currentState = DeviceState.READY
    if request.lat and request.lng:
        from app.repositories.models import Location
        device.lastLocation = Location(lat=request.lat, lng=request.lng)
    await device.save()
    
    return create_success_response(data={"state": device.currentState.value}, message="기기 잠금 해제 요청 전송")

