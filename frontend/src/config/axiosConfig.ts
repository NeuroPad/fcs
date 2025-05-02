import axios, { AxiosInstance } from 'axios';
import { get } from "../services/storage";
import { store } from '../app/store'; // Import the store
import { logout } from '../features/authSlice'; // Import the logout action

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
    if (error.response && error.response.status === 401) {
      // Dispatch logout action when token is expired
      store.dispatch(logout());
      window.location.reload(); // Reload the page to prompt re-login
    }
    return Promise.reject(error);
  }
);
