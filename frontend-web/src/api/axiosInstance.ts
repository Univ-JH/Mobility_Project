import axios from 'axios';

// Use environment variable if available, else fallback to AWS EC2 IP for MVP
// NOTE: If deploying Web to HTTPS (e.g. Vercel), the backend MUST ALSO be HTTPS to avoid Mixed Content errors.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

axiosInstance.interceptors.request.use(
  (config) => {
    // For MVP prototyping, we inject the mock admin token
    // In production, fetch this from localStorage/context
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
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);
