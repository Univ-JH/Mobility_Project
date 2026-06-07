# IoT Device Pairing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded fake-scan pair screen with real backend-mediated IoT device discovery — Pi heartbeats its presence to the backend, mobile fetches the live list, user picks a device and type, then pairs via existing API.

**Architecture:** Pi sends `POST /v1/devices/heartbeat` on startup and every 30s; backend upserts `lastHeartbeatAt` on the Device document. Mobile polls `GET /v1/devices/available` (devices seen ≤60s ago that the current user hasn't paired) and presents a selectable list. User picks device + type → `POST /v1/devices/pair` (existing endpoint, unchanged).

**Tech Stack:** FastAPI + Beanie (MongoDB), Python `httpx` (Pi async HTTP), React Native + TanStack Query (mobile polling)

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `backend/app/repositories/models.py` | Modify | Add `lastHeartbeatAt` field to `Device` |
| `backend/app/schemas/device_dto.py` | Modify | Add `HeartbeatRequest`, `AvailableDevice` DTOs |
| `backend/app/repositories/device_repo.py` | Modify | Add `upsert_heartbeat()`, `get_available_devices()` |
| `backend/app/api/deps.py` | Modify | Add `get_device_auth` dependency |
| `backend/app/api/v1/devices.py` | Modify | Add `POST /heartbeat`, `GET /available` routes |
| `backend/requirements.txt` | Modify | Add `pytest`, `httpx`, `pytest-asyncio` |
| `backend/tests/__init__.py` | Create | Make tests a package |
| `backend/tests/conftest.py` | Create | Patch DB/MQTT startup for tests |
| `backend/tests/test_device_discovery.py` | Create | Tests for new endpoints |
| `edge-pi/requirements.txt` | Create | Add `httpx` + existing deps |
| `edge-pi/src/communication/heartbeat.py` | Create | Async heartbeat loop |
| `edge-pi/src/communication/comm_config.py` | Modify | Add `BACKEND_URL`, `PRE_SHARED_TOKEN` |
| `edge-pi/main.py` | Modify | Start heartbeat task in main loop |
| `frontend-mobile/src/api/userApi.ts` | Modify | Add `AvailableDevice` type + `getAvailableDevices()` |
| `frontend-mobile/app/pair.tsx` | Modify | Rewrite with real discovery list + type picker |
| `frontend-mobile/app/(tabs)/devices.tsx` | Modify | `+` button → navigate to `/pair`, remove inline modal |
| `frontend-mobile/src/hooks/useUserMutations.ts` | Modify | `usePairDevice`: add `invalidateQueries(['myDevices'])` |

---

## Task 1: Backend — Add `lastHeartbeatAt` to Device model + DTOs

**Files:**
- Modify: `backend/app/repositories/models.py`
- Modify: `backend/app/schemas/device_dto.py`

- [ ] **Step 1: Add `lastHeartbeatAt` field to Device document**

In `backend/app/repositories/models.py`, add one import and one field to the `Device` class:

```python
# Add to existing imports at top of file (datetime already imported)
# No new imports needed — Optional and datetime already present

class Device(Document):
    deviceId: Indexed(str, unique=True)
    deviceType: str
    ownerUserId: str
    fwVersion: str
    
    currentState: DeviceState = DeviceState.IDLE
    lastSeenAt: Optional[datetime] = None
    lastHeartbeatAt: Optional[datetime] = None   # ← ADD THIS LINE
    helmetWorn: bool = False
    bleConnected: bool = False
    speedKph: float = 0.0
    currentRoadType: str = "unknown"
    currentPolicyVersion: int = 1
    lastLocation: Optional[Location] = None
    
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "devices"
```

- [ ] **Step 2: Add DTOs to `device_dto.py`**

Append to the bottom of `backend/app/schemas/device_dto.py`:

```python
class HeartbeatRequest(BaseModel):
    deviceId: str = Field(..., example="pi_01")

class AvailableDevice(BaseModel):
    deviceId: str
    lastSeenAt: Optional[datetime] = None

class AvailableDevicesResponse(BaseModel):
    devices: list[AvailableDevice]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/repositories/models.py backend/app/schemas/device_dto.py
git commit -m "feat: add lastHeartbeatAt to Device model and discovery DTOs"
```

---

## Task 2: Backend — Test setup + failing tests

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_device_discovery.py`

- [ ] **Step 1: Add test deps to `backend/requirements.txt`**

Append to `backend/requirements.txt`:

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **Step 2: Install new test deps**

```bash
cd backend
pip install pytest pytest-asyncio "httpx>=0.27.0"
```

Expected: packages install without error.

- [ ] **Step 3: Create `backend/tests/__init__.py`**

Create empty file:

```python
```

- [ ] **Step 4: Create `backend/tests/conftest.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    mock_client = MagicMock()
    mock_client.close = MagicMock()
    with patch("app.core.database.init_db", new_callable=AsyncMock, return_value=mock_client):
        with patch("app.workers.mqtt_client.start_mqtt_worker", new_callable=AsyncMock):
            from app.main import app
            with TestClient(app) as c:
                yield c
```

- [ ] **Step 5: Create `backend/tests/test_device_discovery.py` with failing tests**

```python
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


PRE_SHARED_TOKEN = "proto-secret-token-123"
USER_TOKEN = "mock-jwt-token"


def test_heartbeat_returns_200_with_valid_token(client):
    with patch("app.api.v1.devices.upsert_heartbeat", new_callable=AsyncMock):
        resp = client.post(
            "/v1/devices/heartbeat",
            json={"deviceId": "pi_01"},
            headers={"Authorization": f"Bearer {PRE_SHARED_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_heartbeat_rejects_wrong_token(client):
    resp = client.post(
        "/v1/devices/heartbeat",
        json={"deviceId": "pi_01"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_heartbeat_rejects_missing_token(client):
    resp = client.post("/v1/devices/heartbeat", json={"deviceId": "pi_01"})
    assert resp.status_code == 401


def test_get_available_devices_returns_list(client):
    from app.repositories.models import Device
    from app.domain.states import DeviceState

    mock_device = MagicMock()
    mock_device.deviceId = "pi_01"
    mock_device.lastHeartbeatAt = datetime.now(timezone.utc)

    with patch("app.api.v1.devices.get_available_devices", new_callable=AsyncMock, return_value=[mock_device]):
        resp = client.get(
            "/v1/devices/available",
            headers={"Authorization": f"Bearer {USER_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["devices"]) == 1
    assert body["data"]["devices"][0]["deviceId"] == "pi_01"


def test_get_available_devices_rejects_missing_token(client):
    resp = client.get("/v1/devices/available")
    assert resp.status_code == 401
```

- [ ] **Step 6: Run tests — verify they fail**

```bash
cd backend
pytest tests/test_device_discovery.py -v
```

Expected: all 5 tests FAIL with errors like `404 Not Found` (routes don't exist yet) or import errors.

- [ ] **Step 7: Commit test scaffolding**

```bash
git add backend/requirements.txt backend/tests/
git commit -m "test: add failing tests for device discovery endpoints"
```

---

## Task 3: Backend — Repo functions

**Files:**
- Modify: `backend/app/repositories/device_repo.py`

- [ ] **Step 1: Add imports at top of `device_repo.py`**

The file already imports `datetime` and `timezone`. Add `timedelta`:

```python
from datetime import datetime, timezone, timedelta
```

Replace the existing import line:
```python
# BEFORE:
from datetime import datetime, timezone

# AFTER:
from datetime import datetime, timezone, timedelta
```

- [ ] **Step 2: Append two functions to `device_repo.py`**

Add at the bottom of `backend/app/repositories/device_repo.py`:

```python
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
        Device.ownerUserId != user_id,
    ).to_list()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/repositories/device_repo.py
git commit -m "feat: add upsert_heartbeat and get_available_devices repo functions"
```

---

## Task 4: Backend — Auth dep + new routes (make tests pass)

**Files:**
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/api/v1/devices.py`

- [ ] **Step 1: Add `get_device_auth` to `deps.py`**

Append to `backend/app/api/deps.py`:

```python
async def get_device_auth(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="AUTH_MISSING_TOKEN")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="AUTH_INVALID_SCHEME")
    if token != settings.PRE_SHARED_TOKEN:
        raise HTTPException(status_code=403, detail="AUTH_FORBIDDEN")
    return token
```

Also add the missing import at the top of `deps.py`:

```python
from app.core.config import settings
```

- [ ] **Step 2: Add new route imports and routes to `devices.py`**

At the top of `backend/app/api/v1/devices.py`, update the import block to add the new repo functions and dep:

```python
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
```

- [ ] **Step 3: Append two new routes to `devices.py`**

Add at the bottom of `backend/app/api/v1/devices.py` (before the final newline):

```python
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd backend
pytest tests/test_device_discovery.py -v
```

Expected output:
```
PASSED tests/test_device_discovery.py::test_heartbeat_returns_200_with_valid_token
PASSED tests/test_device_discovery.py::test_heartbeat_rejects_wrong_token
PASSED tests/test_device_discovery.py::test_heartbeat_rejects_missing_token
PASSED tests/test_device_discovery.py::test_get_available_devices_returns_list
PASSED tests/test_device_discovery.py::test_get_available_devices_rejects_missing_token
5 passed
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/deps.py backend/app/api/v1/devices.py
git commit -m "feat: add POST /devices/heartbeat and GET /devices/available endpoints"
```

---

## Task 5: Edge-Pi — Heartbeat module

**Files:**
- Create: `edge-pi/requirements.txt`
- Create: `edge-pi/src/communication/heartbeat.py`
- Modify: `edge-pi/src/communication/comm_config.py`
- Modify: `edge-pi/main.py`

- [ ] **Step 1: Create `edge-pi/requirements.txt`**

```
bleak>=0.21.0
aiomqtt>=2.0.0
httpx>=0.27.0
```

- [ ] **Step 2: Create `edge-pi/src/communication/heartbeat.py`**

```python
import asyncio
import httpx


async def start(backend_url: str, device_id: str, token: str) -> None:
    """Send heartbeat to backend on startup and every 30s."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{backend_url}/v1/devices/heartbeat",
                    json={"deviceId": device_id},
                    headers={"Authorization": f"Bearer {token}"},
                )
            print(f"[HEARTBEAT] ✅ 백엔드 heartbeat 전송 완료 (deviceId: {device_id})")
        except Exception as e:
            print(f"[HEARTBEAT] ⚠️ 전송 실패 (무시, 30초 후 재시도): {e}")
        await asyncio.sleep(30)
```

- [ ] **Step 3: Add `BACKEND_URL` and `PRE_SHARED_TOKEN` to `comm_config.py`**

Add at the bottom of `edge-pi/src/communication/comm_config.py`:

```python
# ==========================================
# [6] 백엔드 HTTP 설정 (heartbeat용)
# ==========================================
BACKEND_URL = "http://52.79.242.44:8000"
PRE_SHARED_TOKEN = "proto-secret-token-123"
```

- [ ] **Step 4: Update `edge-pi/main.py` to import and start heartbeat**

Add heartbeat import with the other communication imports:

```python
# 2. 통신 모듈
from src.communication.ble_manager import HelmetBLEManager
from src.communication.mqtt_client import BikeMQTTClient
from src.communication.comm_config import PI_ID, CMD_BUZZER_ALERT, BACKEND_URL, PRE_SHARED_TOKEN
from src.communication import heartbeat   # ← ADD THIS LINE
```

In `SmartBikeSystem.main_loop()`, change the task creation block from:

```python
        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
```

To:

```python
        self.mqtt.start()
        self.vision.start()
        self.location.start()
        asyncio.create_task(self.ble.start_listening())
        asyncio.create_task(heartbeat.start(BACKEND_URL, PI_ID, PRE_SHARED_TOKEN))
```

- [ ] **Step 5: Verify Pi can send heartbeat (manual test)**

On the Raspberry Pi, run:

```bash
cd edge-pi
python -c "
import asyncio
from src.communication.heartbeat import start
asyncio.run(start('http://52.79.242.44:8000', 'pi_01', 'proto-secret-token-123'))
" &
sleep 3
kill %1
```

Expected: `[HEARTBEAT] ✅ 백엔드 heartbeat 전송 완료 (deviceId: pi_01)` printed (or warning if server unreachable — both are acceptable).

- [ ] **Step 6: Commit**

```bash
git add edge-pi/requirements.txt edge-pi/src/communication/heartbeat.py edge-pi/src/communication/comm_config.py edge-pi/main.py
git commit -m "feat: add Pi heartbeat module for backend-mediated device discovery"
```

---

## Task 6: Mobile — API layer + pair screen rewrite + devices screen update

**Files:**
- Modify: `frontend-mobile/src/api/userApi.ts`
- Modify: `frontend-mobile/src/hooks/useUserMutations.ts`
- Modify: `frontend-mobile/app/pair.tsx`
- Modify: `frontend-mobile/app/(tabs)/devices.tsx`

- [ ] **Step 1: Add `AvailableDevice` type and `getAvailableDevices` to `userApi.ts`**

Add after the `MyDevice` interface in `frontend-mobile/src/api/userApi.ts`:

```typescript
export interface AvailableDevice {
  deviceId: string;
  lastSeenAt: string | null;
}
```

Add to the `userApi` object (after `deregisterDevice`):

```typescript
  getAvailableDevices: () =>
    axiosInstance.get<any, BaseResponse<{ devices: AvailableDevice[] }>>('/devices/available'),
```

- [ ] **Step 2: Fix `usePairDevice` to invalidate `myDevices` on success**

In `frontend-mobile/src/hooks/useUserMutations.ts`, update `usePairDevice`:

```typescript
export const usePairDevice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ deviceId, type }: { deviceId: string, type: string }) => 
      userApi.pairDevice(deviceId, type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myDevices'] });
      Alert.alert('연결 완료', '디바이스가 연결되었습니다.');
    },
    onError: (error: ApiError) => {
      Alert.alert('연결 실패', error.response?.data?.message ?? '디바이스 연결에 실패했습니다.');
    }
  });
};
```

- [ ] **Step 3: Rewrite `frontend-mobile/app/pair.tsx`**

Replace the entire file content with:

```typescript
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ActivityIndicator,
  FlatList, TouchableOpacity,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Bluetooth, Radio } from 'lucide-react-native';
import { SafeButton } from '../src/components/SafeButton';
import { usePairDevice } from '../src/hooks/useUserMutations';
import { userApi, type AvailableDevice } from '../src/api/userApi';

const DEVICE_TYPES = [
  { value: 'scooter', label: '킥보드' },
  { value: 'bike', label: '자전거' },
  { value: 'ebike', label: '전동 자전거' },
] as const;

type DeviceTypeValue = typeof DEVICE_TYPES[number]['value'];

export default function PairScreen() {
  const router = useRouter();
  const [selectedDevice, setSelectedDevice] = useState<AvailableDevice | null>(null);
  const [selectedType, setSelectedType] = useState<DeviceTypeValue>('scooter');
  const pairMutation = usePairDevice();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['availableDevices'],
    queryFn: async () => {
      const res = await userApi.getAvailableDevices();
      return res.data.devices;
    },
    refetchInterval: 5000,
    retry: false,
  });

  const devices = data ?? [];

  const handlePair = () => {
    if (!selectedDevice) return;
    pairMutation.mutate(
      { deviceId: selectedDevice.deviceId, type: selectedType },
      { onSuccess: () => router.back() },
    );
  };

  if (isLoading && devices.length === 0) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
        <Text style={styles.scanText}>주변 디바이스 검색 중...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>
          발견된 디바이스 {isLoading && <ActivityIndicator size="small" color="#3b82f6" />}
        </Text>

        {devices.length === 0 ? (
          <View style={styles.empty}>
            <Bluetooth size={40} color="#334155" />
            <Text style={styles.emptyText}>주변에 디바이스가 없습니다</Text>
            <TouchableOpacity onPress={() => refetch()}>
              <Text style={styles.retryText}>다시 검색</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={devices}
            keyExtractor={(item) => item.deviceId}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  styles.deviceCard,
                  selectedDevice?.deviceId === item.deviceId && styles.deviceCardSelected,
                ]}
                onPress={() => setSelectedDevice(item)}
              >
                <Radio size={20} color={selectedDevice?.deviceId === item.deviceId ? '#3b82f6' : '#64748b'} />
                <Text style={[
                  styles.deviceId,
                  selectedDevice?.deviceId === item.deviceId && styles.deviceIdSelected,
                ]}>
                  {item.deviceId}
                </Text>
              </TouchableOpacity>
            )}
          />
        )}
      </View>

      {selectedDevice && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>디바이스 타입</Text>
          <View style={styles.typeRow}>
            {DEVICE_TYPES.map((t) => (
              <TouchableOpacity
                key={t.value}
                style={[styles.typeChip, selectedType === t.value && styles.typeChipActive]}
                onPress={() => setSelectedType(t.value)}
              >
                <Text style={[styles.typeChipText, selectedType === t.value && styles.typeChipTextActive]}>
                  {t.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      <SafeButton
        title={pairMutation.isPending ? '연결 중...' : '연결하기'}
        onPress={handlePair}
        disabled={!selectedDevice || pairMutation.isPending}
        style={styles.button}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', padding: 20 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  scanText: { color: '#64748b', fontSize: 16 },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#64748b', letterSpacing: 1, marginBottom: 12 },
  empty: { alignItems: 'center', paddingVertical: 32, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 15 },
  retryText: { color: '#3b82f6', fontSize: 14, fontWeight: '600' },
  deviceCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: 16, borderRadius: 12, backgroundColor: '#fff',
    borderWidth: 1, borderColor: '#e2e8f0', marginBottom: 8,
  },
  deviceCardSelected: { borderColor: '#3b82f6', backgroundColor: '#eff6ff' },
  deviceId: { fontSize: 16, fontWeight: '600', color: '#334155' },
  deviceIdSelected: { color: '#3b82f6' },
  typeRow: { flexDirection: 'row', gap: 10 },
  typeChip: {
    flex: 1, padding: 12, borderRadius: 10,
    borderWidth: 1, borderColor: '#e2e8f0', alignItems: 'center',
    backgroundColor: '#fff',
  },
  typeChipActive: { borderColor: '#3b82f6', backgroundColor: '#eff6ff' },
  typeChipText: { color: '#94a3b8', fontWeight: '600', fontSize: 14 },
  typeChipTextActive: { color: '#3b82f6' },
  button: { marginTop: 'auto' },
});
```

- [ ] **Step 4: Replace `frontend-mobile/app/(tabs)/devices.tsx` with this complete file**

```typescript
import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Alert, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Bluetooth, Plus, Trash2, Wifi, WifiOff } from 'lucide-react-native';
import { useMyDevices } from '../../src/hooks/useUserQueries';
import { useDeregisterDevice } from '../../src/hooks/useUserMutations';
import type { MyDevice } from '../../src/api/userApi';

const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: '#10b981',
  RUNNING_LIMITED: '#f59e0b',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: '#ef4444',
  IDLE: '#64748b',
  READY: '#3b82f6',
};

const STATE_LABELS: Record<string, string> = {
  RUNNING_NORMAL: '주행 중',
  RUNNING_LIMITED: '제한 주행',
  AUTO_BRAKING: '자동 제동',
  EMERGENCY: '긴급',
  IDLE: '대기',
  READY: '준비됨',
};

export default function DevicesScreen() {
  const router = useRouter();
  const { data: devices, isLoading, refetch } = useMyDevices();
  const deregisterMutation = useDeregisterDevice();

  const handleDeregister = (device: MyDevice) => {
    Alert.alert(
      '디바이스 해제',
      `${device.deviceId}를 해제하시겠습니까?`,
      [
        { text: '취소', style: 'cancel' },
        { text: '해제', style: 'destructive', onPress: () => deregisterMutation.mutate(device.deviceId) },
      ],
    );
  };

  const renderDevice = ({ item }: { item: MyDevice }) => {
    const stateColor = STATE_COLORS[item.currentState] ?? '#64748b';
    return (
      <View style={styles.deviceCard}>
        <View style={styles.deviceLeft}>
          <View style={[styles.stateIndicator, { backgroundColor: stateColor }]} />
          <View>
            <Text style={styles.deviceId}>{item.deviceId}</Text>
            <Text style={styles.deviceType}>{STATE_LABELS[item.currentState] ?? item.currentState}</Text>
            <View style={styles.statusRow}>
              {item.bleConnected
                ? <Wifi size={12} color="#10b981" />
                : <WifiOff size={12} color="#64748b" />}
              <Text style={[styles.statusText, { color: item.bleConnected ? '#10b981' : '#64748b' }]}>
                {item.bleConnected ? '헬멧 연결됨' : '헬멧 미연결'}
              </Text>
            </View>
          </View>
        </View>
        <TouchableOpacity style={styles.deleteBtn} onPress={() => handleDeregister(item)}>
          <Trash2 size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>내 디바이스</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => router.push('/pair')}>
          <Plus size={20} color="#fff" />
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color="#3b82f6" />
      ) : (
        <FlatList
          data={devices ?? []}
          keyExtractor={(item) => item.deviceId}
          renderItem={renderDevice}
          contentContainerStyle={{ padding: 16, gap: 12 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Bluetooth size={48} color="#334155" />
              <Text style={styles.emptyText}>등록된 디바이스가 없습니다</Text>
              <Text style={styles.emptySubText}>+ 버튼으로 라즈베리파이를 등록하세요</Text>
            </View>
          }
          onRefresh={refetch}
          refreshing={isLoading}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingTop: 20, borderBottomWidth: 1, borderBottomColor: '#1e293b',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#f8fafc' },
  addBtn: {
    backgroundColor: '#3b82f6', width: 36, height: 36,
    borderRadius: 18, alignItems: 'center', justifyContent: 'center',
  },
  deviceCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderWidth: 1, borderColor: '#334155',
  },
  deviceLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  stateIndicator: { width: 10, height: 10, borderRadius: 5 },
  deviceId: { fontSize: 16, fontWeight: '700', color: '#f8fafc', marginBottom: 2 },
  deviceType: { fontSize: 12, color: '#64748b', marginBottom: 4 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  statusText: { fontSize: 12, fontWeight: '500' },
  deleteBtn: { padding: 8 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 16, fontWeight: '600' },
  emptySubText: { color: '#64748b', fontSize: 13 },
});
```

- [ ] **Step 5: Verify TypeScript compiles**

```bash
cd frontend-mobile
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend-mobile/src/api/userApi.ts \
        frontend-mobile/src/hooks/useUserMutations.ts \
        frontend-mobile/app/pair.tsx \
        frontend-mobile/app/(tabs)/devices.tsx
git commit -m "feat: implement IoT device discovery in pair screen"
```

---

## End-to-End Verification

After all tasks complete:

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start Pi: `cd edge-pi && python main.py` → watch for `[HEARTBEAT] ✅` log
3. Open mobile app → Devices tab → tap `+`
4. Verify: pi_01 appears in the list within 5 seconds
5. Select pi_01 → select type → tap "연결하기"
6. Verify: devices tab shows pi_01 in the registered list
