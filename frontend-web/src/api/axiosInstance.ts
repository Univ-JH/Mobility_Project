import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://52.79.242.44:8000/v1';

export const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  },
);
