# LiveMap Device Status & Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the LiveMap screen with per-device status badges on markers, an online/offline device side panel, and click-to-track functionality.

**Architecture:** Extend existing `useDeviceLocations()` (10s) + `useDeviceList()` (30s) polling hooks. Merge results in a new `useMapDevices()` hook that supplies both marker data and panel data. Custom Leaflet `divIcon` renders colored status labels above each pin. A fixed-width left panel lists online/offline devices; clicking any item fires a `flyTo` via a `MapFlyController` child component that calls react-leaflet's `useMap()`.

**Tech Stack:** React 19, TypeScript, react-leaflet v5, Leaflet v1.9.4, TanStack Query v5, lucide-react, existing CSS variables (dark glassmorphism theme)

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/utils/deviceStatus.ts` | Online/offline detection, danger classification, custom divIcon factory |
| Modify | `src/api/adminApi.ts` | Add `MapDevice` interface |
| Modify | `src/hooks/queries/useAdminQueries.ts` | Add `useMapDevices()` combining both hooks |
| Create | `src/components/map/MapDevicePanel.tsx` | Side panel: online/offline lists with click-to-select |
| Modify | `src/screens/LiveMap.tsx` | Full refactor: layout, custom markers, tracking, panel integration |

---

## Task 1: Device Status Utilities

**Files:**
- Create: `src/utils/deviceStatus.ts`

### Why this first
All other tasks depend on the icon factory and helper functions. No imports yet — pure logic, easiest to verify in isolation.

- [ ] **Step 1.1: Create `src/utils/deviceStatus.ts`**

```typescript
import L from 'leaflet';

const ONLINE_THRESHOLD_MS = 2 * 60 * 1000; // 2 minutes

export function isDeviceOnline(lastSeenAt: string | null): boolean {
  if (!lastSeenAt) return false;
  return Date.now() - new Date(lastSeenAt).getTime() < ONLINE_THRESHOLD_MS;
}

// Dangerous = user at risk, requires attention
export function isDangerous(state: string): boolean {
  return ['EMERGENCY', 'AUTO_BRAKING', 'RUNNING_LIMITED'].includes(state);
}

// Hex colors matching STATE_COLORS in deviceStateColors.ts (divIcon needs raw hex, not CSS vars)
export const STATE_HEX: Record<string, string> = {
  RUNNING_NORMAL: '#10b981',
  RUNNING_LIMITED: '#eab308',
  AUTO_BRAKING: '#f97316',
  EMERGENCY: '#ef4444',
  IDLE: '#8b9bb4',
  READY: '#8b9bb4',
};

export function createMarkerIcon(state: string, online: boolean): L.DivIcon {
  const color = STATE_HEX[state] ?? '#8b9bb4';
  const label = isDangerous(state) ? '위험' : '안전';
  const statusText = online ? '온라인' : '오프라인';
  const dotOpacity = online ? '1' : '0.4';

  return L.divIcon({
    className: '',
    html: `
      <div style="display:flex;flex-direction:column;align-items:center;pointer-events:none;">
        <div style="
          background:${color};
          color:#fff;
          font-size:9px;
          font-weight:700;
          font-family:'Outfit',sans-serif;
          padding:1px 5px;
          border-radius:4px;
          white-space:nowrap;
          margin-bottom:3px;
          box-shadow:0 1px 4px rgba(0,0,0,0.4);
          opacity:${dotOpacity};
        ">${label} · ${statusText}</div>
        <div style="
          width:14px;height:14px;border-radius:50%;
          background:${color};
          border:2px solid rgba(255,255,255,0.9);
          box-shadow:0 0 8px ${color};
          opacity:${dotOpacity};
        "></div>
      </div>
    `,
    iconSize: [80, 38],
    iconAnchor: [40, 38],
    popupAnchor: [0, -40],
  });
}
```

- [ ] **Step 1.2: Verify TypeScript compiles**

```bash
cd frontend-web && npx tsc --noEmit
```
Expected: no errors for `src/utils/deviceStatus.ts`

- [ ] **Step 1.3: Commit**

```bash
git add frontend-web/src/utils/deviceStatus.ts
git commit -m "feat(frontend): add device status utilities and custom marker icon factory"
```

---

## Task 2: MapDevice Type + `useMapDevices` Hook

**Files:**
- Modify: `src/api/adminApi.ts` (add `MapDevice` interface)
- Modify: `src/hooks/queries/useAdminQueries.ts` (add `useMapDevices`)

### Why this second
The panel and the map both need the merged device data. Centralising in a hook keeps LiveMap.tsx clean.

- [ ] **Step 2.1: Add `MapDevice` interface to `src/api/adminApi.ts`**

Add after the `DeviceListItem` interface (after line 54):

```typescript
export interface MapDevice {
  deviceId: string;
  lat: number;
  lng: number;
  state: string;
  isOnline: boolean;
  isDangerous: boolean;
  lastSeenAt: string | null;
}
```

- [ ] **Step 2.2: Add `useMapDevices` to `src/hooks/queries/useAdminQueries.ts`**

Add at the bottom of the file:

```typescript
import { useMemo } from 'react';
import { isDeviceOnline, isDangerous } from '../../utils/deviceStatus';
import type { MapDevice } from '../../api/adminApi';

