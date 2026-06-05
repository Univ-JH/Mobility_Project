import React from 'react';
import { X } from 'lucide-react';
import type { DeviceListItem } from '../../api/adminApi';
import { useDeviceEvents } from '../../hooks/queries/useAdminQueries';
import { STATE_COLORS, STATE_BG_COLORS } from '../../utils/deviceStateColors';

interface Props {
  device: DeviceListItem | null;
  onClose: () => void;
}

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
        style={{
          width: '100%', maxWidth: '720px', maxHeight: '80vh', overflowY: 'auto', padding: '2rem',
          background: 'var(--bg-card)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: 'var(--glass-border)',
          borderRadius: '16px',
          boxShadow: 'var(--glass-shadow)',
        }}
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
              background: STATE_BG_COLORS[device.currentState] ?? 'rgba(139, 155, 180, 0.13)',
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
