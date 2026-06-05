import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import { userApi, type BaseResponse } from '../api/userApi';
import { Alert } from 'react-native';

type ApiError = AxiosError<BaseResponse<unknown>>;

export const usePairDevice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ deviceId, type }: { deviceId: string, type: string }) => 
      userApi.pairDevice(deviceId, type),
    onSuccess: () => {
      // Invalidate queries or update local state
      Alert.alert('Success', 'Device paired successfully');
    },
    onError: (error: ApiError) => {
      Alert.alert('Error', error.response?.data?.message ?? 'Failed to pair device');
    }
  });
};

export const useUnlockDevice = () => {
  return useMutation({
    mutationFn: ({ deviceId, lat, lng }: { deviceId: string, lat?: number, lng?: number }) => 
      userApi.unlockDevice(deviceId, lat, lng),
    onSuccess: () => {
      Alert.alert('Success', 'Unlock command sent to device');
    },
    onError: (error: ApiError) => {
      Alert.alert('Error', error.response?.data?.message ?? 'Failed to unlock device');
    }
  });
};

export const useTriggerEmergency = () => {
  return useMutation({
    mutationFn: ({ reason, lat, lng }: { reason: string, lat?: number, lng?: number }) =>
      userApi.triggerEmergency(reason, lat, lng),
    onSuccess: () => {
      Alert.alert('SOS Sent', 'Emergency services and contacts have been notified.');
    },
    onError: (error: ApiError) => {
      Alert.alert('SOS Failed', 'Could not reach the server. Please call emergency services directly.');
    }
  });
};

export const useRegisterDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ deviceId, deviceType }: { deviceId: string; deviceType: string }) =>
      userApi.registerDevice(deviceId, deviceType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myDevices'] });
      Alert.alert('등록 완료', '디바이스가 등록되었습니다.');
    },
    onError: (error: ApiError) => {
      Alert.alert('오류', error.response?.data?.message ?? '디바이스 등록에 실패했습니다.');
    },
  });
};

export const useDeregisterDevice = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) => userApi.deregisterDevice(deviceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['myDevices'] });
      Alert.alert('해제 완료', '디바이스 등록이 해제되었습니다.');
    },
    onError: (error: ApiError) => {
      Alert.alert('오류', error.response?.data?.message ?? '디바이스 해제에 실패했습니다.');
    },
  });
};
