import React, { useState } from 'react';
import type { DeviceListItem } from '../../api/adminApi';
import { isDangerous, STATE_HEX, isDeviceOnline } from '../../utils/deviceStatus';

interface Props {
  onlineDevices: DeviceListItem[];
  offlineDevices: DeviceListItem[];
  selectedDeviceId: string | null;
  onSelect: (deviceId: string) => void;
}

function relativeTime(lastSeenAt: string | null): string {
  if (!lastSeenAt) return '알 수 없음';
  const ts = new Date(lastSeenAt).getTime();
  if (isNaN(ts)) return '알 수 없음';
  const mins = Math.floor((Date.now() - ts) / 60000);
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
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onSelect()}
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
      <div
        style={{
          width: '9px',
          height: '9px',
          borderRadius: '50%',
          background: color,
          flexShrink: 0,
          opacity: online ? 1 : 0.4,
          boxShadow: `0 0 5px ${color}`,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: '0.8rem',
            fontWeight: 600,
            color: 'var(--text-main)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {device.deviceId}
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {dangerous ? '⚠ ' : ''}
          {device.currentState} · {relativeTime(device.lastSeenAt)}
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  count,
  dotColor,
  devices,
  selectedDeviceId,
  onSelect,
}: {
  title: string;
  count: number;
  dotColor: string;
  devices: DeviceListItem[];
  selectedDeviceId: string | null;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div style={{ marginBottom: '8px' }}>
      <div
        onClick={() => setOpen(p => !p)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setOpen(p => !p)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 6px',
          cursor: 'pointer',
          borderRadius: '4px',
          userSelect: 'none',
        }}
      >
        <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: dotColor }} />
        <span
          style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: 'var(--text-muted)',
            letterSpacing: '0.05em',
          }}
        >
          {title}
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '0.7rem',
            background: 'var(--bg-card)',
            padding: '1px 6px',
            borderRadius: '10px',
            color: 'var(--text-muted)',
          }}
        >
          {count}
        </span>
        <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
          {open ? '▲' : '▼'}
        </span>
      </div>

      {open &&
        devices.map(d => (
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
    <div
      style={{
        width: '260px',
        flexShrink: 0,
        background: 'var(--bg-card)',
        border: '1px solid var(--glass-border)',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: '12px 14px 8px',
          borderBottom: '1px solid var(--glass-border)',
          fontSize: '0.8rem',
          fontWeight: 700,
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
          flexShrink: 0,
        }}
      >
        디바이스 목록
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 6px' }}>
        <Section
          title="온라인"
          count={onlineDevices.length}
          dotColor="#10b981"
          devices={onlineDevices}
          selectedDeviceId={selectedDeviceId}
          onSelect={onSelect}
        />
        <Section
          title="오프라인"
          count={offlineDevices.length}
          dotColor="#8b9bb4"
          devices={offlineDevices}
          selectedDeviceId={selectedDeviceId}
          onSelect={onSelect}
        />
      </div>
    </div>
  );
};
