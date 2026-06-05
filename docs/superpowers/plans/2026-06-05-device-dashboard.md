# Device Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 메인 대시보드에 디바이스 목록 테이블을 추가하고, 행 클릭 시 디바이스 상세 정보와 최근 이벤트를 모달로 표시한다.

**Architecture:** 백엔드에 `/admin/devices` 목록 조회 endpoint와 기존 `/admin/events`에 `deviceId` 필터를 추가한다. 프론트엔드는 `DeviceListTable` + `DeviceDetailModal` 두 컴포넌트로 분리하고 `Dashboard.tsx`에서 조립한다.

**Tech Stack:** FastAPI + Beanie/Motor (backend), React 19 + TypeScript + TanStack Query v5 + inline styles/CSS variables (frontend)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `backend/app/schemas/admin_dto.py` | `DeviceListItemDto`, `LocationDto` 스키마 추가 |
| Modify | `backend/app/repositories/admin_repo.py` | `get_all_devices()` 추가, `get_paginated_events()` deviceId 필터 추가 |
| Modify | `backend/app/services/admin_service.py` | `get_device_list()` 추가, `get_event_logs()` device_id 인자 추가 |
| Modify | `backend/app/api/v1/admin.py` | `GET /devices` 라우트 추가, `GET /events` deviceId 파라미터 추가 |
| Modify | `frontend-web/src/api/adminApi.ts` | `DeviceListItem` 타입, `getDeviceList()`, `getEvents()` deviceId 추가 |
| Modify | `frontend-web/src/hooks/queries/useAdminQueries.ts` | `useDeviceList()`, `useDeviceEvents()` 추가 |
| Create | `frontend-web/src/components/devices/DeviceListTable.tsx` | 디바이스 목록 테이블 컴포넌트 |
| Create | `frontend-web/src/components/devices/DeviceDetailModal.tsx` | 디바이스 상세 + 이벤트 모달 컴포넌트 |
| Modify | `frontend-web/src/screens/Dashboard.tsx` | DeviceListTable + DeviceDetailModal 통합 |

---

## Task 1: 백엔드 스키마 — DeviceListItemDto 추가

**Files:**
- Modify: `backend/app/schemas/admin_dto.py`

- [ ] **Step 1: admin_dto.py 열기 — 현재 내용 확인**

현재 파일 끝:
```python
class EventLogPaginatedResponse(BaseModel):
    items: List[EventLogDto]
    totalCount: int
    page: int
    size: int
```

- [ ] **Step 2: LocationDto, DeviceListItemDto 추가**

`backend/app/schemas/admin_dto.py` 파일 끝에 추가:
```python
class LocationDto(BaseModel):
    lat: float
    lng: float

class DeviceListItemDto(BaseModel):
    deviceId: str
    deviceType: str
    currentState: str
    lastSeenAt: Optional[datetime]
    helmetWorn: bool
    bleConnected: bool
    lastLocation: Optional[LocationDto]
    fwVersion: str
    currentPolicyVersion: int
```

- [ ] **Step 3: 커밋**

```bash
git add backend/app/schemas/admin_dto.py
git commit -m "feat: add DeviceListItemDto schema"
```

---

## Task 2: 백엔드 레포지토리 — 디바이스 목록 쿼리 + 이벤트 deviceId 필터

**Files:**
- Modify: `backend/app/repositories/admin_repo.py`

- [ ] **Step 1: get_all_devices() 추가**

`backend/app/repositories/admin_repo.py` 파일 끝에 추가:
```python
async def get_all_devices() -> List[Device]:
    return await Device.find().sort(-Device.lastSeenAt).to_list()
```

- [ ] **Step 2: get_paginated_events에 device_id 파라미터 추가**

기존:
```python
async def get_paginated_events(page: int, size: int, severity: Optional[str] = None) -> Tuple[List[Event], int]:
    query = Event.find()
    if severity:
        query = query.find(Event.severity == severity)
```

