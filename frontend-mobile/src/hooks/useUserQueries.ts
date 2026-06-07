import { useQuery } from '@tanstack/react-query';
import { userApi, type MyDevice } from '../api/userApi';
import { useAuth } from '../context/AuthContext';

export const useUserProfile = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await userApi.getProfile();
      return res.data;
    },
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
  });
};

export const useRideHistory = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: ['rideHistory'],
    queryFn: async () => {
      const res = await userApi.getHistory();
      return res.data.history;
    },
    enabled: !!token,
    staleTime: 2 * 60 * 1000,
  });
};

export const useMyDevices = () => {
  const { token } = useAuth();
  return useQuery({
    queryKey: ['myDevices'],
    queryFn: async () => {
      const res = await userApi.getMyDevices();
      return res.data as MyDevice[];
    },
    enabled: !!token,
    staleTime: 30_000,
  });
};
