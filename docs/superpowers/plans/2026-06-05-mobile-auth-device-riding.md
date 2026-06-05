# Mobile Auth / Device Management / Riding Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add login, device(Pi) registration/deregistration, helmet BLE status, and a live riding screen (speed + road type + events via WebSocket) to the React Native mobile app.

**Architecture:** Backend gains a WebSocket endpoint (`/v1/ws/device/{deviceId}`) that receives MQTT telemetry, repackages it, and pushes it to connected mobile clients. Mobile gains an `AuthContext` (JWT stored in AsyncStorage), a device management tab, and a full-screen riding view that connects to the WS and renders live data. Existing MQTT ingestion worker is extended to call the WS manager after processing each telemetry/event message.

**Tech Stack:** FastAPI WebSocket, aiomqtt, Beanie/Motor, React Native Expo, @react-native-async-storage/async-storage, TanStack Query v5, Expo Router v3.

---

## File Map

### Backend — new / changed
| File | Action |
|---|---|
| `backend/app/repositories/device_repo.py` | Modify — add `get_devices_by_owner`, `deregister_device`, update `update_device_status` signature |
| `backend/app/repositories/models.py` | Modify — add `speedKph`, `currentRoadType` fields to `Device` |
| `backend/app/schemas/mqtt_payloads.py` | Modify — add `speedKph` to `TelemetryPayload` |
| `backend/app/api/v1/devices.py` | Modify — add `GET /devices` (user list) and `DELETE /devices/{id}` |
| `backend/app/services/ws_manager.py` | **Create** — `ConnectionManager` singleton |
| `backend/app/api/v1/ws.py` | **Create** — WebSocket router |
| `backend/app/api/router.py` | Modify — include `ws` router |
| `backend/app/workers/ingestion_worker.py` | Modify — broadcast to WS after telemetry/event processing |

### Mobile — new / changed
| File | Action |
|---|---|
| `frontend-mobile/src/context/AuthContext.tsx` | **Create** — JWT state, login/logout, AsyncStorage |
| `frontend-mobile/src/api/axiosInstance.ts` | Modify — token injection via module-level variable |
| `frontend-mobile/app/login.tsx` | **Create** — login screen |
| `frontend-mobile/app/index.tsx` | Modify — auth redirect (replace onboarding logic) |
| `frontend-mobile/app/_layout.tsx` | Modify — wrap with `AuthProvider` |
| `frontend-mobile/src/api/userApi.ts` | Modify — add `getMyDevices`, `registerDevice`, `deregisterDevice` |
| `frontend-mobile/src/hooks/useUserQueries.ts` | Modify — add `useMyDevices` |
| `frontend-mobile/src/hooks/useUserMutations.ts` | Modify — add `useRegisterDevice`, `useDeregisterDevice` |
| `frontend-mobile/app/(tabs)/devices.tsx` | **Create** — device management tab |
| `frontend-mobile/app/(tabs)/_layout.tsx` | Modify — add Devices tab |
| `frontend-mobile/app/(tabs)/index.tsx` | Modify — show real device list, Start Ride button |
| `frontend-mobile/src/hooks/useRidingWebSocket.ts` | **Create** — WS hook for riding screen |
| `frontend-mobile/app/riding/[deviceId].tsx` | **Create** — live riding screen |

---

## Task 1: Backend — User device list + deregister endpoints

**Files:**
- Modify: `backend/app/repositories/device_repo.py`
- Modify: `backend/app/api/v1/devices.py`

- [ ] **Step 1: Add repo functions**

Open `backend/app/repositories/device_repo.py` and append:

```python
from typing import List

async def get_devices_by_owner(user_id: str) -> List[Device]:
    return await Device.find(Device.ownerUserId == user_id).to_list()

async def deregister_device(device_id: str, user_id: str) -> bool:
    device = await get_device(device_id)
    if not device or device.ownerUserId != user_id:
        return False
    device.ownerUserId = ""
    await device.save()
    return True
```

- [ ] **Step 2: Add API endpoints to devices.py**

Add these two routes to `backend/app/api/v1/devices.py` (after the existing `register_device` route):

```python
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

@router.delete("/{device_id}")
async def deregister_device_route(
    device_id: str,
    user_id: str = Depends(get_current_user)
) -> Any:
    from app.repositories.device_repo import deregister_device
    success = await deregister_device(device_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
    return create_success_response(data={"deviceId": device_id}, message="기기 등록 해제 완료")
```

- [ ] **Step 3: Verify server starts without error**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Expected: no import errors, server starts.

- [ ] **Step 4: Commit**

```bash
git add backend/app/repositories/device_repo.py backend/app/api/v1/devices.py
git commit -m "feat: add user device list and deregister endpoints"
```

---

## Task 2: Backend — Add speed + roadType to Device model and TelemetryPayload

**Files:**
- Modify: `backend/app/repositories/models.py`
- Modify: `backend/app/schemas/mqtt_payloads.py`
- Modify: `backend/app/repositories/device_repo.py`
- Modify: `backend/app/workers/ingestion_worker.py`

- [ ] **Step 1: Extend Device model**

In `backend/app/repositories/models.py`, add two fields to the `Device` class after `bleConnected`:

```python
class Device(Document):
    deviceId: Indexed(str, unique=True)
    deviceType: str
    ownerUserId: str
    fwVersion: str

    currentState: DeviceState = DeviceState.IDLE
    lastSeenAt: Optional[datetime] = None
    helmetWorn: bool = False
    bleConnected: bool = False
    speedKph: float = 0.0            # ← add
    currentRoadType: str = "unknown" # ← add
    currentPolicyVersion: int = 1
    lastLocation: Optional[Location] = None

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "devices"
```