변경 후:
```python
async def get_paginated_events(page: int, size: int, severity: Optional[str] = None, device_id: Optional[str] = None) -> Tuple[List[Event], int]:
    query = Event.find()
    if severity:
        query = query.find(Event.severity == severity)
    if device_id:
        query = query.find(Event.deviceId == device_id)
```

- [ ] **Step 3: 커밋**

```bash
git add backend/app/repositories/admin_repo.py
git commit -m "feat: add get_all_devices and deviceId filter to events query"
```

---

## Task 3: 백엔드 서비스 — get_device_list() + get_event_logs() 업데이트

**Files:**
- Modify: `backend/app/services/admin_service.py`

- [ ] **Step 1: import DeviceListItemDto, LocationDto 추가**

기존 import:
```python
from app.schemas.admin_dto import (
    AdminStatsResponse, DeviceLocationDto, AlertsTimelineResponse,
    AlertsTimelineBucket, EnvironmentStatsResponse, EventLogPaginatedResponse, EventLogDto
)
```

변경 후:
```python
from app.schemas.admin_dto import (
    AdminStatsResponse, DeviceLocationDto, AlertsTimelineResponse,
    AlertsTimelineBucket, EnvironmentStatsResponse, EventLogPaginatedResponse, EventLogDto,
    DeviceListItemDto, LocationDto
)
```

- [ ] **Step 2: get_device_list() 함수 추가**

`get_active_locations()` 함수 아래에 추가:
```python
async def get_device_list() -> list[DeviceListItemDto]:
    devices = await admin_repo.get_all_devices()
    result = []
    for d in devices:
        location = None
        if d.lastLocation:
            location = LocationDto(lat=d.lastLocation.lat, lng=d.lastLocation.lng)
        result.append(DeviceListItemDto(
            deviceId=d.deviceId,
            deviceType=d.deviceType,
            currentState=d.currentState.value,
            lastSeenAt=d.lastSeenAt,
            helmetWorn=d.helmetWorn,
            bleConnected=d.bleConnected,
            lastLocation=location,
            fwVersion=d.fwVersion,
            currentPolicyVersion=d.currentPolicyVersion
        ))
    return result
```

- [ ] **Step 3: get_event_logs() 시그니처에 device_id 추가**

기존:
```python
async def get_event_logs(page: int, size: int, severity: Optional[str]) -> EventLogPaginatedResponse:
    items, total = await admin_repo.get_paginated_events(page, size, severity)
```

변경 후:
```python
async def get_event_logs(page: int, size: int, severity: Optional[str], device_id: Optional[str] = None) -> EventLogPaginatedResponse:
    items, total = await admin_repo.get_paginated_events(page, size, severity, device_id)
```

- [ ] **Step 4: 커밋**

```bash
git add backend/app/services/admin_service.py
git commit -m "feat: add get_device_list service and device_id filter to event logs"
```

---

## Task 4: 백엔드 라우터 — GET /admin/devices 추가, GET /admin/events deviceId 파라미터 추가

**Files:**
- Modify: `backend/app/api/v1/admin.py`

- [ ] **Step 1: GET /devices 라우트 추가**

`read_device_locations` 함수 아래에 추가:
```python
@router.get("/devices")
async def read_device_list() -> Any:
    devices = await admin_service.get_device_list()
    return create_success_response(data=[d.model_dump() for d in devices], message="디바이스 목록 조회 성공")
```

- [ ] **Step 2: read_events에 deviceId 파라미터 추가**

기존:
```python
@router.get("/events")
async def read_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None)
) -> Any:
    paginated_events = await admin_service.get_event_logs(page, size, severity)
```

변경 후:
```python
@router.get("/events")
async def read_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None),
    deviceId: Optional[str] = Query(None)
) -> Any:
    paginated_events = await admin_service.get_event_logs(page, size, severity, deviceId)
```

- [ ] **Step 3: 서버 실행 후 수동 검증**

