import { useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi } from '../api/userApi';
import { Alert } from 'react-native';

export const usePairDevice = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ deviceId, type }: { deviceId: string, type: string }) => 
      userApi.pairDevice(deviceId, type),
    onSuccess: () => {
      // Invalidate queries or update local state
      Alert.alert('Success', 'Device paired successfully');
    },
    onError: (error: any) => {
      Alert.alert('Error', error.response?.data?.message || 'Failed to pair device');
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
    onError: (error: any) => {
      Alert.alert('Error', error.response?.data?.message || 'Failed to unlock device');
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
    onError: (error: any) => {
      Alert.alert('SOS Failed', 'Could not reach the server. Please call emergency services directly.');
    }
  });
};