export const useMapDevices = () => {
  const { data: locations, isLoading } = useDeviceLocations();
  const { data: deviceList } = useDeviceList();

  const statusMap = useMemo(() => {
    const m = new Map<string, DeviceListItem>();
    deviceList?.forEach(d => m.set(d.deviceId, d));
    return m;
  }, [deviceList]);

  const markerDevices = useMemo((): MapDevice[] => {
    if (!locations) return [];
    return locations.map(loc => {
      const detail = statusMap.get(loc.deviceId);
      return {
        deviceId: loc.deviceId,
        lat: loc.lat,
        lng: loc.lng,
        state: loc.state,
        isOnline: detail ? isDeviceOnline(detail.lastSeenAt) : true,
        isDangerous: isDangerous(loc.state),
        lastSeenAt: detail?.lastSeenAt ?? null,
      };
    });
  }, [locations, statusMap]);

  const onlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => isDeviceOnline(d.lastSeenAt)),
    [deviceList],
  );

  const offlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => !isDeviceOnline(d.lastSeenAt)),
    [deviceList],
  );

  return { markerDevices, onlineDevices, offlineDevices, isLoading };
};
```

Note: `DeviceListItem` is already imported via the existing `useDeviceList` body — TypeScript can infer its type from the existing `adminApi` import at the top. Make sure `adminApi.ts` imports are correct.

- [ ] **Step 2.3: Verify TypeScript compiles**

```bash
cd frontend-web && npx tsc --noEmit
```
Expected: no new errors

- [ ] **Step 2.4: Commit**

```bash
git add frontend-web/src/api/adminApi.ts frontend-web/src/hooks/queries/useAdminQueries.ts
git commit -m "feat(frontend): add MapDevice type and useMapDevices combined hook"
```

---

## Task 3: MapDevicePanel Component

**Files:**
- Create: `src/components/map/MapDevicePanel.tsx`

### What it renders
Fixed-width (260px) scrollable panel with two collapsible sections — "온라인" and "오프라인" — each listing `DeviceListItem[]`. Each row shows: colored state dot, `deviceId`, state text, last-seen relative time. Clicking a row calls `onSelect(deviceId)`. Selected row gets a highlight.

- [ ] **Step 3.1: Create `src/components/map/MapDevicePanel.tsx`**

```typescript
import React, { useState } from 'react';
import type { DeviceListItem } from '../../api/adminApi';
import { isDeviceOnline, isDangerous, STATE_HEX } from '../../utils/deviceStatus';

interface Props {
  onlineDevices: DeviceListItem[];
  offlineDevices: DeviceListItem[];
  selectedDeviceId: string | null;
  onSelect: (deviceId: string) => void;
}

