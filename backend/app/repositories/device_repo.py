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

async def update_device_status(device_id: str, state: DeviceState, helmet_worn: bool, ble_connected: bool, event_timestamp: datetime, lat: float = 0.0, lng: float = 0.0):
    device = await get_device(device_id)
    if not device:
        return None
        
    # 최신 이벤트인지 확인 후 덮어쓰기 (순서 역전 방지)
    last_seen = device.lastSeenAt
    if last_seen and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if not last_seen or event_timestamp > last_seen:
        device.currentState = state
        device.helmetWorn = helmet_worn
        device.bleConnected = ble_connected
        device.lastSeenAt = event_timestamp
        device.updatedAt = datetime.now(timezone.utc)
        
        if lat != 0.0 or lng != 0.0:
            from app.repositories.models import Location
            device.lastLocation = Location(lat=lat, lng=lng)
            
        await device.save()
    
    return device
