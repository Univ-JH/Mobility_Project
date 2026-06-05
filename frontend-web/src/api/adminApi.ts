import { axiosInstance } from './axiosInstance';

export interface BaseResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  traceId: string;
}

export interface AdminStats {
  activeDevices: number;
  emergenciesToday: number;
  helmetCompliance: number;
  avgBattery: number;
}

export interface LocationDto {
  deviceId: string;
  lat: number;
  lng: number;
  state: string;
}

export interface TimelineBucket {
  time: string;
  count: number;
}

export interface AlertsTimeline {
  timeline: TimelineBucket[];
}

export interface EnvironmentStats {
  sidewalkRatio: number;
  roadRatio: number;
}

export interface DeviceLocation {
  lat: number;
  lng: number;
}

export interface DeviceListItem {
  deviceId: string;
  deviceType: string;
  currentState: string;
  lastSeenAt: string | null;
  helmetWorn: boolean;
  bleConnected: boolean;
  lastLocation: DeviceLocation | null;
  fwVersion: string;
  currentPolicyVersion: number;
}

export interface EventLog {
  eventId: string;
  deviceId: string;
  eventType: string;
  severity: string;
  reason: string;
  confidence: number;
  eventAt: string;
}

export interface PaginatedEvents {
  items: EventLog[];
  totalCount: number;
  page: number;
  size: number;
}

export const adminApi = {
  getStats: () => axiosInstance.get<any, BaseResponse<AdminStats>>('/admin/stats'),
  
  getLocations: () => axiosInstance.get<any, BaseResponse<LocationDto[]>>('/admin/devices/locations'),
  
  getTimeline: () => axiosInstance.get<any, BaseResponse<AlertsTimeline>>('/admin/analytics/alerts-timeline'),
  
  getEnvironment: () => axiosInstance.get<any, BaseResponse<EnvironmentStats>>('/admin/analytics/environment'),
  
  getDeviceList: () =>
    axiosInstance.get<any, BaseResponse<DeviceListItem[]>>('/admin/devices'),

  getEvents: (page: number = 1, size: number = 20, severity?: string, deviceId?: string) => {
    let url = `/admin/events?page=${page}&size=${size}`;
    if (severity) url += `&severity=${severity}`;
    if (deviceId) url += `&deviceId=${deviceId}`;
    return axiosInstance.get<any, BaseResponse<PaginatedEvents>>(url);
  },
  
  exportLogs: () => {
    return axiosInstance.get('/admin/export/logs', { responseType: 'blob' });
  },

  // Policies
  getActivePolicy: () => axiosInstance.get<any, BaseResponse<any>>('/policies/active'),
  updatePolicy: (data: any) => axiosInstance.post<any, BaseResponse<any>>('/policies', data),

  // Emergencies
  getActiveEmergencies: () => axiosInstance.get<any, BaseResponse<any[]>>('/emergencies'),
  ackEmergency: (caseId: string) => axiosInstance.post<any, BaseResponse<any>>(`/emergencies/${caseId}/ack`),
  resolveEmergency: (caseId: string, data: { resolutionType: string; note: string }) => 
    axiosInstance.post<any, BaseResponse<any>>(`/emergencies/${caseId}/resolve`, data)
};
