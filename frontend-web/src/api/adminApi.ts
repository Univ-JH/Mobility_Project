import { axiosInstance } from './axiosInstance';

export interface BaseResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  traceId: string;
}

export interface AdminStats {
  activeDevices: int;
  emergenciesToday: int;
  helmetCompliance: float;
  avgBattery: float;
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
  
  getEvents: (page: number = 1, size: number = 20, severity?: string) => {
    let url = `/admin/events?page=${page}&size=${size}`;
    if (severity) url += `&severity=${severity}`;
    return axiosInstance.get<any, BaseResponse<PaginatedEvents>>(url);
  },
  
  exportLogs: () => {
    // For download, we use standard fetch or window.open to handle the stream properly
    // or axios with responseType: 'blob'
    return axiosInstance.get('/admin/export/logs', { responseType: 'blob' });
  }
};
