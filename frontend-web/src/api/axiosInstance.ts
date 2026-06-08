import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

export const getAdminToken = (): string | null => localStorage.getItem('admin_token');
export const setAdminToken = (token: string | null): void => {
  if (token) localStorage.setItem('admin_token', token);
  else localStorage.removeItem('admin_token');
};

axiosInstance.interceptors.request.use(
  (config) => {
    const token = getAdminToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error),
);

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  },
);
