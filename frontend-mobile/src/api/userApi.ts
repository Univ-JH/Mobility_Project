import { axiosInstance } from './axiosInstance';

export interface BaseResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  traceId: string;
}

export interface UserProfile {
  name: string;
  email: string;
  safetyScore: number;
  appSettings: Record<string, unknown>;
}

export interface RideHistoryItem {
  rideId: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  alertCount: number;
}

export interface RideHistory {
  history: RideHistoryItem[];
}

export type EmergencyStatus = 'open' | 'acked' | 'resolved' | 'false_alarm';

export interface EmergencyItem {
  id: string;
  reason: string;
  status: EmergencyStatus;
  createdAt: string;
}

export interface ActiveEmergencies {
  emergencies: EmergencyItem[];
}

export const userApi = {
  getProfile: () => 
    axiosInstance.get<any, BaseResponse<UserProfile>>('/users/profile'),
  
  getHistory: () => 
    axiosInstance.get<any, BaseResponse<RideHistory>>('/users/history'),
    
  pairDevice: (deviceId: string, deviceType: string) => 
    axiosInstance.post<any, BaseResponse<any>>('/devices/pair', { deviceId, deviceType }),
    
  unlockDevice: (deviceId: string, lat?: number, lng?: number) => 
    axiosInstance.post<any, BaseResponse<any>>(`/devices/${deviceId}/unlock`, { lat, lng }),
    
  triggerEmergency: (reason: string, lat?: number, lng?: number) =>
    axiosInstance.post<any, BaseResponse<any>>('/events/emergency', { reason, lat, lng }),

  getActiveEmergencies: () =>
    axiosInstance.get<any, BaseResponse<ActiveEmergencies>>('/emergencies?status=open&limit=10'),

  acknowledgeEmergency: (emergencyId: string, status: 'false_alarm' | 'resolved') =>
    axiosInstance.patch<any, BaseResponse<any>>(`/emergencies/${emergencyId}/status`, { status }),
};
