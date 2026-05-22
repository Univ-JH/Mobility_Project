import { useQuery } from '@tanstack/react-query';
import { userApi } from '../api/userApi';

export const useUserProfile = () => {
  return useQuery({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await userApi.getProfile();
      return res.data;
    },
  });
};

export const useRideHistory = () => {
  return useQuery({
    queryKey: ['rideHistory'],
    queryFn: async () => {
      const res = await userApi.getHistory();
      return res.data.history;
    },
  });
};
