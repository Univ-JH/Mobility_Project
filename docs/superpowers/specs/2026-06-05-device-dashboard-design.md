# Device Dashboard Design

**Date:** 2026-06-05  
**Scope:** frontend-web 메인 대시보드 디바이스 목록 + 상세 모달

---

## Overview

메인 대시보드(Dashboard 화면) 하단에 디바이스 목록 테이블을 추가한다. 행 클릭 시 해당 디바이스의 상세 정보와 최근 이벤트 10개를 모달로 표시한다.

---

## Backend Changes

### New Endpoint: `GET /admin/devices`

전체 디바이스 목록 반환. 어드민 인증 필요 (기존 `get_current_admin` 의존성).

**Response fields per item:**
```json
{
  "deviceId": "string",
  "deviceType": "string",
  "currentState": "IDLE | READY | RUNNING_NORMAL | RUNNING_LIMITED | AUTO_BRAKING | EMERGENCY",
  "lastSeenAt": "ISO8601 | null",
  "helmetWorn": "boolean",
  "bleConnected": "boolean",
  "lastLocation": { "lat": "float", "lng": "float" } | null,
  "fwVersion": "string",
  "currentPolicyVersion": "integer"
}
```

**변경 파일:**
- `backend/app/api/v1/admin.py` — `GET /devices` 라우트 추가
- `backend/app/services/admin_service.py` — `get_device_list()` 추가
- `backend/app/repositories/admin_repo.py` — `get_all_devices()` 추가 (정렬: `lastSeenAt` 내림차순)
- `backend/app/schemas/admin_dto.py` — `DeviceListItemDto` 스키마 추가

### Modified Endpoint: `GET /admin/events`

기존 파라미터(`page`, `size`, `severity`)에 `deviceId: Optional[str]` 추가.

**변경 파일:**
- `backend/app/api/v1/admin.py` — `deviceId` 쿼리 파라미터 추가
- `backend/app/services/admin_service.py` — `get_event_logs()` `device_id` 인자 추가
- `backend/app/repositories/admin_repo.py` — `get_paginated_events()` deviceId 필터 추가

---

## Frontend Changes

### API Layer (`src/api/adminApi.ts`)

추가:
- `DeviceListItem` 타입 (백엔드 DTO 대응)
- `getDeviceList()` → `GET /admin/devices`
- `getEvents()` 시그니처에 `deviceId?: string` 추가

### Query Hooks (`src/hooks/queries/useAdminQueries.ts`)

추가:
- `useDeviceList()` — `refetchInterval: 30000`
- `useDeviceEvents(deviceId: string)` — `enabled: !!deviceId`, `refetchInterval: false`

### New Components

**`src/components/devices/DeviceListTable.tsx`**

| Props | Type |
|---|---|
| `devices` | `DeviceListItem[]` |
| `onSelect` | `(device: DeviceListItem) => void` |
| `isLoading` | `boolean` |

- 행 클릭 → `onSelect(device)` 호출
- `currentState` 배지 색상:
  - `RUNNING_NORMAL` → 초록(`var(--accent-success)`)
  - `RUNNING_LIMITED` → 노랑(`#eab308`)
  - `AUTO_BRAKING` → 주황(`#f97316`)
  - `EMERGENCY` → 빨강(`var(--accent-critical)`)
  - `IDLE`, `READY` → 회색(`var(--text-muted)`)
- `helmetWorn`: ✓ / ✗ 아이콘
- `lastSeenAt`: 상대 시간 표시 (예: "3분 전")
- `lastLocation`: 소수점 4자리 lat/lng 또는 "위치 없음"

**`src/components/devices/DeviceDetailModal.tsx`**

| Props | Type |
|---|---|
| `device` | `DeviceListItem \| null` |
| `onClose` | `() => void` |

- `device === null` → 렌더링 없음
- 상단 섹션: 상태 배지, deviceType, FW 버전, 정책 버전, BLE 연결, 헬멧, 마지막 위치
- 하단 섹션: `useDeviceEvents(device.deviceId)` 최근 이벤트 10개 테이블 (eventType, severity, eventAt)
- 닫기: 오버레이 클릭 또는 X 버튼
- 오버레이: `position: fixed`, `inset: 0`, `backdrop-filter: blur(4px)`

### Dashboard Integration (`src/screens/Dashboard.tsx`)

- `selectedDevice: DeviceListItem | null` state 추가
- 기존 차트 섹션 아래 `<DeviceListTable>` 섹션 추가
- `<DeviceDetailModal>` 조건부 렌더링
- `useDeviceList()` 훅 추가

**변경 없는 파일:** `App.tsx`, `Sidebar.tsx`, `Layout.tsx`

---

## Data Flow

```
Dashboard
  └── useDeviceList() → GET /admin/devices (30s interval)
  └── DeviceListTable (row click → setSelectedDevice)
  └── DeviceDetailModal
        └── useDeviceEvents(deviceId) → GET /admin/events?deviceId=xxx&size=10
```

---

## Error Handling

- 디바이스 목록 로딩 실패: 테이블 영역에 에러 메시지 표시 (크래시 없음)
- 이벤트 로딩 실패: 모달 하단에 "이벤트를 불러올 수 없습니다" 표시
- 빈 디바이스 목록: "등록된 디바이스가 없습니다" 빈 상태 표시
