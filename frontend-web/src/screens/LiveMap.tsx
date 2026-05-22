import React from 'react';
import { useDeviceLocations } from '../hooks/queries/useAdminQueries';

export const LiveMap: React.FC = () => {
  const { data: locations, isLoading } = useDeviceLocations();

  return (
    <div className="glass-panel" style={{ flex: 1, padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', margin: 0 }}>Live Device Map</h2>
        <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          {locations?.length || 0} active devices
        </span>
      </div>
      
      <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: '8px', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {/* Placeholder for actual Map integration (e.g., react-leaflet) */}
        {isLoading ? (
          <div>Loading map data...</div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <p>Map Integration Placeholder</p>
            <p style={{ fontSize: '0.875rem' }}>Would render {locations?.length || 0} pins here.</p>
            
            {/* Example pseudo-pins */}
            {locations?.map((loc, _) => (
              <div 
                key={loc.deviceId}
                style={{
                  position: 'absolute',
                  top: `${40 + (Math.random() * 20)}%`, 
                  left: `${40 + (Math.random() * 20)}%`,
                  width: '12px', height: '12px',
                  background: loc.state === 'running' ? 'var(--accent-primary)' : 'var(--accent-success)',
                  borderRadius: '50%',
                  boxShadow: '0 0 10px var(--accent-primary)',
                  cursor: 'pointer'
                }}
                title={loc.deviceId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