```bash
# 서버 실행 (backend 디렉토리에서)
uvicorn app.main:app --reload --port 8000

# 새 터미널에서 — admin 토큰 필요 (PRE_SHARED_TOKEN 값)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/admin/devices
# 예상: {"success": true, "data": [...], ...}

curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/admin/events?deviceId=test-device&size=10"
# 예상: {"success": true, "data": {"items": [...], ...}, ...}
```

- [ ] **Step 4: 커밋**

```bash
git add backend/app/api/v1/admin.py
git commit -m "feat: add GET /admin/devices endpoint and deviceId filter to events"
```

---

## Task 5: 프론트엔드 API 레이어 — DeviceListItem 타입 + 함수 추가

**Files:**
- Modify: `frontend-web/src/api/adminApi.ts`

- [ ] **Step 1: DeviceListItem 타입 추가**

기존 `EnvironmentStats` 인터페이스 아래에 추가:
```typescript
export interface DeviceLocation {
  lat: number;
  lng: number;
}

export interface DeviceListItem {
  deviceId: string;
  deviceType: string;
  currentState: string;
  lastSeenAt: string | null;
  helmetWorn: boolean;
  bleConnected: boolean;
  lastLocation: DeviceLocation | null;
  fwVersion: string;
  currentPolicyVersion: number;
}
```

- [ ] **Step 2: getDeviceList() 추가, getEvents() deviceId 파라미터 추가**

`adminApi` 객체에서:

기존 `getEvents`:
```typescript
getEvents: (page: number = 1, size: number = 20, severity?: string) => {
  let url = `/admin/events?page=${page}&size=${size}`;
  if (severity) url += `&severity=${severity}`;
  return axiosInstance.get<any, BaseResponse<PaginatedEvents>>(url);
},
```

변경 후 (deviceId 추가 + getDeviceList 추가):
```typescript
getDeviceList: () =>
  axiosInstance.get<any, BaseResponse<DeviceListItem[]>>('/admin/devices'),

getEvents: (page: number = 1, size: number = 20, severity?: string, deviceId?: string) => {
  let url = `/admin/events?page=${page}&size=${size}`;
  if (severity) url += `&severity=${severity}`;
  if (deviceId) url += `&deviceId=${deviceId}`;
  return axiosInstance.get<any, BaseResponse<PaginatedEvents>>(url);
},
```

- [ ] **Step 3: 커밋**

```bash
git add frontend-web/src/api/adminApi.ts
git commit -m "feat: add DeviceListItem type and getDeviceList API function"
```

---

## Task 6: 프론트엔드 쿼리 훅 — useDeviceList, useDeviceEvents 추가

**Files:**
- Modify: `frontend-web/src/hooks/queries/useAdminQueries.ts`

- [ ] **Step 1: useDeviceList 추가**

파일 끝에 추가:
```typescript
export const useDeviceList = () => {
  return useQuery({
    queryKey: ['deviceList'],
    queryFn: async () => {
      const res = await adminApi.getDeviceList();
      return res.data;
    },
    refetchInterval: 30000,
  });
};
```

- [ ] **Step 2: useDeviceEvents 추가**

`useDeviceList` 아래에 추가:
```typescript
export const useDeviceEvents = (deviceId: string) => {
  return useQuery({
    queryKey: ['deviceEvents', deviceId],
    queryFn: async () => {
      const res = await adminApi.getEvents(1, 10, undefined, deviceId);
      return res.data.items;
    },
    enabled: !!deviceId,
    refetchInterval: false,
  });
};
```

- [ ] **Step 3: 커밋**

```bash
git add frontend-web/src/hooks/queries/useAdminQueries.ts
git commit -m "feat: add useDeviceList and useDeviceEvents query hooks"
```

---

## Task 7: DeviceListTable 컴포넌트 생성

**Files:**
- Create: `frontend-web/src/components/devices/DeviceListTable.tsx`

- [ ] **Step 1: 디렉토리 생성 후 파일 작성**