function relativeTime(lastSeenAt: string | null): string {
  if (!lastSeenAt) return '알 수 없음';
  const diff = Date.now() - new Date(lastSeenAt).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '방금 전';
  if (mins < 60) return `${mins}분 전`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}시간 전`;
  return `${Math.floor(hrs / 24)}일 전`;
}

function DeviceRow({
  device,
  selected,
  onSelect,
}: {
  device: DeviceListItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const color = STATE_HEX[device.currentState] ?? '#8b9bb4';
  const online = isDeviceOnline(device.lastSeenAt);
  const dangerous = isDangerous(device.currentState);

  return (
    <div
      onClick={onSelect}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 10px',
        borderRadius: '6px',
        cursor: 'pointer',
        background: selected ? 'rgba(99,179,237,0.15)' : 'transparent',
        border: selected ? '1px solid rgba(99,179,237,0.4)' : '1px solid transparent',
        transition: 'background 0.15s',
        marginBottom: '2px',
      }}
    >
      {/* State color dot */}
      <div style={{
        width: '9px', height: '9px', borderRadius: '50%',
        background: color, flexShrink: 0,
        opacity: online ? 1 : 0.4,
        boxShadow: `0 0 5px ${color}`,
      }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: '0.8rem',
          fontWeight: 600,
          color: 'var(--text-main)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {device.deviceId}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {dangerous ? '⚠ ' : ''}{device.currentState} · {relativeTime(device.lastSeenAt)}
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  count,
  color,
  devices,
  selectedDeviceId,
  onSelect,
}: {
  title: string;
  count: number;
  color: string;
  devices: DeviceListItem[];
  selectedDeviceId: string | null;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div style={{ marginBottom: '8px' }}>
      <div
        onClick={() => setOpen(p => !p)}
        style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '5px 6px', cursor: 'pointer', borderRadius: '4px',
          userSelect: 'none',
        }}
      >
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: color }} />
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
          {title}
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.7rem',
          background: 'var(--bg-card)',
          padding: '1px 6px',
          borderRadius: '10px',
          color: 'var(--text-muted)',
        }}>{count}</span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && devices.map(d => (
        <DeviceRow
          key={d.deviceId}
          device={d}
          selected={selectedDeviceId === d.deviceId}
          onSelect={() => onSelect(d.deviceId)}
        />
      ))}
    </div>
  );
}

export const MapDevicePanel: React.FC<Props> = ({
  onlineDevices,
  offlineDevices,
  selectedDeviceId,
  onSelect,
}) => {
  return (
    <div style={{
      width: '260px',
      flexShrink: 0,
      background: 'var(--bg-card)',
      border: '1px solid var(--glass-border)',
      borderRadius: '8px',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '12px 14px 8px',
        borderBottom: '1px solid var(--glass-border)',
        fontSize: '0.8rem',
        fontWeight: 700,
        color: 'var(--text-muted)',
        letterSpacing: '0.06em',
      }}>
        디바이스 목록
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 6px' }}>
        <Section
          title="온라인"
          count={onlineDevices.length}
          color="#10b981"
          devices={onlineDevices}
          selectedDeviceId={selectedDeviceId}
          onSelect={onSelect}
        />
        <Section
          title="오프라인"
          count={offlineDevices.length}
          color="#8b9bb4"
          devices={offlineDevices}
          selectedDeviceId={selectedDeviceId}
          onSelect={onSelect}
        />
      </div>
    </div>
  );
};
```

- [ ] **Step 3.2: Verify TypeScript compiles**

```bash
cd frontend-web && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 3.3: Commit**

```bash
git add frontend-web/src/components/map/MapDevicePanel.tsx
git commit -m "feat(frontend): add MapDevicePanel component with online/offline sections"
```

---

## Task 4: LiveMap.tsx Full Refactor

**Files:**
- Modify: `src/screens/LiveMap.tsx`

### What changes
1. Replace `useDeviceLocations()` with `useMapDevices()`
2. Add `selectedDeviceId` state
3. Add `MapFlyController` inner component (calls `useMap()` to fly to selected device)
4. Replace default Leaflet markers with custom `createMarkerIcon()` markers
5. Enrich popup with state, online status, danger badge
6. Layout: flex row — `MapDevicePanel` (260px) + map (flex:1)
7. Header stat uses `markerDevices.length` for active count

- [ ] **Step 4.1: Rewrite `src/screens/LiveMap.tsx`**

```typescript
import React, { useState, useEffect } from 'react';
import { useMapDevices } from '../hooks/queries/useAdminQueries';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { createMarkerIcon } from '../utils/deviceStatus';
import { MapDevicePanel } from '../components/map/MapDevicePanel';
import type { MapDevice } from '../api/adminApi';