- [ ] **Step 2: Add speedKph to TelemetryPayload**

In `backend/app/schemas/mqtt_payloads.py`, add `speedKph` to `TelemetryPayload`:

```python
class TelemetryPayload(BaseModel):
    schemaVersion: int = 1
    deviceId: str
    timestamp: datetime
    seq: int
    rideId: str
    helmet: Optional[HelmetData] = None
    motion: Optional[MotionData] = None
    vision: Optional[VisionData] = None
    health: Optional[HealthData] = None
    speedKph: Optional[float] = None  # ← add
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
```

- [ ] **Step 3: Update update_device_status to accept speed + roadType**

In `backend/app/repositories/device_repo.py`, update the function signature and body:

```python
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
```

- [ ] **Step 4: Update ingestion_worker to pass speed + roadType**

In `backend/app/workers/ingestion_worker.py`, update `process_telemetry`:

```python
async def process_telemetry(data: TelemetryPayload):
    helmet_worn = data.helmet.worn if data.helmet else False
    ble_connected = data.health.bleConnected if data.health else False
    speed_kph = data.speedKph or 0.0
    road_type = data.vision.surfaceClass if data.vision else "unknown"

    from app.repositories.device_repo import get_device
    device = await get_device(data.deviceId)
    if not device:
        print(f"[Telemetry Dropped] Unknown device: {data.deviceId}")
    else:
        await update_device_status(
            device_id=data.deviceId,
            state=device.currentState,
            helmet_worn=helmet_worn,
            ble_connected=ble_connected,
            event_timestamp=data.timestamp,
            lat=data.latitude or 0.0,
            lng=data.longitude or 0.0,
            speed_kph=speed_kph,
            road_type=road_type,
        )

    from app.services.policy_engine import evaluate_telemetry_policy
    await evaluate_telemetry_policy(data)
```

- [ ] **Step 5: Verify server starts**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/models.py backend/app/schemas/mqtt_payloads.py \
        backend/app/repositories/device_repo.py backend/app/workers/ingestion_worker.py
