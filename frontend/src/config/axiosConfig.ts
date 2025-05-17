import axios, { AxiosInstance } from 'axios';
import { get } from "../services/storage";
import { logout } from '../features/authSlice'; // Import the logout action
import { API_BASE_URL } from '../api/config';
const BASE_URL = API_BASE_URL;

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

export const setupAxiosInterceptors = (store: any) => {
  api.interceptors.request.use(async (config) => {
    const token = await get("token");
    console.log('Fetching token from storage:', token); // Add this line
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
      console.log('Adding Authorization header:', config.headers["Authorization"]); // Add this line
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
};
