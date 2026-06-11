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
const WS_CONNECT_TIMEOUT_MS = 5_000;

export const useRidingWebSocket = (deviceId: string) => {
  const [data, setData] = useState<RidingData>(INITIAL_DATA);
  const [events, setEvents] = useState<RidingEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsConnectedRef = useRef(false);

  const applyStatus = useCallback((d: any) => {
    setData({
      speedKph: d.speedKph ?? 0,
      roadType: d.roadType ?? 'unknown',
      helmetWorn: d.helmetWorn ?? false,
      bleConnected: d.bleConnected ?? false,
    });
  }, []);

  const fetchStatus = useCallback(() => {
    if (!deviceId) return;
    axiosInstance
      .get<any, any>(`/devices/${deviceId}/status`)
      .then((res: any) => {
        const d = res?.data ?? res;
        applyStatus(d);
      })
      .catch(() => {});
  }, [deviceId, applyStatus]);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    fetchStatus();
    pollTimerRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
  }, [fetchStatus]);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!deviceId) return;

    wsConnectedRef.current = false;

    const WS_BASE =
      process.env.EXPO_PUBLIC_WS_URL ?? 'ws://52.79.242.44:8000/v1/ws';
    const url = `${WS_BASE}/device/${deviceId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    // If WebSocket doesn't open within timeout, fall back to HTTP polling.
    const connectTimeout = setTimeout(() => {
      if (!wsConnectedRef.current) {
        startPolling();
      }
    }, WS_CONNECT_TIMEOUT_MS);

    ws.onopen = () => {
      clearTimeout(connectTimeout);
      wsConnectedRef.current = true;
      stopPolling();
      setConnected(true);
    };

    ws.onclose = () => {
      wsConnectedRef.current = false;
      setConnected(false);
      // WebSocket dropped mid-session — fall back to polling
      startPolling();
    };

    ws.onerror = () => {
      wsConnectedRef.current = false;
      setConnected(false);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string);
        if (msg.type === 'telemetry_update') {
          applyStatus(msg);
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
        // malformed — ignore
      }
    };

    const pingInterval = setInterval(() => {
      if (wsRef.current === ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 20_000);

    return () => {
      clearTimeout(connectTimeout);
      clearInterval(pingInterval);
      stopPolling();
      wsRef.current = null;
      ws.close();
    };
  }, [deviceId, applyStatus, startPolling, stopPolling]);

  return { data, events, connected };
};
