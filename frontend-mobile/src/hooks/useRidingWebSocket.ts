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
const EVENT_POLL_INTERVAL_MS = 10_000;
const DATA_STALE_MS = 15_000;
const WS_RECONNECT_DELAY_MS = 3_000;
const WS_MAX_RETRIES = 5;

export const useRidingWebSocket = (deviceId: string) => {
  const [data, setData] = useState<RidingData>(INITIAL_DATA);
  const [events, setEvents] = useState<RidingEvent[]>([]);
  const [connected, setConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const eventPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const freshnessTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const lastDataAtRef = useRef<number>(0);
  const wsRetriesRef = useRef(0);
  const wsReconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const applyStatus = useCallback((d: any) => {
    if (!mountedRef.current) return;
    lastDataAtRef.current = Date.now();
    setConnected(true);
    setData({
      speedKph: typeof d.speedKph === 'number' ? d.speedKph : 0,
      roadType: (d.roadType as any) ?? 'unknown',
      helmetWorn: d.helmetWorn === true,
      bleConnected: d.bleConnected === true,
    });
  }, []);

  // ── HTTP polling: telemetry (5s) ────────────────────────────────────────
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
        .catch(() => {});
    };

    poll();
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [deviceId, applyStatus]);

  // ── HTTP polling: events (10s) ──────────────────────────────────────────
  useEffect(() => {
    if (!deviceId) return;

    const pollEvents = () => {
      axiosInstance
        .get<any, any>(`/events/device/${deviceId}?limit=${MAX_EVENTS}`)
        .then((res: any) => {
          if (!mountedRef.current) return;
          const list: RidingEvent[] = Array.isArray(res?.data)
            ? res.data
            : Array.isArray(res)
            ? res
            : [];
          if (list.length > 0) {
            setEvents(list.slice(0, MAX_EVENTS));
          }
        })
        .catch(() => {});
    };

    pollEvents();
    eventPollTimerRef.current = setInterval(pollEvents, EVENT_POLL_INTERVAL_MS);

    return () => {
      if (eventPollTimerRef.current) {
        clearInterval(eventPollTimerRef.current);
        eventPollTimerRef.current = null;
      }
    };
  }, [deviceId]);

  // ── Data freshness watchdog ─────────────────────────────────────────────
  useEffect(() => {
    freshnessTimerRef.current = setInterval(() => {
      if (!mountedRef.current) return;
      if (lastDataAtRef.current > 0 && Date.now() - lastDataAtRef.current > DATA_STALE_MS) {
        setConnected(false);
      }
    }, 5_000);

    return () => {
      if (freshnessTimerRef.current) {
        clearInterval(freshnessTimerRef.current);
        freshnessTimerRef.current = null;
      }
    };
  }, []);

  // ── WebSocket (real-time overlay + event push) ──────────────────────────
  useEffect(() => {
    if (!deviceId) return;

    const WS_BASE =
      process.env.EXPO_PUBLIC_WS_URL ?? 'ws://52.79.242.44:8000/v1/ws';
    const url = `${WS_BASE}/device/${deviceId}`;

    let cancelled = false;

    const connect = () => {
      if (cancelled || !mountedRef.current) return;
      if (wsRetriesRef.current >= WS_MAX_RETRIES) {
        console.warn('[WS] Max retries reached, giving up');
        return;
      }

      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        console.warn('[WS] Failed to create WebSocket:', e);
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) { ws.close(); return; }
        console.log('[WS] Connected to', url);
        wsRetriesRef.current = 0;
      };

      ws.onerror = (e) => {
        console.warn('[WS] Error:', e);
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
        if (!cancelled && wsRef.current === ws && ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 20_000);

      ws.onclose = (e) => {
        clearInterval(pingInterval);
        console.warn('[WS] Closed:', e.code, e.reason);
        if (!cancelled && mountedRef.current && wsRetriesRef.current < WS_MAX_RETRIES) {
          wsRetriesRef.current += 1;
          wsReconnectTimerRef.current = setTimeout(connect, WS_RECONNECT_DELAY_MS);
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current);
        wsReconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;
        ws.close();
      }
    };
  }, [deviceId, applyStatus]);

  return { data, events, connected };
};