git commit -m "feat: add speedKph and currentRoadType to device telemetry pipeline"
```

---

## Task 3: Backend — WebSocket connection manager

**Files:**
- Create: `backend/app/services/ws_manager.py`

- [ ] **Step 1: Create ws_manager.py**

```python
# backend/app/services/ws_manager.py
from collections import defaultdict
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[device_id].add(websocket)

    def disconnect(self, device_id: str, websocket: WebSocket) -> None:
        self._connections[device_id].discard(websocket)

    async def broadcast(self, device_id: str, message: dict) -> None:
        dead: Set[WebSocket] = set()
        for ws in list(self._connections.get(device_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections[device_id] -= dead


ws_manager = ConnectionManager()
```

- [ ] **Step 2: Verify import works**

```bash
cd backend
python -c "from app.services.ws_manager import ws_manager; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/ws_manager.py
git commit -m "feat: add WebSocket connection manager"
```

---

## Task 4: Backend — WebSocket endpoint + router wiring

**Files:**
- Create: `backend/app/api/v1/ws.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 1: Create WebSocket router**

```python
# backend/app/api/v1/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/device/{device_id}")
async def device_telemetry_ws(device_id: str, websocket: WebSocket) -> None:
    """
    Mobile clients connect here to receive live telemetry for a device.
    The server pushes messages; client sends pings to keep connection alive.
    """
    await ws_manager.connect(device_id, websocket)
    try:
        while True:
            # Drain any incoming frames (client pings); we don't process them.
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(device_id, websocket)
    except Exception:
        ws_manager.disconnect(device_id, websocket)
```

- [ ] **Step 2: Register the WS router**

In `backend/app/api/router.py`, add the ws import and include it:

```python
from fastapi import APIRouter

from app.api.v1 import auth, devices, admin, users, events, policies, emergencies, ws

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(events.router, prefix="/events", tags=["Events"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(policies.router, prefix="/policies", tags=["Policies"])
api_router.include_router(emergencies.router, prefix="/emergencies", tags=["Emergencies"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
```

- [ ] **Step 3: Verify WebSocket route is visible**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# open browser at http://localhost:8000/docs — scroll to WebSocket section
```

Expected: `/v1/ws/device/{device_id}` listed under "WebSocket" tags.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/ws.py backend/app/api/router.py
git commit -m "feat: add WebSocket endpoint /v1/ws/device/{device_id}"
```

---

## Task 5: Backend — Broadcast telemetry and events to WebSocket clients

**Files:**
- Modify: `backend/app/workers/ingestion_worker.py`

- [ ] **Step 1: Add WS broadcast calls to process_telemetry and process_event**

Replace the contents of `backend/app/workers/ingestion_worker.py` with:

```python
import traceback
from typing import Dict, Any
from pydantic import ValidationError

from app.schemas.mqtt_payloads import TelemetryPayload, EventPayload
from app.repositories.event_repo import save_event_idempotent
from app.repositories.device_repo import update_device_status
from app.domain.states import DeviceState


async def handle_mqtt_message(topic: str, payload: Dict[str, Any]) -> None:
    try:
        if topic.endswith("/telemetry"):
            data = TelemetryPayload(**payload)
            await process_telemetry(data)
        elif topic.endswith("/event"):
            data = EventPayload(**payload)
            await process_event(data)
    except ValidationError as e:
        print(f"Schema Validation Error on topic {topic}: {e}")
    except Exception as e:
        print(f"Error handling message on {topic}: {e}")
        traceback.print_exc()


async def process_telemetry(data: TelemetryPayload) -> None:
    helmet_worn = data.helmet.worn if data.helmet else False
    ble_connected = data.health.bleConnected if data.health else False
    speed_kph = data.speedKph or 0.0
    road_type = data.vision.surfaceClass if data.vision else "unknown"

    from app.repositories.device_repo import get_device
    device = await get_device(data.deviceId)
    if not device:
        print(f"[Telemetry Dropped] Unknown device: {data.deviceId}")
    else:
        await update_device_status(
            device_id=data.deviceId,
            state=device.currentState,
            helmet_worn=helmet_worn,
            ble_connected=ble_connected,
            event_timestamp=data.timestamp,
            lat=data.latitude or 0.0,
            lng=data.longitude or 0.0,
            speed_kph=speed_kph,
            road_type=road_type,
        )

    # Broadcast to any mobile clients watching this device
    from app.services.ws_manager import ws_manager
    await ws_manager.broadcast(data.deviceId, {
        "type": "telemetry_update",
        "deviceId": data.deviceId,
        "speedKph": speed_kph,
        "roadType": road_type,
        "helmetWorn": helmet_worn,
        "bleConnected": ble_connected,
        "timestamp": data.timestamp.isoformat(),
    })

    from app.services.policy_engine import evaluate_telemetry_policy
    await evaluate_telemetry_policy(data)


async def process_event(data: EventPayload) -> None:
    event_doc = await save_event_idempotent(payload=data, anomaly=False)

    if event_doc:
        print(f"[Event Ingested] {data.deviceId} -> {data.eventType} (seq {data.seq})")

        # Broadcast event notification to mobile clients
        from app.services.ws_manager import ws_manager
        await ws_manager.broadcast(data.deviceId, {
            "type": "event_notification",
            "deviceId": data.deviceId,
            "eventType": data.eventType,
            "severity": data.severity,
            "reason": data.reason,
            "confidence": data.confidence,
            "timestamp": data.timestamp.isoformat(),
        })

        from app.services.policy_engine import evaluate_event_policy
        await evaluate_event_policy(data)
    else:
        print(f"[Duplicate/Ignored] {data.deviceId} seq {data.seq}")
```

- [ ] **Step 2: Verify server starts**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add backend/app/workers/ingestion_worker.py
git commit -m "feat: broadcast MQTT telemetry and events to WebSocket clients"
```

---

## Task 6: Mobile — AuthContext + token storage + axiosInstance update

**Files:**
- Create: `frontend-mobile/src/context/AuthContext.tsx`
- Modify: `frontend-mobile/src/api/axiosInstance.ts`

- [ ] **Step 1: Install AsyncStorage**

```bash
cd frontend-mobile
npx expo install @react-native-async-storage/async-storage
```

Expected: package added to package.json.

- [ ] **Step 2: Add module-level token setter to axiosInstance.ts**

Replace `frontend-mobile/src/api/axiosInstance.ts` with:

```typescript
import axios from 'axios';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

// Module-level token — set by AuthContext on login/logout/restore
let _authToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
  _authToken = token;
};

axiosInstance.interceptors.request.use(
  (config) => {
    if (_authToken) {
      config.headers.Authorization = `Bearer ${_authToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('Mobile API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  },
);
```

- [ ] **Step 3: Create AuthContext.tsx**

```typescript
// frontend-mobile/src/context/AuthContext.tsx
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { axiosInstance, setAuthToken } from '../api/axiosInstance';
import type { BaseResponse } from '../api/userApi';

const TOKEN_KEY = 'auth_token';

interface AuthContextValue {
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore token from storage on app start
  useEffect(() => {
    AsyncStorage.getItem(TOKEN_KEY).then((stored) => {
      if (stored) {
        setToken(stored);
        setAuthToken(stored);
      }
      setIsLoading(false);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res: BaseResponse<{ accessToken: string; role: string }> =
      await axiosInstance.post('/auth/login', { email, password });
    const t = res.data.accessToken;
    await AsyncStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setAuthToken(t);
  }, []);

  const logout = useCallback(async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setAuthToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
```

- [ ] **Step 4: Commit**

```bash
cd frontend-mobile
git add src/context/AuthContext.tsx src/api/axiosInstance.ts package.json package-lock.json
git commit -m "feat: add AuthContext with AsyncStorage token persistence"
```

---

## Task 7: Mobile — Login screen

**Files:**
- Create: `frontend-mobile/app/login.tsx`

- [ ] **Step 1: Create login.tsx**

```typescript
// frontend-mobile/app/login.tsx
import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { ShieldAlert } from 'lucide-react-native';
import { useAuth } from '../src/context/AuthContext';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert('입력 오류', '이메일과 비밀번호를 입력해 주세요.');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/(tabs)');
    } catch {
      Alert.alert('로그인 실패', '이메일 또는 비밀번호를 확인해 주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.content}>
        <View style={styles.iconWrap}>
          <ShieldAlert size={56} color="#3b82f6" />
        </View>
        <Text style={styles.title}>Safe Mobility</Text>
        <Text style={styles.subtitle}>로그인하여 안전한 주행을 시작하세요</Text>

        <TextInput
          style={styles.input}
          placeholder="이메일"
          placeholderTextColor="#64748b"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        <TextInput
          style={styles.input}
          placeholder="비밀번호"
          placeholderTextColor="#64748b"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.buttonText}>로그인</Text>}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  content: { flex: 1, padding: 28, justifyContent: 'center', gap: 16 },
  iconWrap: {
    width: 96, height: 96, borderRadius: 48,
    backgroundColor: 'rgba(59,130,246,0.12)',
    alignItems: 'center', justifyContent: 'center',
    alignSelf: 'center', marginBottom: 8,
  },
  title: { fontSize: 28, fontWeight: '800', color: '#f8fafc', textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#94a3b8', textAlign: 'center', marginBottom: 16 },
  input: {
    backgroundColor: '#1e293b', borderRadius: 12,
    padding: 16, color: '#f8fafc', fontSize: 16,
    borderWidth: 1, borderColor: '#334155',
  },
  button: {
    backgroundColor: '#3b82f6', borderRadius: 12,
    padding: 16, alignItems: 'center', marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend-mobile/app/login.tsx
git commit -m "feat: add login screen"
```

---

## Task 8: Mobile — Auth guard (root layout + app entry redirect)

**Files:**
- Modify: `frontend-mobile/app/_layout.tsx`
- Modify: `frontend-mobile/app/index.tsx`

- [ ] **Step 1: Wrap root layout with AuthProvider**

Replace `frontend-mobile/app/_layout.tsx` with:

```typescript
import { Stack } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider } from '../src/context/AuthContext';
import { EmergencyProvider } from '../src/context/EmergencyContext';
import { GlobalEmergencyOverlay } from '../src/components/GlobalEmergencyOverlay';

const queryClient = new QueryClient();

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <EmergencyProvider>
          <StatusBar style="light" />
          <Stack>
            <Stack.Screen name="index" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="riding/[deviceId]" options={{ headerShown: false }} />
            <Stack.Screen name="pair" options={{ presentation: 'modal', title: 'Pair Device' }} />
          </Stack>
          <GlobalEmergencyOverlay />
        </EmergencyProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Replace app/index.tsx with auth redirect**

Replace `frontend-mobile/app/index.tsx` with:

```typescript
import { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../src/context/AuthContext';

export default function RootIndex() {
  const { token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (token) {
      router.replace('/(tabs)');
    } else {
      router.replace('/login');
    }
  }, [token, isLoading, router]);

  return (
    <View style={{ flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' }}>
      <ActivityIndicator size="large" color="#3b82f6" />
    </View>
  );
}
```

- [ ] **Step 3: Test auth flow manually**

Run Expo: `npm run start` in `frontend-mobile`. Verify:
- App shows loading spinner briefly
- Without stored token → redirects to Login screen
- After entering any email + password "admin" → redirects to tabs

- [ ] **Step 4: Commit**

```bash
git add frontend-mobile/app/_layout.tsx frontend-mobile/app/index.tsx
git commit -m "feat: add auth guard — unauthenticated users redirected to login"
```

---

## Task 9: Mobile — Device management screen (register, list, deregister)

**Files:**
- Modify: `frontend-mobile/src/api/userApi.ts`
- Modify: `frontend-mobile/src/hooks/useUserQueries.ts`
- Modify: `frontend-mobile/src/hooks/useUserMutations.ts`
- Create: `frontend-mobile/app/(tabs)/devices.tsx`
- Modify: `frontend-mobile/app/(tabs)/_layout.tsx`

- [ ] **Step 1: Add device API methods to userApi.ts**

Add the following interface and methods inside `frontend-mobile/src/api/userApi.ts`:

```typescript
export interface MyDevice {
  deviceId: string;
  deviceType: string;
  currentState: string;
  bleConnected: boolean;
  helmetWorn: boolean;
  lastSeenAt: string | null;
}

// Add to userApi object:
getMyDevices: () =>
  axiosInstance.get<any, BaseResponse<MyDevice[]>>('/devices'),

registerDevice: (deviceId: string, deviceType: string) =>
  axiosInstance.post<any, BaseResponse<{ deviceId: string }>>('/devices/pair', {
    deviceId,
    deviceType,
  }),

deregisterDevice: (deviceId: string) =>
  axiosInstance.delete<any, BaseResponse<{ deviceId: string }>>(`/devices/${deviceId}`),
```

- [ ] **Step 2: Add useMyDevices query to useUserQueries.ts**

Append to `frontend-mobile/src/hooks/useUserQueries.ts`:

```typescript
import type { MyDevice } from '../api/userApi';

export const useMyDevices = () => {
  return useQuery({
    queryKey: ['myDevices'],
    queryFn: async () => {
      const res = await userApi.getMyDevices();
      return res.data as MyDevice[];
    },
    staleTime: 30_000,
  });
};
```

- [ ] **Step 3: Add device mutations to useUserMutations.ts**

Append to `frontend-mobile/src/hooks/useUserMutations.ts`:

```typescript
export const useRegisterDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deviceId, deviceType }: { deviceId: string; deviceType: string }) =>
      userApi.registerDevice(deviceId, deviceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myDevices'] });
      Alert.alert('등록 완료', '디바이스가 등록되었습니다.');
    },
    onError: (error: ApiError) => {
      Alert.alert('오류', error.response?.data?.message ?? '디바이스 등록에 실패했습니다.');
    },
  });
};

export const useDeregisterDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) => userApi.deregisterDevice(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myDevices'] });
      Alert.alert('해제 완료', '디바이스 등록이 해제되었습니다.');
    },
    onError: (error: ApiError) => {
      Alert.alert('오류', error.response?.data?.message ?? '디바이스 해제에 실패했습니다.');
    },
  });
};
```

- [ ] **Step 4: Create devices.tsx tab screen**

```typescript
// frontend-mobile/app/(tabs)/devices.tsx
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Alert, TextInput, Modal,
} from 'react-native';
import { Bluetooth, Plus, Trash2, Wifi, WifiOff } from 'lucide-react-native';
import { useMyDevices } from '../../src/hooks/useUserQueries';
import { useRegisterDevice, useDeregisterDevice } from '../../src/hooks/useUserMutations';
import type { MyDevice } from '../../src/api/userApi';

