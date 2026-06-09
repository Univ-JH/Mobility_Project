from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from app.schemas.common import create_success_response
from app.schemas.device_dto import (
    DeviceCreate, DeviceStatusResponse, DevicePairRequest,
    DeviceUnlockRequest, HeartbeatRequest, AvailableDevice,
    AvailableDevicesResponse,
)
from app.repositories.device_repo import (
    create_or_update_device, get_device,
    upsert_heartbeat, get_available_devices,
)
from app.domain.states import DeviceState
from app.services.mqtt_service import publish_control_command
from app.api.deps import get_current_user, get_device_auth

router = APIRouter()

# ── literal routes first (before parameterised) to prevent 405 shadowing ──

@router.post("")
async def register_device(device_in: DeviceCreate) -> Any:
    device = await create_or_update_device(device_in)
    return create_success_response(
        data={"deviceId": device.deviceId, "currentPolicyVersion": device.currentPolicyVersion},
        message="장치 등록 성공"
    )

@router.get("")
async def list_my_devices(user_id: str = Depends(get_current_user)) -> Any:
    from app.repositories.device_repo import get_devices_by_owner
    devices = await get_devices_by_owner(user_id)
    return create_success_response(
        data=[
            {
                "deviceId": d.deviceId,
                "deviceType": d.deviceType,
                "currentState": d.currentState.value,
                "bleConnected": d.bleConnected,
                "helmetWorn": d.helmetWorn,
                "lastSeenAt": d.lastSeenAt.isoformat() if d.lastSeenAt else None,
            }
            for d in devices
        ],
        message="디바이스 목록 조회 성공"
    )

@router.post("/pair")
async def pair_device(
    request: DevicePairRequest,
    user_id: str = Depends(get_current_user)
) -> Any:
    device = await get_device(request.deviceId)
    if not device:
        device_in = DeviceCreate(
            deviceId=request.deviceId,
            deviceType=request.deviceType or "scooter",
            fwVersion=request.fwVersion or "1.0.0",
            ownerUserId=user_id
        )
        device = await create_or_update_device(device_in)
    else:
        device.ownerUserId = user_id
        device.lastSeenAt = datetime.now(timezone.utc)
        device.updatedAt = datetime.now(timezone.utc)
        await device.save()
    return create_success_response(data={"deviceId": device.deviceId}, message="기기 페어링 완료")


@router.post("/heartbeat")
async def device_heartbeat(
    request: HeartbeatRequest,
    _: str = Depends(get_device_auth),
) -> Any:
    await upsert_heartbeat(request.deviceId)
    return create_success_response(data={}, message="heartbeat 수신")


@router.get("/available")
async def list_available_devices(
    user_id: str = Depends(get_current_user),
) -> Any:
    devices = await get_available_devices(user_id)
    return create_success_response(
        data={
            "devices": [
                {
                    "deviceId": d.deviceId,
                    "lastSeenAt": d.lastHeartbeatAt.isoformat() if d.lastHeartbeatAt else None,
                }
                for d in devices
            ]
        },
        message="사용 가능한 디바이스 목록"
    )


# ── parameterised routes after all literals ──

@router.delete("/{device_id}")
async def deregister_device_route(device_id: str, user_id: str = Depends(get_current_user)) -> Any:
    from app.repositories.device_repo import deregister_device
    success = await deregister_device(device_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return create_success_response(data={"deviceId": device_id}, message="기기 등록 해제 완료")

@router.get("/{device_id}/status")
async def read_device_status(device_id: str, _: str = Depends(get_current_user)) -> Any:
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

@router.post("/{device_id}/unlock")
async def unlock_device(
    device_id: str,
    request: DeviceUnlockRequest,
    user_id: str = Depends(get_current_user)
) -> Any:
    device = await get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    if device.ownerUserId != user_id:
        raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")
    await publish_control_command(device_id, "unlock", {"lat": request.lat, "lng": request.lng})
    device.currentState = DeviceState.READY
    if request.lat is not None and request.lng is not None:
        from app.repositories.models import Location
        device.lastLocation = Location(lat=request.lat, lng=request.lng)
    await device.save()
    return create_success_response(data={"state": device.currentState.value}, message="기기 잠금 해제 요청 전송")