// Suppress default icon URL resolution (we use divIcon)
delete (L.Icon.Default.prototype as any)._getIconUrl;

const DEFAULT_CENTER: [number, number] = [37.498095, 127.02761];
const DEFAULT_ZOOM = 13;
const TRACK_ZOOM = 16;

// Child component: programmatically fly map when selectedDeviceId changes
const MapFlyController: React.FC<{ target: [number, number] | null }> = ({ target }) => {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, TRACK_ZOOM, { duration: 1 });
  }, [target, map]);
  return null;
};

export const LiveMap: React.FC = () => {
  const { markerDevices, onlineDevices, offlineDevices, isLoading } = useMapDevices();
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);

  const selectedDevice: MapDevice | undefined = markerDevices.find(
    d => d.deviceId === selectedDeviceId,
  );
  const flyTarget: [number, number] | null = selectedDevice
    ? [selectedDevice.lat, selectedDevice.lng]
    : null;

  return (
    <div
      className="glass-panel"
      style={{ flex: 1, padding: '1.5rem', display: 'flex', flexDirection: 'column' }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>실시간 디바이스 지도</h2>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          <span style={{ color: '#10b981' }}>● 온라인 {onlineDevices.length}대</span>
          <span>● 오프라인 {offlineDevices.length}대</span>
        </div>
      </div>

      {/* Body: panel + map */}
      <div style={{ flex: 1, display: 'flex', gap: '12px', minHeight: 0 }}>
        <MapDevicePanel
          onlineDevices={onlineDevices}
          offlineDevices={offlineDevices}
          selectedDeviceId={selectedDeviceId}
          onSelect={setSelectedDeviceId}
        />

        <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden', position: 'relative' }}>
          {isLoading ? (
            <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
              지도 데이터 로딩 중...
            </div>
          ) : (
            <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} style={{ height: '100%', width: '100%' }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapFlyController target={flyTarget} />
              {markerDevices.map(dev => (
                <Marker
                  key={dev.deviceId}
                  position={[dev.lat, dev.lng]}
                  icon={createMarkerIcon(dev.state, dev.isOnline)}
                  eventHandlers={{ click: () => setSelectedDeviceId(dev.deviceId) }}
                >
                  <Popup>
                    <div style={{ minWidth: '140px' }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>{dev.deviceId}</strong>
                      <div>상태: {dev.state}</div>
                      <div>접속: {dev.isOnline ? '🟢 온라인' : '⚫ 오프라인'}</div>
                      {dev.isDangerous && <div style={{ color: '#ef4444', fontWeight: 700 }}>⚠ 위험 상태</div>}
                      {dev.lastSeenAt && (
                        <div style={{ fontSize: '0.75em', color: '#888', marginTop: '4px' }}>
                          마지막 수신: {new Date(dev.lastSeenAt).toLocaleTimeString('ko-KR')}
                        </div>
                      )}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          )}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 4.2: Verify TypeScript compiles**

```bash
cd frontend-web && npx tsc --noEmit
```
Expected: no errors

- [ ] **Step 4.3: Commit**

```bash
git add frontend-web/src/screens/LiveMap.tsx
git commit -m "feat(frontend): refactor LiveMap with status markers, device panel, and click-to-track"
```

---

## Spec Coverage Checklist

| Requirement | Task |
|-------------|------|
| 마커 위에 현재 상태 표시 (위험/안전, 온라인/오프라인) | Task 1 (divIcon label) + Task 4 (marker rendering) |
| 온라인 디바이스 목록 | Task 3 (온라인 section) |
| 오프라인 디바이스 목록 | Task 3 (오프라인 section) |
| 특정 디바이스 클릭 → 지도 추적 | Task 4 (MapFlyController + onSelect) |
| 데이터 소스 (state, lastSeenAt) | Task 2 (useMapDevices merge) |

---

## Execution Notes

- Tasks 1 → 2 → 3 → 4 must run sequentially (each depends on the previous)
- After each task: run `npx tsc --noEmit`, review diff, commit
- After Task 4: start dev server and visually verify in browser
- No backend changes required — all data comes from existing `/admin/devices` and `/admin/devices/locations` endpoints
