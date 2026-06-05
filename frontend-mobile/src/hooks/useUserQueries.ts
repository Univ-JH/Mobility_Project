import { useQuery } from '@tanstack/react-query';
import { userApi, type MyDevice } from '../api/userApi';

export const useUserProfile = () => {
  return useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await userApi.getProfile();
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // 5 min — profile changes infrequently
  });
};

export const useRideHistory = () => {
  return useQuery({
    queryKey: ['rideHistory'],
    queryFn: async () => {
      const res = await userApi.getHistory();
      return res.data.history;
    },
    staleTime: 2 * 60 * 1000, // 2 min — new rides appear after sessions end
  });
};

export const useMyDevices = () => {
  return useQuery({
    queryKey: ['myDevices'],
    queryFn: async () => {
      const res = await userApi.getMyDevices();
      return res.data as MyDevice[];
    },
    staleTime: 30_000,
  });
};