`frontend-web/src/components/devices/DeviceListTable.tsx`:
```tsx
import React from 'react';
import type { DeviceListItem } from '../../api/adminApi';

interface Props {
  devices: DeviceListItem[];
  onSelect: (device: DeviceListItem) => void;
  isLoading: boolean;
}

const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: 'var(--accent-success)',
  RUNNING_LIMITED: '#eab308',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: 'var(--accent-critical)',
  IDLE: 'var(--text-muted)',
  READY: 'var(--text-muted)',
};

function relativeTime(isoStr: string | null): string {
  if (!isoStr) return '알 수 없음';
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '방금 전';
  if (mins < 60) return `${mins}분 전`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}

export const DeviceListTable: React.FC<Props> = ({ devices, onSelect, isLoading }) => {
  if (isLoading) {
    return (
      <div style={{ padding: '1.5rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        디바이스 목록 로딩 중...
      </div>
    );
  }

  if (devices.length === 0) {
    return (
      <div style={{ padding: '1.5rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        등록된 디바이스가 없습니다.
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: 'var(--glass-border)', color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'left' }}>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>디바이스 ID</th>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>타입</th>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>상태</th>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>헬멧</th>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>위치</th>
            <th style={{ padding: '0.75rem 1rem', fontWeight: 500 }}>마지막 접속</th>
          </tr>
        </thead>
        <tbody>
          {devices.map(device => (
            <tr
              key={device.deviceId}
              onClick={() => onSelect(device)}
              style={{ borderBottom: 'var(--glass-border)', cursor: 'pointer', transition: 'background 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <td style={{ padding: '0.875rem 1rem', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {device.deviceId}
              </td>
              <td style={{ padding: '0.875rem 1rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                {device.deviceType}
              </td>
              <td style={{ padding: '0.875rem 1rem' }}>
                <span style={{
                  display: 'inline-block', padding: '0.25rem 0.6rem', borderRadius: '12px',
                  fontSize: '0.75rem', fontWeight: 600,
                  background: `${STATE_COLORS[device.currentState] ?? 'var(--text-muted)'}22`,
                  color: STATE_COLORS[device.currentState] ?? 'var(--text-muted)',
                }}>
                  {device.currentState}
                </span>
              </td>
              <td style={{ padding: '0.875rem 1rem', textAlign: 'center' }}>
                {device.helmetWorn
                  ? <span style={{ color: 'var(--accent-success)', fontWeight: 700 }}>✓</span>
                  : <span style={{ color: 'var(--accent-critical)', fontWeight: 700 }}>✗</span>
                }
              </td>
              <td style={{ padding: '0.875rem 1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {device.lastLocation
                  ? `${device.lastLocation.lat.toFixed(4)}, ${device.lastLocation.lng.toFixed(4)}`
                  : '위치 없음'}
              </td>
              <td style={{ padding: '0.875rem 1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {relativeTime(device.lastSeenAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

- [ ] **Step 2: 커밋**

```bash
git add frontend-web/src/components/devices/DeviceListTable.tsx
git commit -m "feat: add DeviceListTable component"
```

---

## Task 8: DeviceDetailModal 컴포넌트 생성

**Files:**
- Create: `frontend-web/src/components/devices/DeviceDetailModal.tsx`

- [ ] **Step 1: 파일 작성**

`frontend-web/src/components/devices/DeviceDetailModal.tsx`:
```tsx
import React from 'react';
import { X } from 'lucide-react';
import type { DeviceListItem } from '../../api/adminApi';
import { useDeviceEvents } from '../../hooks/queries/useAdminQueries';

interface Props {
  device: DeviceListItem | null;
  onClose: () => void;
}

const STATE_COLORS: Record<string, string> = {
  RUNNING_NORMAL: 'var(--accent-success)',
  RUNNING_LIMITED: '#eab308',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: 'var(--accent-critical)',
  IDLE: 'var(--text-muted)',
  READY: 'var(--text-muted)',
};

const SEVERITY_COLORS: Record<string, string> = {
  high: 'var(--accent-critical)',
  medium: '#eab308',
  low: 'var(--accent-success)',
};

