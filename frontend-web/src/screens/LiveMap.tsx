import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useMapDevices } from '../hooks/queries/useAdminQueries';
import { createMarkerIcon } from '../utils/deviceStatus';
import { MapDevicePanel } from '../components/map/MapDevicePanel';
import type { MapDevice } from '../api/adminApi';

// Suppress default icon URL resolution — we use divIcon exclusively
delete (L.Icon.Default.prototype as any)._getIconUrl;

const DEFAULT_CENTER: [number, number] = [37.498095, 127.02761];
const DEFAULT_ZOOM = 13;
const TRACK_ZOOM = 16;

// Must live inside MapContainer to access useMap()
const MapFlyController: React.FC<{ target: [number, number] | null }> = ({ target }) => {
  const map = useMap();
  useEffect(() => {
    if (target) map.flyTo(target, TRACK_ZOOM, { duration: 1 });
  }, [target, map]);
  return null;
};

export const LiveMap: React.FC = () => {
  const { markerDevices, onlineDevices, offlineDevices, isLoading, isError } = useMapDevices();
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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
        }}
      >
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>실시간 디바이스 지도</h2>
        <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem' }}>
          <span style={{ color: '#10b981' }}>● 온라인 {onlineDevices.length}대</span>
          <span style={{ color: 'var(--text-muted)' }}>● 오프라인 {offlineDevices.length}대</span>
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
            <div
              style={{
                display: 'flex',
                height: '100%',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-muted)',
              }}
            >
              지도 데이터 로딩 중...
            </div>
          ) : isError ? (
            <div
              style={{
                display: 'flex',
                height: '100%',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: '8px',
                color: 'var(--accent-critical)',
              }}
            >
              <span>⚠ 지도 데이터를 불러올 수 없습니다</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                네트워크 상태를 확인하세요
              </span>
            </div>
          ) : (
            <MapContainer
              center={DEFAULT_CENTER}
              zoom={DEFAULT_ZOOM}
              style={{ height: '100%', width: '100%' }}
            >
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
                    <div style={{ minWidth: '150px', lineHeight: '1.6' }}>
                      <strong style={{ display: 'block', marginBottom: '4px' }}>
                        {dev.deviceId}
                      </strong>
                      <div>상태: {dev.state}</div>
                      <div>접속: {dev.isOnline ? '🟢 온라인' : '⚫ 오프라인'}</div>
                      {dev.isDangerous && (
                        <div style={{ color: '#ef4444', fontWeight: 700 }}>⚠ 위험 상태</div>
                      )}
                      {dev.lastSeenAt && (
                        <div style={{ fontSize: '0.75em', color: '#888', marginTop: '4px' }}>
                          마지막 수신:{' '}
                          {new Date(dev.lastSeenAt).toLocaleTimeString('ko-KR')}
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