const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: '#10b981',
  RUNNING_LIMITED: '#f59e0b',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: '#ef4444',
  IDLE: '#64748b',
  READY: '#64748b',
};

export default function DevicesScreen() {
  const { data: devices, isLoading, refetch } = useMyDevices();
  const registerMutation = useRegisterDevice();
  const deregisterMutation = useDeregisterDevice();

  const [modalVisible, setModalVisible] = useState(false);
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceType, setNewDeviceType] = useState('scooter');

  const handleRegister = () => {
    if (!newDeviceId.trim()) {
      Alert.alert('입력 오류', '디바이스 ID를 입력해 주세요.');
      return;
    }
    registerMutation.mutate(
      { deviceId: newDeviceId.trim(), deviceType: newDeviceType },
      {
        onSuccess: () => {
          setModalVisible(false);
          setNewDeviceId('');
        },
      },
    );
  };

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

  const renderDevice = ({ item }: { item: MyDevice }) => (
    <View style={styles.deviceCard}>
      <View style={styles.deviceLeft}>
        <View style={[styles.stateIndicator, { backgroundColor: STATE_COLORS[item.currentState] ?? '#64748b' }]} />
        <View>
          <Text style={styles.deviceId}>{item.deviceId}</Text>
          <Text style={styles.deviceType}>{item.deviceType}</Text>
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

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>내 디바이스</Text>
        <TouchableOpacity style={styles.addBtn} onPress={() => setModalVisible(true)}>
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

      {/* Register modal */}
      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalBox}>
            <Text style={styles.modalTitle}>디바이스 등록</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="디바이스 ID (예: pi-001)"
              placeholderTextColor="#64748b"
              value={newDeviceId}
              onChangeText={setNewDeviceId}
              autoCapitalize="none"
            />
            <View style={styles.typeRow}>
              {['scooter', 'bike'].map((t) => (
                <TouchableOpacity
                  key={t}
                  style={[styles.typeChip, newDeviceType === t && styles.typeChipActive]}
                  onPress={() => setNewDeviceType(t)}
                >
                  <Text style={[styles.typeChipText, newDeviceType === t && styles.typeChipTextActive]}>
                    {t === 'scooter' ? '킥보드' : '자전거'}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
            <TouchableOpacity
              style={[styles.button, registerMutation.isPending && styles.buttonDisabled]}
              onPress={handleRegister}
              disabled={registerMutation.isPending}
            >
              {registerMutation.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.buttonText}>등록</Text>}
            </TouchableOpacity>
            <TouchableOpacity style={styles.cancelBtn} onPress={() => setModalVisible(false)}>
              <Text style={styles.cancelText}>취소</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingTop: 60, borderBottomWidth: 1, borderBottomColor: '#1e293b',
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
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'flex-end' },
  modalBox: {
    backgroundColor: '#1e293b', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 28, gap: 16,
  },
  modalTitle: { fontSize: 20, fontWeight: '700', color: '#f8fafc' },
  modalInput: {
    backgroundColor: '#0f172a', borderRadius: 12, padding: 14,
    color: '#f8fafc', fontSize: 15, borderWidth: 1, borderColor: '#334155',
  },
  typeRow: { flexDirection: 'row', gap: 12 },
  typeChip: {
    flex: 1, padding: 12, borderRadius: 10, borderWidth: 1,
    borderColor: '#334155', alignItems: 'center',
  },
  typeChipActive: { borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)' },
  typeChipText: { color: '#94a3b8', fontWeight: '600' },
  typeChipTextActive: { color: '#3b82f6' },
  button: { backgroundColor: '#3b82f6', borderRadius: 12, padding: 16, alignItems: 'center' },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  cancelBtn: { alignItems: 'center', padding: 12 },
  cancelText: { color: '#64748b', fontSize: 15 },
});
```

- [ ] **Step 5: Add Devices tab to _layout.tsx**

In `frontend-mobile/app/(tabs)/_layout.tsx`, add the Devices tab (import `Cpu` from lucide-react-native):

```typescript
import { Tabs } from 'expo-router';
import { Home, List, User, Cpu } from 'lucide-react-native';
import { useEmergencyPolling } from '../../src/hooks/useEmergencyPolling';

