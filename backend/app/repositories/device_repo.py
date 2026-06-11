from datetime import datetime, timezone, timedelta
from typing import Optional, List
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
        fwVersion=dto.fwVersion,
        lastSeenAt=datetime.now(timezone.utc),
    )
    await new_device.insert()
    return new_device

async def update_device_status(
    device_id: str,
    state: DeviceState,
    helmet_worn: bool,
    ble_connected: bool,
    event_timestamp: datetime,
    lat: float = 0.0,
    lng: float = 0.0,
    speed_kph: float = 0.0,
    road_type: str = "unknown",
) -> Optional[Device]:
    device = await get_device(device_id)
    if not device:
        return None

    if event_timestamp.tzinfo is None:
        event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
    last_seen = device.lastSeenAt
    if last_seen and last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if not last_seen or event_timestamp > last_seen:
        device.currentState = state
        device.helmetWorn = helmet_worn
        device.bleConnected = ble_connected
        device.speedKph = speed_kph
        device.currentRoadType = road_type
        device.lastSeenAt = event_timestamp
        device.updatedAt = datetime.now(timezone.utc)

        if lat != 0.0 or lng != 0.0:
            from app.repositories.models import Location
            device.lastLocation = Location(lat=lat, lng=lng)

        await device.save()

    return device

async def get_devices_by_owner(user_id: str) -> List[Device]:
    return await Device.find(Device.ownerUserId == user_id).to_list()

async def deregister_device(device_id: str, user_id: str) -> bool:
    device = await get_device(device_id)
    if not device or device.ownerUserId != user_id:
        return False
    device.ownerUserId = ""
    await device.save()
    return True


async def upsert_heartbeat(device_id: str) -> None:
    now = datetime.now(timezone.utc)
    device = await Device.find_one(Device.deviceId == device_id)
    if device:
        device.lastHeartbeatAt = now
        await device.save()
    else:
        new_device = Device(
            deviceId=device_id,
            deviceType="unknown",
            ownerUserId="",
            fwVersion="unknown",
            lastHeartbeatAt=now,
        )
        await new_device.insert()


async def get_available_devices(user_id: str) -> list[Device]:
    threshold = datetime.now(timezone.utc) - timedelta(seconds=60)
    return await Device.find(
        Device.lastHeartbeatAt >= threshold,
        Device.ownerUserId == "",
    ).to_list()


async def reset_stale_devices() -> int:
    """Set IDLE for devices whose heartbeat has been absent for >90s.
    Returns the number of devices reset."""
    threshold = datetime.now(timezone.utc) - timedelta(seconds=90)
    stale = await Device.find(
        Device.lastHeartbeatAt < threshold,
        Device.currentState != DeviceState.IDLE,
    ).to_list()
    for device in stale:
        device.currentState = DeviceState.IDLE
        device.speedKph = 0.0
        device.updatedAt = datetime.now(timezone.utc)
        await device.save()
    if stale:
        print(f"[Heartbeat GC] Reset {len(stale)} stale device(s) to IDLE")
    return len(stale)
