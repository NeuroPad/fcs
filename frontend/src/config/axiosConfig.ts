import axios, { AxiosInstance } from 'axios';
import { get } from "../services/storage";

const BASE_URL = 'api/';

export const getBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return window.location.href.includes('sandbox') ||
      window.location.href.includes('localhost')
      ? BASE_URL
      : BASE_URL;
  }
};

export const api: AxiosInstance = axios.create({
  baseURL: getBaseUrl(),
  timeout: 100000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
  const token = await get("token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 403) {
      localStorage.removeItem('token');
      window.location.reload();
    }

    return Promise.reject(error);
  }
);
