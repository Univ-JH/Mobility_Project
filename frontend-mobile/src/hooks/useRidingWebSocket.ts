import { useEffect, useRef, useState } from 'react';

export interface RidingData {
  speedKph: number;
  roadType: 'road' | 'sidewalk' | 'unknown';
  helmetWorn: boolean;
  bleConnected: boolean;
}

export interface RidingEvent {
  eventType: string;
  severity: string;
  reason: string;
  timestamp: string;
}

const INITIAL_DATA: RidingData = {
  speedKph: 0,
  roadType: 'unknown',
  helmetWorn: false,
  bleConnected: false,
};

const MAX_EVENTS = 20;

export const useRidingWebSocket = (deviceId: string) => {
  const [data, setData] = useState<RidingData>(INITIAL_DATA);
  const [events, setEvents] = useState<RidingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!deviceId) return;

    const WS_BASE =
      process.env.EXPO_PUBLIC_WS_URL ?? 'ws://52.79.242.44:8000/v1/ws';
    const url = `${WS_BASE}/device/${deviceId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'telemetry_update') {
          setData({
            speedKph: msg.speedKph ?? 0,
            roadType: msg.roadType ?? 'unknown',
            helmetWorn: msg.helmetWorn ?? false,
            bleConnected: msg.bleConnected ?? false,
          });
        } else if (msg.type === 'event_notification') {
          setEvents((prev) =>
            [
              {
                eventType: msg.eventType,
                severity: msg.severity,
                reason: msg.reason,
                timestamp: msg.timestamp,
              },
              ...prev,
            ].slice(0, MAX_EVENTS),
          );
        }
      } catch {
        // malformed message — ignore
      }
    };

    const pingInterval = setInterval(() => {
      if (wsRef.current === ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 20_000);

    return () => {
      clearInterval(pingInterval);
      wsRef.current = null;
      ws.close();
    };
  }, [deviceId]);

  return { data, events, connected };
};
