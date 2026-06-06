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
  const { data: locations, isLoading } = useDeviceLocations();
  const { data: deviceList } = useDeviceList();

  const statusMap = useMemo(() => {
    const m = new Map<string, (typeof deviceList)[number] & {}>();
    deviceList?.forEach(d => m.set(d.deviceId, d));
    return m;
  }, [deviceList]);

  const markerDevices = useMemo((): MapDevice[] => {
    if (!locations) return [];
    return locations.map(loc => {
      const detail = statusMap.get(loc.deviceId);
      return {
        deviceId: loc.deviceId,
        lat: loc.lat,
        lng: loc.lng,
        state: loc.state,
        isOnline: detail ? isDeviceOnline(detail.lastSeenAt) : true,
        isDangerous: isDangerous(loc.state),
        lastSeenAt: detail?.lastSeenAt ?? null,
      };
    });
  }, [locations, statusMap]);

  const onlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => isDeviceOnline(d.lastSeenAt)),
    [deviceList],
  );

  const offlineDevices = useMemo(
    () => (deviceList ?? []).filter(d => !isDeviceOnline(d.lastSeenAt)),
    [deviceList],
  );

  return { markerDevices, onlineDevices, offlineDevices, isLoading };
};
