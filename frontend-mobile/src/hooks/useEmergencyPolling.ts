import { useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { userApi } from '../api/userApi';
import { useEmergency } from '../context/EmergencyContext';

// AGENTS.md: no unlimited background network activity
const FOREGROUND_POLL_MS = 5_000;

export const useEmergencyPolling = (): void => {
  const { triggerSOS, emergencyState } = useEmergency();

  const appStateRef = useRef<AppStateStatus>(AppState.currentState);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const emergencyVisibleRef = useRef(emergencyState.visible);

  useEffect(() => {
    emergencyVisibleRef.current = emergencyState.visible;
  }, [emergencyState.visible]);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      appStateRef.current = state;
    });
    return () => sub.remove();
  }, []);

  const { data } = useQuery({
    queryKey: ['emergencies', 'active'],
    queryFn: () => userApi.getActiveEmergencies(),
    // Pause poll when app is backgrounded or overlay already showing
    refetchInterval: () => {
      if (appStateRef.current !== 'active') return false;
      if (emergencyVisibleRef.current) return false;
      return FOREGROUND_POLL_MS;
    },
    staleTime: FOREGROUND_POLL_MS - 1000,
    // Don't show error UI for polling failures — silent retry
    retry: false,
    throwOnError: false,
  });

  // Side-effect: trigger overlay for newly seen server emergencies
  useEffect(() => {
    const emergencies = data?.data?.emergencies;
    if (!emergencies?.length) return;

    for (const emergency of emergencies) {
      if (emergency.status !== 'open') continue;
      if (seenIdsRef.current.has(emergency.id)) continue;

      seenIdsRef.current.add(emergency.id);
      triggerSOS({
        emergencyId: emergency.id,
        reason: emergency.reason,
        source: 'server',
      });
      break; // show one overlay at a time
    }
  }, [data, triggerSOS]);
};