function InfoItem({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.03)', borderRadius: '8px', padding: '0.875rem' }}>
      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.375rem' }}>{label}</div>
      <div style={{ color: 'var(--text-main)', fontWeight: 500 }}>{children}</div>
    </div>
  );
}

export const DeviceDetailModal: React.FC<Props> = ({ device, onClose }) => {
  const { data: events, isLoading: eventsLoading } = useDeviceEvents(device?.deviceId ?? '');

  if (!device) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="glass-panel"
        style={{ width: '100%', maxWidth: '720px', maxHeight: '80vh', overflowY: 'auto', padding: '2rem' }}
      >
        {/* 헤더 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', margin: 0, fontFamily: 'monospace' }}>{device.deviceId}</h2>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textTransform: 'capitalize' }}>
              {device.deviceType}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0.25rem', display: 'flex', alignItems: 'center' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* 정보 그리드 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '2rem' }}>
          <InfoItem label="상태">
            <span style={{
              padding: '0.2rem 0.5rem', borderRadius: '10px', fontSize: '0.8rem', fontWeight: 600,
              background: `${STATE_COLORS[device.currentState] ?? 'var(--text-muted)'}22`,
              color: STATE_COLORS[device.currentState] ?? 'var(--text-muted)',
            }}>
              {device.currentState}
            </span>
          </InfoItem>
          <InfoItem label="헬멧 착용">
            <span style={{ color: device.helmetWorn ? 'var(--accent-success)' : 'var(--accent-critical)', fontWeight: 600 }}>
              {device.helmetWorn ? '착용 중' : '미착용'}
            </span>
          </InfoItem>
          <InfoItem label="BLE 연결">
            <span style={{ color: device.bleConnected ? 'var(--accent-success)' : 'var(--text-muted)' }}>
              {device.bleConnected ? '연결됨' : '미연결'}
            </span>
          </InfoItem>
          <InfoItem label="위치">
            {device.lastLocation
              ? `${device.lastLocation.lat.toFixed(4)}, ${device.lastLocation.lng.toFixed(4)}`
              : '위치 없음'}
          </InfoItem>
          <InfoItem label="펌웨어 버전">{device.fwVersion}</InfoItem>
          <InfoItem label="정책 버전">v{device.currentPolicyVersion}</InfoItem>
        </div>

        {/* 최근 이벤트 */}
        <h3 style={{ fontSize: '0.95rem', marginBottom: '0.875rem', color: 'var(--text-muted)', fontWeight: 500 }}>
          최근 이벤트
        </h3>

        {eventsLoading && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', padding: '0.5rem 0' }}>
            이벤트 로딩 중...
          </div>
        )}

        {!eventsLoading && (!events || events.length === 0) && (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '1.5rem 0' }}>
            이벤트 내역이 없습니다.
          </div>
        )}

        {events && events.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: 'var(--glass-border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 500 }}>이벤트 타입</th>
                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 500 }}>심각도</th>
                <th style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 500 }}>시간</th>
              </tr>
            </thead>
            <tbody>
              {events.map(ev => (
                <tr key={ev.eventId} style={{ borderBottom: 'var(--glass-border)' }}>
                  <td style={{ padding: '0.5rem 0.75rem' }}>{ev.eventType}</td>
                  <td style={{ padding: '0.5rem 0.75rem' }}>
                    <span style={{
                      color: SEVERITY_COLORS[ev.severity] ?? 'var(--text-muted)',
                      fontWeight: 600, textTransform: 'uppercase', fontSize: '0.75rem',
                    }}>
                      {ev.severity}
                    </span>
                  </td>
                  <td style={{ padding: '0.5rem 0.75rem', color: 'var(--text-muted)' }}>
                    {new Date(ev.eventAt).toLocaleString('ko-KR')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: 커밋**

```bash
git add frontend-web/src/components/devices/DeviceDetailModal.tsx
git commit -m "feat: add DeviceDetailModal component"
```

---

## Task 9: Dashboard.tsx 통합

**Files:**
- Modify: `frontend-web/src/screens/Dashboard.tsx`

- [ ] **Step 1: import 추가**

기존 import 블록:
```tsx
import React from 'react';
import { Activity, AlertTriangle, Battery, ShieldCheck } from 'lucide-react';
import { useDashboardStats, useAlertsTimeline, useEnvironmentStats } from '../hooks/queries/useAdminQueries';
import { StatCard } from '../components/common/StatCard';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
```

변경 후:
```tsx
import React, { useState } from 'react';
import { Activity, AlertTriangle, Battery, ShieldCheck } from 'lucide-react';
import { useDashboardStats, useAlertsTimeline, useEnvironmentStats, useDeviceList } from '../hooks/queries/useAdminQueries';
import { StatCard } from '../components/common/StatCard';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { DeviceListTable } from '../components/devices/DeviceListTable';
import { DeviceDetailModal } from '../components/devices/DeviceDetailModal';
import type { DeviceListItem } from '../api/adminApi';
```

- [ ] **Step 2: 컴포넌트 내부 state + 훅 추가**

기존:
```tsx
export const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: timeline } = useAlertsTimeline();
  const { data: envStats } = useEnvironmentStats();

  if (statsLoading) return <div>Loading dashboard data...</div>;
```

변경 후:
```tsx
export const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: timeline } = useAlertsTimeline();
  const { data: envStats } = useEnvironmentStats();
  const { data: devices, isLoading: devicesLoading } = useDeviceList();
  const [selectedDevice, setSelectedDevice] = useState<DeviceListItem | null>(null);

  if (statsLoading) return <div>Loading dashboard data...</div>;
```

- [ ] **Step 3: 차트 섹션 아래 DeviceListTable + DeviceDetailModal 추가**

기존 return 문의 가장 끝 `</div>` 바로 앞에 추가 (차트 Row div 닫힌 후):
```tsx
      {/* Device List */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>디바이스 목록</h3>
        <DeviceListTable
          devices={devices ?? []}
          onSelect={setSelectedDevice}
          isLoading={devicesLoading}
        />
      </div>

      <DeviceDetailModal device={selectedDevice} onClose={() => setSelectedDevice(null)} />
```

전체 return 구조:
```tsx
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Top Stats Row - 기존 유지 */}
      ...
      {/* Charts Row - 기존 유지 */}
      ...
      {/* Device List */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>디바이스 목록</h3>
        <DeviceListTable
          devices={devices ?? []}
          onSelect={setSelectedDevice}
          isLoading={devicesLoading}
        />
      </div>

      <DeviceDetailModal device={selectedDevice} onClose={() => setSelectedDevice(null)} />
    </div>
  );
```

- [ ] **Step 4: TypeScript 타입 체크**

```bash
cd frontend-web && npx tsc --noEmit
# 예상: 에러 없음
```

- [ ] **Step 5: 커밋**

```bash
git add frontend-web/src/screens/Dashboard.tsx
git commit -m "feat: integrate device list and detail modal into dashboard"
```

---

## Task 10: 전체 검증

- [ ] **Step 1: 백엔드 + 프론트엔드 동시 실행**

터미널 1 (백엔드):
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

터미널 2 (프론트엔드):
```bash
cd frontend-web
npm run dev
```

- [ ] **Step 2: 브라우저에서 확인**

1. `http://localhost:5173` 접속
2. Dashboard 화면 하단에 "디바이스 목록" 테이블이 보이는지 확인
3. 디바이스 행 클릭 → 모달 열리는지 확인
4. 모달 내 디바이스 정보(상태, 헬멧, BLE, 위치 등) 표시 확인
5. 모달 하단 최근 이벤트 목록 확인
6. 오버레이 클릭 또는 X 버튼으로 모달 닫히는지 확인
7. 30초 후 디바이스 목록 자동 갱신되는지 확인 (Network 탭)

- [ ] **Step 3: 최종 커밋**

```bash
git add -A
git status  # 남은 파일 없는지 확인
```