export default function TabLayout() {
  useEmergencyPolling();

  return (
    <Tabs screenOptions={{
      tabBarActiveTintColor: '#3b82f6',
      tabBarInactiveTintColor: '#64748b',
      tabBarStyle: { backgroundColor: '#0f172a', borderTopColor: '#1e293b' },
      headerShown: false,
    }}>
      <Tabs.Screen
        name="index"
        options={{ title: '홈', tabBarIcon: ({ color }) => <Home color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="devices"
        options={{ title: '디바이스', tabBarIcon: ({ color }) => <Cpu color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: '주행기록', tabBarIcon: ({ color }) => <List color={color} size={24} /> }}
      />
      <Tabs.Screen
        name="profile"
        options={{ title: '프로필', tabBarIcon: ({ color }) => <User color={color} size={24} /> }}
      />
      <Tabs.Screen name="dashboard" options={{ href: null }} />
    </Tabs>
  );
}
```

Note: `dashboard` is hidden from tab bar (`href: null`) since it was a prototype screen.

- [ ] **Step 6: Commit**

```bash
git add frontend-mobile/src/api/userApi.ts \
        frontend-mobile/src/hooks/useUserQueries.ts \
        frontend-mobile/src/hooks/useUserMutations.ts \
        frontend-mobile/app/(tabs)/devices.tsx \
        frontend-mobile/app/(tabs)/_layout.tsx
git commit -m "feat: add device management screen with register and deregister"
```

---

## Task 10: Mobile — Riding WebSocket hook

**Files:**
- Create: `frontend-mobile/src/hooks/useRidingWebSocket.ts`

- [ ] **Step 1: Create the hook**

```typescript
// frontend-mobile/src/hooks/useRidingWebSocket.ts
import { useEffect, useRef, useState } from 'react';

export interface RidingData {
  speedKph: number;
  roadType: 'road' | 'sidewalk' | 'unknown';
  helmetWorn: boolean;
  bleConnected: boolean;
}

export interface RidingEvent {
  eventType: string;
  severity: string;
  reason: string;
  timestamp: string;
}

const INITIAL_DATA: RidingData = {
  speedKph: 0,
  roadType: 'unknown',
  helmetWorn: false,
  bleConnected: false,
};

const MAX_EVENTS = 20;

export const useRidingWebSocket = (deviceId: string) => {
  const [data, setData] = useState<RidingData>(INITIAL_DATA);
  const [events, setEvents] = useState<RidingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!deviceId) return;

    const WS_BASE =
      process.env.EXPO_PUBLIC_WS_URL ?? 'ws://52.79.242.44:8000/v1/ws';
    const url = `${WS_BASE}/device/${deviceId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'telemetry_update') {
          setData({
            speedKph: msg.speedKph ?? 0,
            roadType: msg.roadType ?? 'unknown',
            helmetWorn: msg.helmetWorn ?? false,
            bleConnected: msg.bleConnected ?? false,
          });
        } else if (msg.type === 'event_notification') {
          setEvents((prev) =>
            [
              {
                eventType: msg.eventType,
                severity: msg.severity,
                reason: msg.reason,
                timestamp: msg.timestamp,
              },
              ...prev,
            ].slice(0, MAX_EVENTS),
          );
        }
      } catch {
        // malformed message — ignore
      }
    };

    // Send periodic ping to keep connection alive (every 20s)
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 20_000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [deviceId]);

  return { data, events, connected };
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend-mobile/src/hooks/useRidingWebSocket.ts
git commit -m "feat: add WebSocket hook for live riding data"
```

---

## Task 11: Mobile — Riding screen

**Files:**
- Create: `frontend-mobile/app/riding/[deviceId].tsx`

- [ ] **Step 1: Create the riding screen directory and file**

```typescript
// frontend-mobile/app/riding/[deviceId].tsx
import React from 'react';
import {
  View, Text, StyleSheet, SafeAreaView, ScrollView,
  TouchableOpacity, FlatList,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Shield, MapPin, Wifi, WifiOff, ChevronLeft, AlertTriangle } from 'lucide-react-native';
import { useRidingWebSocket } from '../../src/hooks/useRidingWebSocket';
import type { RidingEvent } from '../../src/hooks/useRidingWebSocket';

const ROAD_TYPE_LABEL: Record<string, string> = {
  road: '도로',
  sidewalk: '인도',
  unknown: '감지 중...',
};

const ROAD_TYPE_COLOR: Record<string, string> = {
  road: '#10b981',
  sidewalk: '#f59e0b',
  unknown: '#64748b',
};

const SEVERITY_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#3b82f6',
};

export default function RidingScreen() {
  const { deviceId } = useLocalSearchParams<{ deviceId: string }>();
  const router = useRouter();
  const { data, events, connected } = useRidingWebSocket(deviceId ?? '');

  const roadColor = ROAD_TYPE_COLOR[data.roadType] ?? '#64748b';

  const renderEvent = ({ item }: { item: RidingEvent }) => (
    <View style={[styles.eventItem, { borderLeftColor: SEVERITY_COLOR[item.severity] ?? '#64748b' }]}>
      <View style={styles.eventHeader}>
        <Text style={styles.eventType}>{item.eventType}</Text>
        <Text style={[styles.eventSeverity, { color: SEVERITY_COLOR[item.severity] ?? '#64748b' }]}>
          {item.severity.toUpperCase()}
        </Text>
      </View>
      <Text style={styles.eventReason}>{item.reason}</Text>
      <Text style={styles.eventTime}>
        {new Date(item.timestamp).toLocaleTimeString('ko-KR')}
      </Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      {/* Top bar */}
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <ChevronLeft size={28} color="#f8fafc" />
        </TouchableOpacity>
        <Text style={styles.deviceTitle} numberOfLines={1}>{deviceId}</Text>
        <View style={styles.connBadge}>
          {connected
            ? <Wifi size={14} color="#10b981" />
            : <WifiOff size={14} color="#ef4444" />}
          <Text style={[styles.connText, { color: connected ? '#10b981' : '#ef4444' }]}>
            {connected ? 'Live' : '연결 끊김'}
          </Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Speed display */}
        <View style={styles.speedCard}>
          <Text style={styles.speedLabel}>현재 속력</Text>
          <Text style={styles.speedValue}>{data.speedKph.toFixed(1)}</Text>
          <Text style={styles.speedUnit}>km/h</Text>
          {data.roadType === 'sidewalk' && (
            <View style={styles.warningBanner}>
              <AlertTriangle size={14} color="#f59e0b" />
              <Text style={styles.warningText}>인도 감지 — 속도 제한 적용 중</Text>
            </View>
          )}
        </View>

        {/* Road type */}
        <View style={[styles.statusCard, { borderLeftColor: roadColor }]}>
          <MapPin size={22} color={roadColor} />
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>도로 유형</Text>
            <Text style={[styles.statusValue, { color: roadColor }]}>
              {ROAD_TYPE_LABEL[data.roadType] ?? '알 수 없음'}
            </Text>
          </View>
        </View>

        {/* Helmet */}
        <View style={[styles.statusCard, {
          borderLeftColor: data.helmetWorn ? '#10b981' : '#ef4444',
        }]}>
          <Shield size={22} color={data.helmetWorn ? '#10b981' : '#ef4444'} />
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>헬멧 상태</Text>
            <Text style={[styles.statusValue, { color: data.helmetWorn ? '#10b981' : '#ef4444' }]}>
              {data.helmetWorn ? '착용 중' : '미착용 ⚠️'}
            </Text>
          </View>
        </View>

        {/* BLE helmet connection */}
        <View style={[styles.statusCard, {
          borderLeftColor: data.bleConnected ? '#10b981' : '#64748b',
        }]}>
          {data.bleConnected
            ? <Wifi size={22} color="#10b981" />
            : <WifiOff size={22} color="#64748b" />}
          <View style={styles.statusCardContent}>
            <Text style={styles.statusLabel}>헬멧 BLE 연결</Text>
            <Text style={[styles.statusValue, { color: data.bleConnected ? '#10b981' : '#64748b' }]}>
              {data.bleConnected ? '연결됨' : '연결 안 됨'}
            </Text>
          </View>
        </View>

        {/* Events */}
        <Text style={styles.sectionTitle}>주행 이벤트</Text>
        {events.length === 0 ? (
          <View style={styles.noEvents}>
            <Text style={styles.noEventsText}>이벤트 없음</Text>
          </View>
        ) : (
          <FlatList
            data={events}
            keyExtractor={(_, i) => String(i)}
            renderItem={renderEvent}
            scrollEnabled={false}
            contentContainerStyle={{ gap: 8 }}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  topBar: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16,
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1e293b',
  },
  backBtn: { marginRight: 8 },
  deviceTitle: { flex: 1, fontSize: 18, fontWeight: '700', color: '#f8fafc' },
  connBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, marginLeft: 8 },
  connText: { fontSize: 12, fontWeight: '600' },
  scroll: { padding: 16, gap: 12, paddingBottom: 40 },
  speedCard: {
    backgroundColor: '#1e293b', borderRadius: 20, padding: 28,
    alignItems: 'center', borderWidth: 1, borderColor: '#334155',
  },
  speedLabel: { fontSize: 14, color: '#94a3b8', marginBottom: 4 },
  speedValue: { fontSize: 72, fontWeight: '800', color: '#f8fafc', lineHeight: 80 },
  speedUnit: { fontSize: 18, color: '#64748b', marginTop: 4 },
  warningBanner: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: 'rgba(245,158,11,0.1)', borderRadius: 8,
    paddingHorizontal: 12, paddingVertical: 6, marginTop: 12,
  },
  warningText: { fontSize: 13, color: '#f59e0b', fontWeight: '500' },
  statusCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    flexDirection: 'row', alignItems: 'center', gap: 14,
    borderLeftWidth: 4, borderColor: '#334155', borderWidth: 1,
  },
  statusCardContent: { flex: 1 },
  statusLabel: { fontSize: 12, color: '#64748b', marginBottom: 2 },
  statusValue: { fontSize: 18, fontWeight: '700' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#94a3b8', marginTop: 8 },
  noEvents: { backgroundColor: '#1e293b', borderRadius: 12, padding: 24, alignItems: 'center' },
  noEventsText: { color: '#64748b', fontSize: 14 },
  eventItem: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 14,
    borderLeftWidth: 3, borderColor: '#334155', borderWidth: 1,
  },
  eventHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  eventType: { fontSize: 14, fontWeight: '700', color: '#f8fafc' },
  eventSeverity: { fontSize: 11, fontWeight: '700' },
  eventReason: { fontSize: 13, color: '#94a3b8', marginBottom: 4 },
  eventTime: { fontSize: 11, color: '#64748b' },
});
```

- [ ] **Step 2: Commit**

```bash
git add frontend-mobile/app/riding
git commit -m "feat: add live riding screen with speed, road type, and events"
```

---

## Task 12: Mobile — Home tab update (device selector → Start Ride)

**Files:**
- Modify: `frontend-mobile/app/(tabs)/index.tsx`

- [ ] **Step 1: Replace home screen with device selector**

Replace `frontend-mobile/app/(tabs)/index.tsx` with:

```typescript
import React from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, SafeAreaView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Play, Cpu, Shield, WifiOff, Wifi, LogOut } from 'lucide-react-native';
import { useMyDevices } from '../../src/hooks/useUserQueries';
import { useAuth } from '../../src/context/AuthContext';
import type { MyDevice } from '../../src/api/userApi';
import { SafeButton } from '../../src/components/SafeButton';
import { useEmergency } from '../../src/context/EmergencyContext';

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

export default function HomeScreen() {
  const router = useRouter();
  const { logout } = useAuth();
  const { triggerSOS } = useEmergency();
  const { data: devices, isLoading, refetch } = useMyDevices();

  const renderDevice = ({ item }: { item: MyDevice }) => {
    const stateColor = STATE_COLORS[item.currentState] ?? '#64748b';
    return (
      <View style={styles.deviceCard}>
        <View style={styles.deviceInfo}>
          <Cpu size={20} color={stateColor} />
          <View style={{ flex: 1 }}>
            <Text style={styles.deviceId}>{item.deviceId}</Text>
            <Text style={[styles.deviceState, { color: stateColor }]}>
              {STATE_LABELS[item.currentState] ?? item.currentState}
            </Text>
            <View style={styles.helmetRow}>
              <Shield size={12} color={item.helmetWorn ? '#10b981' : '#64748b'} />
              <Text style={[styles.helmetText, { color: item.helmetWorn ? '#10b981' : '#64748b' }]}>
                {item.helmetWorn ? '헬멧 착용' : '헬멧 미착용'}
              </Text>
              {item.bleConnected
                ? <Wifi size={12} color="#10b981" />
                : <WifiOff size={12} color="#64748b" />}
            </View>
          </View>
        </View>
        <TouchableOpacity
          style={styles.startBtn}
          onPress={() => router.push(`/riding/${item.deviceId}`)}
        >
          <Play size={16} color="#fff" />
          <Text style={styles.startBtnText}>주행 시작</Text>
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Safe Mobility</Text>
          <Text style={styles.subtitle}>안전한 주행을 시작하세요</Text>
        </View>
        <TouchableOpacity onPress={logout} style={styles.logoutBtn}>
          <LogOut size={20} color="#64748b" />
        </TouchableOpacity>
      </View>

      {isLoading ? (
        <ActivityIndicator style={{ marginTop: 40 }} size="large" color="#3b82f6" />
      ) : (
        <FlatList
          data={devices ?? []}
          keyExtractor={(item) => item.deviceId}
          renderItem={renderDevice}
          contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 120 }}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Cpu size={48} color="#334155" />
              <Text style={styles.emptyText}>등록된 디바이스가 없습니다</Text>
              <Text style={styles.emptySubText}>디바이스 탭에서 라즈베리파이를 등록하세요</Text>
            </View>
          }
          onRefresh={refetch}
          refreshing={isLoading}
        />
      )}

      {/* SOS button fixed at bottom */}
      <View style={styles.sosContainer}>
        <Text style={styles.sosWarning}>긴급 상황에서만 사용하세요</Text>
        <SafeButton
          title="긴급 SOS"
          variant="danger"
          onPress={() => triggerSOS({ reason: '사용자 SOS (모바일 앱)' })}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingTop: 24,
  },
  greeting: { fontSize: 22, fontWeight: '800', color: '#f8fafc' },
  subtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  logoutBtn: { padding: 8 },
  deviceCard: {
    backgroundColor: '#1e293b', borderRadius: 16, padding: 16,
    borderWidth: 1, borderColor: '#334155', gap: 12,
  },
  deviceInfo: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  deviceId: { fontSize: 16, fontWeight: '700', color: '#f8fafc', marginBottom: 2 },
  deviceState: { fontSize: 13, fontWeight: '600', marginBottom: 4 },
  helmetRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  helmetText: { fontSize: 12, fontWeight: '500' },
  startBtn: {
    backgroundColor: '#3b82f6', borderRadius: 10, padding: 12,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
  },
  startBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  empty: { alignItems: 'center', paddingTop: 80, gap: 12 },
  emptyText: { color: '#94a3b8', fontSize: 16, fontWeight: '600' },
  emptySubText: { color: '#64748b', fontSize: 13, textAlign: 'center' },
  sosContainer: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    padding: 20, backgroundColor: '#0f172a',
    borderTopWidth: 1, borderTopColor: '#1e293b',
  },
  sosWarning: { textAlign: 'center', color: '#64748b', fontSize: 12, marginBottom: 8 },
});
```

- [ ] **Step 2: Run the app and verify the full flow**

```bash
cd frontend-mobile
npm run start
```

Verify the following flow end-to-end:
1. App opens → loading spinner → redirects to Login screen
2. Enter any email + password `admin` → logged in → home tab shows device list
3. Devices tab → register a device (e.g., `pi-001`, scooter) → appears in list
4. Home tab → device shows → tap "주행 시작" → riding screen opens
5. Riding screen shows speed/road type/helmet status (initially 0/unknown/false until MQTT data arrives)
6. Devices tab → long-press or trash icon → deregister confirmation → device removed
7. Home screen logout button → returns to login screen

- [ ] **Step 3: Commit**

```bash
git add frontend-mobile/app/(tabs)/index.tsx
git commit -m "feat: update home screen with device list and Start Ride navigation"
```

---

## Summary of changes

| Layer | Tasks | Key new capabilities |
|---|---|---|
| Backend | 1–5 | User device list/deregister, speed+roadType fields, WS endpoint, MQTT→WS bridge |
| Mobile | 6–12 | Login + auth guard, device management, live riding screen via WebSocket |

**New routes (backend):**
- `GET /v1/devices` — list devices owned by authenticated user
- `DELETE /v1/devices/{id}` — deregister device
- `WS /v1/ws/device/{id}` — live telemetry stream

**New screens (mobile):**
- `/login` — login form
- `/(tabs)/devices` — device management
- `/riding/[deviceId]` — live riding dashboard
