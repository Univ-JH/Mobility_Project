# IoT Device Pairing — Design Spec

**Date:** 2026-06-07  
**Status:** Approved  
**Scope:** Backend · Edge-Pi · Mobile

---

## Problem

`pair.tsx` currently uses a hardcoded 2-second fake scan and always pairs `dev-001`. Users cannot discover real nearby Raspberry Pi devices.

## Goal

Mobile app detects available Raspberry Pi devices on the same WiFi network via backend-mediated discovery, presents a list, lets the user select a device and its type, then completes pairing through the existing API.

---

## Approach: Backend-Mediated Discovery

Chosen over mDNS (requires native module, incompatible with Expo Go) and UDP broadcast (same issue). Backend acts as the discovery registry — Pi heartbeats in, mobile fetches the list.

---

## Architecture

```
Pi (startup + every 30s)
  └─ POST /v1/devices/heartbeat  {deviceId}
       └─ Backend: upsert device.lastHeartbeatAt = now()

Mobile (pair screen, every 5s poll)
  └─ GET /v1/devices/available
       └─ Backend: devices where lastHeartbeatAt >= now-60s
                   AND not in current user's paired list
       └─ Returns: [{ deviceId, lastSeenAt }]

User selects device + picks type
  └─ POST /v1/devices/pair  {deviceId, deviceType}
       └─ Backend: register pairing
  └─ Mobile: navigate back to devices tab
```

---

## Backend Changes

### New endpoint: `POST /v1/devices/heartbeat`

- **Auth:** `PRE_SHARED_TOKEN` (device → server, same as existing device auth)
- **Body:** `{ "deviceId": "pi_01" }`
- **Logic:** Upsert device document — set `lastHeartbeatAt = now()`. Create document if not exists.
- **Response:** `{ "success": true, "code": "OK", "data": {} }`
- **Error:** `AUTH_FORBIDDEN` if token invalid

### New endpoint: `GET /v1/devices/available`

- **Auth:** Bearer token (user)
- **Logic:**
  1. Find all devices where `lastHeartbeatAt >= now - 60s`
  2. Exclude devices already in the requesting user's paired device list
  3. Return minimal fields only
- **Response:**
  ```json
  {
    "success": true,
    "code": "OK",
    "data": {
      "devices": [
        { "deviceId": "pi_01", "lastSeenAt": "2026-06-07T12:00:00Z" },
        { "deviceId": "pi_02", "lastSeenAt": "2026-06-07T12:00:05Z" }
      ]
    }
  }
  ```

### Files to add/modify

| File | Change |
|---|---|
| `backend/app/api/v1/devices.py` | Add two new route handlers |
| `backend/app/services/device_service.py` | Add `heartbeat()` and `get_available()` methods |
| `backend/app/repositories/device_repository.py` | Add `upsert_heartbeat()` and `find_available()` queries |
| `backend/app/schemas/device_schemas.py` | Add `HeartbeatRequest`, `AvailableDevicesResponse` DTOs |

No changes to existing routes or schemas.

---

## Edge-Pi Changes

### Dependency: add `httpx` to `edge-pi/requirements.txt`

### New file: `edge-pi/src/communication/heartbeat.py`

```python
async def start(backend_url: str, device_id: str, token: str):
    """Send heartbeat on startup and every 30s indefinitely."""
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{backend_url}/v1/devices/heartbeat",
                    json={"deviceId": device_id},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5.0,
                )
        except Exception as e:
            print(f"⚠️ [HEARTBEAT] 전송 실패 (무시): {e}")
        await asyncio.sleep(30)
```

### `edge-pi/src/communication/comm_config.py`

Add two variables:
```python
BACKEND_URL = "http://52.79.242.44:8000"
PRE_SHARED_TOKEN = "<token>"   # matches backend .env
```

### `edge-pi/src/main.py`

Add heartbeat task to `asyncio.gather()`:
```python
asyncio.gather(
    ble_manager.start_listening(),   # existing
    mqtt_client.start(),             # existing
    heartbeat.start(BACKEND_URL, PI_ID, PRE_SHARED_TOKEN),  # new
)
```

---

## Mobile Changes

### `frontend-mobile/src/api/userApi.ts`

Add one function:
```typescript
getAvailableDevices: () =>
  axiosInstance.get<any, BaseResponse<{ devices: AvailableDevice[] }>>('/devices/available'),
```

Add type:
```typescript
export interface AvailableDevice {
  deviceId: string;
  lastSeenAt: string;
}
```

### `frontend-mobile/app/pair.tsx`

Full rewrite. States:

1. **scanning** — polling `GET /devices/available` every 5s, show spinner
2. **deviceList** — show found devices as tappable cards
3. **typeSelect** — after device selected, show type picker (킥보드 / 자전거 / 스쿠터)
4. **pairing** — call `POST /devices/pair`, show loading
5. **done** — navigate back to devices tab

Empty state: "주변에 장치가 없습니다" with retry button.
Error state: API failure → toast, keep polling.

### `frontend-mobile/src/hooks/useUserMutations.ts`

`usePairDevice`: add `queryClient.invalidateQueries({ queryKey: ['myDevices'] })` on success (currently missing).

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Pi offline (no heartbeat > 60s) | Disappears from available list naturally |
| Backend unreachable on mobile | Show "서버에 연결할 수 없습니다", retry button |
| Pair API fails (already paired) | Show error from API response message |
| Heartbeat POST fails on Pi | Log warning, retry next cycle — non-fatal |

---

## Out of Scope

- BLE-based discovery (future upgrade path)
- Pi device type self-reporting (user selects type at pairing time)
- Multi-user conflict resolution (same Pi paired by two users simultaneously)
