import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/adminApi';
import type { MapDevice } from '../../api/adminApi';
import { isDeviceOnline, isDangerous } from '../../utils/deviceStatus';

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['adminStats'],
    queryFn: async () => {
      const res = await adminApi.getStats();
      return res.data;
    },
    refetchInterval: 60000, // Refetch every 1 min
  });
};

export const useAlertsTimeline = () => {
  return useQuery({
    queryKey: ['alertsTimeline'],
    queryFn: async () => {
      const res = await adminApi.getTimeline();
      return res.data.timeline;
    },
    refetchInterval: 60000,
  });
};

export const useEnvironmentStats = () => {
  return useQuery({
    queryKey: ['environmentStats'],
    queryFn: async () => {
      const res = await adminApi.getEnvironment();
      return res.data;
    },
    refetchInterval: 60000,
  });
};

export const useDeviceLocations = () => {
  return useQuery({
    queryKey: ['deviceLocations'],
    queryFn: async () => {
      const res = await adminApi.getLocations();
      return res.data;
    },
    refetchInterval: 10000, // Refetch every 10 secs for live map
  });
};

export const useEventLogs = (page: number, size: number, severity?: string) => {
  return useQuery({
    queryKey: ['eventLogs', page, size, severity],
    queryFn: async () => {
      const res = await adminApi.getEvents(page, size, severity);
      return res.data;
    },
  });
};

export const useDeviceList = () => {
  return useQuery({
    queryKey: ['deviceList'],
    queryFn: async () => {
      const res = await adminApi.getDeviceList();
      return res.data;
    },
    refetchInterval: 30000,
  });
};

export const useDeviceEvents = (deviceId: string) => {
  return useQuery({
    queryKey: ['deviceEvents', deviceId],
    queryFn: async () => {
      const res = await adminApi.getEvents(1, 10, undefined, deviceId);
      return res.data.items;
    },
    enabled: !!deviceId,
    refetchInterval: false,
  });
};

export const useMapDevices = () => {
  const { data: deviceList, isLoading, isError } = useDeviceList();

  const markerDevices = useMemo((): MapDevice[] => {
    return (deviceList ?? [])
      .filter(d => d.lastLocation !== null)
      .map(d => ({
        deviceId: d.deviceId,
        lat: d.lastLocation!.lat,
        lng: d.lastLocation!.lng,
        state: d.currentState,
        isOnline: isDeviceOnline(d.lastSeenAt, d.lastHeartbeatAt),
        isDangerous: isDangerous(d.currentState),
        lastSeenAt: d.lastSeenAt,
      }));
  }, [deviceList]);

  const onlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => isDeviceOnline(d.lastSeenAt, d.lastHeartbeatAt)),
    [deviceList],
  );

  const offlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => !isDeviceOnline(d.lastSeenAt, d.lastHeartbeatAt)),
    [deviceList],
  );

  return { markerDevices, onlineDevices, offlineDevices, isLoading, isError };
};
