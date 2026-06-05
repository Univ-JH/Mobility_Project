import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../api/adminApi';

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
