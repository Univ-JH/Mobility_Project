import L from 'leaflet';

const ONLINE_THRESHOLD_MS = 2 * 60 * 1000; // 2 minutes

export function isDeviceOnline(lastSeenAt: string | null): boolean {
  if (!lastSeenAt) return false;
  return Date.now() - new Date(lastSeenAt).getTime() < ONLINE_THRESHOLD_MS;
}

export function isDangerous(state: string): boolean {
  return ['EMERGENCY', 'AUTO_BRAKING', 'RUNNING_LIMITED'].includes(state);
}

// Hex equivalents of STATE_COLORS (divIcon HTML can't use CSS vars)
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
