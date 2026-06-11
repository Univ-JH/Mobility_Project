import { useEffect, useRef, useState, useCallback } from 'react';
import { axiosInstance } from '../api/axiosInstance';

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
const POLL_INTERVAL_MS = 5_000;

export const useRidingWebSocket = (deviceId: string) => {
  const [data, setData] = useState<RidingData>(INITIAL_DATA);
  const [events, setEvents] = useState<RidingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  const applyStatus = useCallback((d: any) => {
    if (!mountedRef.current) return;
    setData({
      speedKph: typeof d.speedKph === 'number' ? d.speedKph : 0,
      roadType: (d.roadType as any) ?? 'unknown',
      helmetWorn: d.helmetWorn === true,
      bleConnected: d.bleConnected === true,
    });
  }, []);

  // ── HTTP polling (always active as primary data source) ──────────────────
  useEffect(() => {
    if (!deviceId) return;
    mountedRef.current = true;

    const poll = () => {
      axiosInstance
        .get<any, any>(`/devices/${deviceId}/status`)
        .then((res: any) => {
          const d = res?.data ?? res;
          applyStatus(d);
        })
        .catch(() => {/* network error — retry next interval */});
    };

    poll(); // immediate fetch on mount
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [deviceId, applyStatus]);

  // ── WebSocket (upgrade when available — real-time overlay) ──────────────
  useEffect(() => {
    if (!deviceId) return;

    const WS_BASE =
      process.env.EXPO_PUBLIC_WS_URL ?? 'ws://52.79.242.44:8000/v1/ws';
    const url = `${WS_BASE}/device/${deviceId}`;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      console.warn('[WS] Failed to create WebSocket:', e);
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected to', url);
      setConnected(true);
    };

    ws.onclose = (e) => {
      console.warn('[WS] Closed:', e.code, e.reason);
      setConnected(false);
    };

    ws.onerror = (e) => {
      console.warn('[WS] Error:', e);
      setConnected(false);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'telemetry_update') {
          applyStatus(msg);
        } else if (msg.type === 'event_notification') {
          if (!mountedRef.current) return;
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
        // malformed — ignore
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
  }, [deviceId, applyStatus]);

  return { data, events, connected };
};
