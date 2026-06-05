import React from 'react';
import { useDeviceLocations } from '../hooks/queries/useAdminQueries';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export const LiveMap: React.FC = () => {
  const { data: locations, isLoading } = useDeviceLocations();

  // 강남역 부근 초기 좌표
  const defaultCenter: [number, number] = [37.498095, 127.027610];

  return (
    <div className="glass-panel" style={{ flex: 1, padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>실시간 디바이스 지도</h2>
        <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          활성 디바이스 {locations?.length || 0}대
        </span>
      </div>
      
      <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden', position: 'relative' }}>
        {isLoading ? (
          <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
            지도 데이터 로딩 중...
          </div>
        ) : (
          <MapContainer center={defaultCenter} zoom={13} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {locations?.map((loc) => (
              <Marker key={loc.deviceId} position={[loc.lat, loc.lng]}>
                <Popup>
                  <strong>{loc.deviceId}</strong><br />
                  상태: {loc.state}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        )}
      </div>
    </div>
  );
};
