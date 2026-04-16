from datetime import datetime, timezone
from typing import Optional
from app.repositories.models import Device
from app.domain.states import DeviceState
from app.schemas.device_dto import DeviceCreate

async def get_device(device_id: str) -> Optional[Device]:
    return await Device.find_one(Device.deviceId == device_id)

async def create_or_update_device(dto: DeviceCreate) -> Device:
    device = await get_device(dto.deviceId)
    if device:
        device.deviceType = dto.deviceType
        device.ownerUserId = dto.ownerUserId
        device.fwVersion = dto.fwVersion
        device.updatedAt = datetime.now(timezone.utc)
        await device.save()
        return device
    
    new_device = Device(
        deviceId=dto.deviceId,
        deviceType=dto.deviceType,
        ownerUserId=dto.ownerUserId,
        fwVersion=dto.fwVersion
    )
    await new_device.insert()
    return new_device

async def update_device_status(device_id: str, state: DeviceState, helmet_worn: bool, ble_connected: bool, event_timestamp: datetime):
    device = await get_device(device_id)
    if not device:
        return None
        
    # 최신 이벤트인지 확인 후 덮어쓰기 (순서 역전 방지)
    if not device.lastSeenAt or event_timestamp > device.lastSeenAt:
        device.currentState = state
        device.helmetWorn = helmet_worn
        device.bleConnected = ble_connected
        device.lastSeenAt = event_timestamp
        device.updatedAt = datetime.now(timezone.utc)
        await device.save()
    
    return device
