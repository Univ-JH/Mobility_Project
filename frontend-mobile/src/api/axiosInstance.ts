import axios from 'axios';
import { Platform } from 'react-native';

// Use Expo env variable if available, else fallback to AWS MVP IP
const BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

axiosInstance.interceptors.request.use(
  (config) => {
    // For MVP prototyping, we inject a mock mobile token
    const token = 'mock-jwt-token';
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

axiosInstance.interceptors.response.use(
  (response) => {
    // Return just the response data object
    return response.data;
  },
  (error) => {
    console.error('Mobile API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
