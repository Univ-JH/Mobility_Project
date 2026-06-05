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
