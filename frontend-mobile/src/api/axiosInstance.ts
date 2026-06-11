import axios from 'axios';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

let _authToken: string | null = null;

export const setAuthToken = (token: string | null): void => {
  _authToken = token;
};

export const getAuthToken = (): string | null => _authToken;

axiosInstance.interceptors.request.use(
  (config) => {
    if (_authToken) {
      config.headers.Authorization = `Bearer ${_authToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('Mobile API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  },
);
